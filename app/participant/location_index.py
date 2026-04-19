# app/participant/location_index.py
import csv
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 缓存
_location_index: Optional[Dict[str, str]] = None
_postal_to_city: Optional[Dict[str, str]] = None

# 手动区域别名（补充 CSV 中没有的区域名）
DISTRICT_ALIASES: Dict[str, str] = {
    # Zürich 区域
    "oerlikon": "Zurich",
    "örlikon": "Zurich",
    "altstetten": "Zurich",
    "wiedikon": "Zurich",
    "wollishofen": "Zurich",
    "leimbach": "Zurich",
    "enge": "Zurich",
    "friesenberg": "Zurich",
    "sihlfeld": "Zurich",
    "aussersihl": "Zurich",
    "kreis 4": "Zurich", "k4": "Zurich",
    "langstrasse": "Zurich",
    "hard": "Zurich",
    "industriequartier": "Zurich",
    "kreis 5": "Zurich", "k5": "Zurich",
    "escher-wyss": "Zurich",
    "unterstrass": "Zurich",
    "oberstrass": "Zurich",
    "kreis 6": "Zurich", "k6": "Zurich",
    "fluntern": "Zurich",
    "hottingen": "Zurich",
    "hirslanden": "Zurich",
    "witikon": "Zurich",
    "kreis 7": "Zurich", "k7": "Zurich",
    "riesbach": "Zurich",
    "seefeld": "Zurich",
    "kreis 8": "Zurich", "k8": "Zurich",
    "albisrieden": "Zurich",
    "kreis 9": "Zurich", "k9": "Zurich",
    "höngg": "Zurich", "hongg": "Zurich",
    "wipkingen": "Zurich",
    "kreis 10": "Zurich", "k10": "Zurich",
    "affoltern": "Zurich",
    "seebach": "Zurich",
    "kreis 11": "Zurich", "k11": "Zurich",
    "schwamendingen": "Zurich",
    "kreis 12": "Zurich", "k12": "Zurich",
    "zürich west": "Zurich", "zurich west": "Zurich",
    "zürich nord": "Zurich", "zurich nord": "Zurich",
    
    # Basel 区域
    "grossbasel": "Basel",
    "kleinbasel": "Basel",
    
    # Bern 区域
    "bümpliz": "Bern", "bumpliz": "Bern",
    "lorraine": "Bern",
    
    # Geneva 区域
    "paquis": "Geneva", "pâquis": "Geneva",
    "eaux-vives": "Geneva",
    
    # Winterthur 区域
    "oberwinterthur": "Winterthur",
    "seen": "Winterthur",
    "töss": "Winterthur", "toss": "Winterthur",
    "wülflingen": "Winterthur", "wulflingen": "Winterthur",
}


def build_location_index(csv_path: Optional[Path] = None) -> Dict[str, str]:
    global _location_index, _postal_to_city
    
    if _location_index is not None:
        return _location_index
    
    if csv_path is None:
        csv_path = Path(__file__).parent.parent.parent / "raw_data" / "AMTOVZ_CSV_LV95.csv"
    
    location_index: Dict[str, str] = {}
    postal_to_city: Dict[str, str] = {}
    
    # 1. 先加载手动区域别名
    for alias, city in DISTRICT_ALIASES.items():
        location_index[alias.lower()] = city
        # 添加简化变体
        simple = alias.lower().replace('ä', 'a').replace('ö', 'o').replace('ü', 'u')
        simple = simple.replace('é', 'e').replace('è', 'e').replace('ê', 'e')
        location_index[simple] = city
    
    print(f"✅ Loaded {len(DISTRICT_ALIASES)} district aliases")
    
    # 2. 加载 CSV
    if csv_path.exists():
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                ortschaft = row.get('Ortschaftsname', '').strip()
                plz = row.get('PLZ4', '').strip()
                gemeinde = row.get('Gemeindename', '').strip()
                
                if not ortschaft:
                    continue
                
                city_name = gemeinde if gemeinde else ortschaft
                
                # 添加原始地名
                location_index[ortschaft.lower()] = city_name
                
                # 简化变体
                simplified = ortschaft.lower()
                simplified = simplified.replace('ä', 'a').replace('ö', 'o').replace('ü', 'u')
                simplified = simplified.replace('é', 'e').replace('è', 'e').replace('ê', 'e')
                location_index[simplified] = city_name
                
                # 处理复合名称的每个部分
                parts = ortschaft.split()
                if len(parts) > 1:
                    for part in parts:
                        if len(part) >= 3 and not part.isdigit():
                            location_index[part.lower()] = city_name
                            part_simple = part.lower().replace('ä', 'a').replace('ö', 'o').replace('ü', 'u')
                            location_index[part_simple] = city_name
                
                # 邮政编码
                if plz:
                    postal_to_city[plz] = city_name
    
    _location_index = location_index
    _postal_to_city = postal_to_city
    print(f"✅ Total location entries: {len(location_index)}")
    return location_index


def search_location(query: str) -> Optional[Tuple[str, str]]:
    index = build_location_index()
    query_lower = query.lower()
    
    # 1. 邮政编码
    postal_match = re.search(r'\b(\d{4})\b', query)
    if postal_match:
        plz = postal_match.group(1)
        if _postal_to_city and plz in _postal_to_city:
            return (plz, _postal_to_city[plz])
    
    # 2. 按长度降序匹配
    sorted_keys = sorted(index.keys(), key=len, reverse=True)
    for key in sorted_keys:
        if key in query_lower:
            if _is_word_boundary(key, query_lower):
                return (key, index[key])
    
    return None


def _is_word_boundary(key: str, text: str) -> bool:
    idx = text.find(key)
    if idx == -1:
        return False
    left_ok = idx == 0 or not text[idx-1].isalpha()
    right_ok = idx + len(key) == len(text) or not text[idx+len(key)].isalpha()
    return left_ok and right_ok


def get_city_from_postal(plz: str) -> Optional[str]:
    if _postal_to_city is None:
        build_location_index()
    return _postal_to_city.get(plz)