from __future__ import annotations

import json
import numpy as np
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.models.schemas import ListingData, RankedListingResult

_CORPUS: tuple | None = None
_DATA_DIR = Path("/workshop/retrieval_aws/data")
RRF_K = 60


def _load_corpus() -> tuple:
    global _CORPUS
    if _CORPUS is not None:
        return _CORPUS

    d = np.load(_DATA_DIR / "embeddings_bge_dense.npz")
    ids = list(d["ids"])
    dense_vecs = d["vecs"].astype(np.float32)
    id_to_idx = {lid: i for i, lid in enumerate(ids)}

    sparse_by_id: dict[str, dict[str, float]] = {}
    with open(_DATA_DIR / "embeddings_sparse.jsonl") as f:
        for line in f:
            r = json.loads(line)
            sparse_by_id[r["id"]] = {k: float(v) for k, v in r["weights"].items()}

    siglip: tuple | None = None
    siglip_path = _DATA_DIR / "siglip_image_vecs.npz"
    if siglip_path.exists():
        s = np.load(siglip_path)
        siglip_ids = list(s["ids"])
        siglip_vecs = s["vecs"].astype(np.float32)
        sid_to_idx = {lid: i for i, lid in enumerate(siglip_ids)}
        siglip = (siglip_vecs, sid_to_idx)

    _CORPUS = (dense_vecs, sparse_by_id, id_to_idx, siglip)
    return _CORPUS


def _rrf_fuse(rank_lists: list[list[str]], k: int = RRF_K) -> list[tuple[str, float]]:
    scores: dict[str, float] = defaultdict(float)
    for rlist in rank_lists:
        for rank, lid in enumerate(rlist, 1):
            scores[lid] += 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: -x[1])


def rank_listings(
    candidates: list[dict[str, Any]],
    soft_facts: dict[str, Any],
) -> list[RankedListingResult]:
    if not candidates:
        return []

    qv: np.ndarray | None = soft_facts.get("_query_dense")
    qw: dict[str, float] | None = soft_facts.get("_query_sparse")

    if qv is None or qw is None:
        # No query vectors — return as-is with stub scores
        return [
            RankedListingResult(
                listing_id=str(c["listing_id"]),
                score=1.0,
                reason="Hard filter match.",
                listing=_to_listing_data(c),
            )
            for c in candidates
        ]

    dense_vecs, sparse_by_id, id_to_idx, siglip = _load_corpus()
    pool = [str(c["listing_id"]) for c in candidates]

    # BGE dense scores
    cand_idxs = np.array([id_to_idx[lid] for lid in pool if lid in id_to_idx])
    valid_pool = [lid for lid in pool if lid in id_to_idx]
    d_scores = dense_vecs[cand_idxs] @ qv[0]
    dense_rank = [valid_pool[i] for i in np.argsort(-d_scores)]

    # BGE sparse scores
    sp = np.zeros(len(valid_pool), dtype=np.float32)
    for i, lid in enumerate(valid_pool):
        w = sparse_by_id.get(lid, {})
        sp[i] = sum(qw.get(tok, 0.0) * dw for tok, dw in w.items())
    sparse_rank = [valid_pool[i] for i in np.argsort(-sp)]

    rank_lists: list[list[str]] = [dense_rank, sparse_rank]

    # BM25 as 3rd signal (top-N only — lower influence than BGE)
    bm25_top: dict[str, int] = soft_facts.get("_bm25_top", {})
    if bm25_top:
        # Only include BM25 hits that are in the candidate pool
        bm25_rank = [lid for lid in sorted(bm25_top, key=bm25_top.__getitem__) if lid in set(valid_pool)]
        if bm25_rank:
            rank_lists.append(bm25_rank)

    # SigLIP image scores (query text tower not available without model — skip)
    # TODO: encode query with SigLIP text tower when model is cached locally

    fused = _rrf_fuse(rank_lists)
    score_map = {lid: score for lid, score in fused}
    cand_map = {str(c["listing_id"]): c for c in candidates}

    results = []
    for lid, rrf_score in fused:
        c = cand_map.get(lid)
        if c is None:
            continue
        results.append(RankedListingResult(
            listing_id=lid,
            score=round(rrf_score, 6),
            reason="BGE-M3 dense+sparse RRF.",
            listing=_to_listing_data(c),
        ))

    # Append any candidates not in BGE corpus (no embedding)
    ranked_ids = set(score_map)
    for c in candidates:
        lid = str(c["listing_id"])
        if lid not in ranked_ids:
            results.append(RankedListingResult(
                listing_id=lid,
                score=0.0,
                reason="No embedding available.",
                listing=_to_listing_data(c),
            ))

    return results


def _to_listing_data(candidate: dict[str, Any]) -> ListingData:
    return ListingData(
        id=str(candidate["listing_id"]),
        title=candidate["title"],
        description=candidate.get("description"),
        street=candidate.get("street"),
        city=candidate.get("city"),
        postal_code=candidate.get("postal_code"),
        canton=candidate.get("canton"),
        latitude=candidate.get("latitude"),
        longitude=candidate.get("longitude"),
        price_chf=candidate.get("price"),
        rooms=candidate.get("rooms"),
        living_area_sqm=_coerce_int(candidate.get("area")),
        available_from=candidate.get("available_from"),
        image_urls=_coerce_image_urls(candidate.get("image_urls")),
        hero_image_url=candidate.get("hero_image_url"),
        original_listing_url=candidate.get("original_url"),
        features=candidate.get("features") or [],
        offer_type=candidate.get("offer_type"),
        object_category=candidate.get("object_category"),
        object_type=candidate.get("object_type"),
    )


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _coerce_image_urls(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    return None
