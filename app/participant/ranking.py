from __future__ import annotations

import json
from typing import Any

from app.core.claude import RANKING_MAX_TOKENS, SMART_MODEL, client as _client
from app.models.schemas import ListingData, RankedListingResult

# _SYSTEM = """\
# You are a Swiss real estate agent. Score each listing 0.0–1.0 based on how well it matches \
# the user's soft preferences. Return a JSON array in the same order as the input, each item \
# with "listing_id", "score" (float 0-1), and "reason" (one sentence in English).
# Only use the listing content — do not invent details not present.
# """


def rank_listings(
    candidates: list[dict[str, Any]],
    soft_facts: dict[str, Any],
) -> list[RankedListingResult]:
    if not candidates:
        return []

    # scored = _score_with_claude(candidates, soft_facts)
    # scored.sort(key=lambda x: x["score"], reverse=True)
    # return [
    #     RankedListingResult(
    #         listing_id=str(item["listing_id"]),
    #         score=item["score"],
    #         reason=item["reason"],
    #         listing=_to_listing_data(_find(candidates, item["listing_id"])),
    #     )
    #     for item in scored
    # ]

    return [
        RankedListingResult(
            listing_id=str(c["listing_id"]),
            score=0.0,
            reason=str(soft_facts),
            listing=_to_listing_data(c),
        )
        for c in candidates
    ]


def _score_with_claude(
    candidates: list[dict[str, Any]],
    soft_facts: dict[str, Any],
) -> list[dict[str, Any]]:
    # Build a compact representation of each listing for Claude
    listings_text = json.dumps([
        {
            "listing_id": c["listing_id"],
            "title": c.get("title", ""),
            "description": (c.get("description") or "")[:500],  # cap to save tokens
            "price": c.get("price"),
            "rooms": c.get("rooms"),
            "area": c.get("area"),
            "features": c.get("features", []),
            "city": c.get("city"),
            "distance_public_transport": c.get("distance_public_transport"),
            "distance_shop": c.get("distance_shop"),
            "distance_kindergarten": c.get("distance_kindergarten"),
        }
        for c in candidates
    ], ensure_ascii=False)

    user_message = (
        f"User query: {soft_facts.get('raw_query', '')}\n\n"
        f"Soft preferences: {json.dumps({k: v for k, v in soft_facts.items() if k != 'raw_query'}, ensure_ascii=False)}\n\n"
        f"Listings to score:\n{listings_text}"
    )

    response = _client.messages.create(
        model=SMART_MODEL,
        max_tokens=RANKING_MAX_TOKENS,
        system=_SYSTEM,
        messages=[{"role": "user", "content": user_message}],
    )

    text = next(b.text for b in response.content if b.type == "text")

    # Extract JSON array from response
    start = text.find("[")
    end = text.rfind("]") + 1
    return json.loads(text[start:end])


def _find(candidates: list[dict[str, Any]], listing_id: Any) -> dict[str, Any]:
    return next(c for c in candidates if str(c["listing_id"]) == str(listing_id))


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
