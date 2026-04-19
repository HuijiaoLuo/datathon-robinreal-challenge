# # app/participant/hard_fact_extraction.py
# import re
# from typing import Any, Dict, List
# from app.models.schemas import HardFilters

# SWISS_CITIES = {
#     "zurich": "Zurich", "zürich": "Zurich", 
#     "geneva": "Geneva", "genève": "Geneva", "genf": "Geneva",
#     "basel": "Basel", "bern": "Bern", "lausanne": "Lausanne",
#     "winterthur": "Winterthur", "luzern": "Luzern", "lucerne": "Luzern",
#     "st. gallen": "St. Gallen", "sankt gallen": "St. Gallen", "lugano": "Lugano",
#     "biel": "Biel", "biel/bienne": "Biel", "thun": "Thun", "zug": "Zug"
# }

# def extract_hard_facts(query: str) -> HardFilters:
#     facts: Dict[str, Any] = {}
#     query_lower = query.lower()

#     # city
#     for key, city in SWISS_CITIES.items():
#         if key in query_lower:
#             facts["city"] = [city]
#             break

#     # rooms
#     room_match = re.search(r'(\d+(?:\.\d+)?)\s*[- ]?(?:room|rooms|zimmer|pièces|pièce)', query_lower)
#     if room_match:
#         rooms = float(room_match.group(1))
#         facts["min_rooms"] = max(0, rooms - 0.5) if rooms == int(rooms) else rooms
#         facts["max_rooms"] = rooms + 0.5 if rooms == int(rooms) else rooms

#     # prize
#     max_price = re.search(r'(?:under|below|max|up to|less than)\s*(\d+)', query_lower)
#     if max_price:
#         facts["max_price"] = int(max_price.group(1))
    
#     min_price = re.search(r'(?:over|above|min|at least|from)\s*(\d+)', query_lower)
#     if min_price:
#         facts["min_price"] = int(min_price.group(1))

#     # features
#     features = []
#     for kw, feat in {"balcony": "balcony", "elevator": "elevator", "lift": "elevator",
#                      "garage": "garage", "parking": "parking", "garden": "garden"}.items():
#         if kw in query_lower:
#             features.append(feat)
#     if features:
#         facts["features"] = features

#     facts["offer_type"] = "RENT"  # assume rental for now, could be extended to detect sales
#     return HardFilters(**facts)

# app/participant/hard_fact_extraction.py
import re
from typing import Any, Dict, List
from app.models.schemas import HardFilters
from app.participant.location_index import build_location_index, search_location


def extract_hard_facts(query: str) -> HardFilters:
    facts: Dict[str, Any] = {}
    query_lower = query.lower()
    
    # 确保位置索引已加载
    build_location_index()

    # 1. 使用 CSV 索引进行位置匹配
    location_match = search_location(query)
    if location_match:
        matched_key, city_name = location_match
        facts["city"] = [city_name]
        print(f"📍 Matched '{matched_key}' → {city_name}")

    # 2. 房间数提取
    room_match = re.search(r'(\d+(?:\.\d+)?)\s*[- ]?(?:room|rooms|zimmer|pièces|pièce)', query_lower)
    if room_match:
        rooms = float(room_match.group(1))
        if rooms == int(rooms):
            facts["min_rooms"] = max(0, rooms - 0.5)
            facts["max_rooms"] = rooms + 0.5
        else:
            facts["min_rooms"] = rooms
            facts["max_rooms"] = rooms

    # 3. 价格提取
    max_price = re.search(r'(?:under|below|max|up to|less than|bis)\s*(\d+(?:[.,]\d+)?)', query_lower)
    if max_price:
        facts["max_price"] = int(float(max_price.group(1).replace(',', '')))
    
    min_price = re.search(r'(?:over|above|min|at least|from|ab)\s*(\d+(?:[.,]\d+)?)', query_lower)
    if min_price:
        facts["min_price"] = int(float(min_price.group(1).replace(',', '')))
    
    range_match = re.search(r'(\d+)\s*[-–]\s*(\d+)\s*(?:CHF|chf)?', query_lower)
    if range_match:
        facts["min_price"] = int(range_match.group(1))
        facts["max_price"] = int(range_match.group(2))

    # 4. 邮政编码
    postal_match = re.search(r'\b(\d{4})\b', query)
    if postal_match:
        facts["postal_code"] = [postal_match.group(1)]

    # 5. 特性提取
    feature_keywords = {
        "balcony": "balcony", "balkon": "balcony",
        "elevator": "elevator", "lift": "elevator", "aufzug": "elevator",
        "garage": "garage", "parking": "parking", "parkplatz": "parking",
        "garden": "garden", "garten": "garden",
        "furnished": "furnished", "möbliert": "furnished",
        "wheelchair": "wheelchair_accessible", "rollstuhl": "wheelchair_accessible",
        "dishwasher": "dishwasher", "geschirrspüler": "dishwasher",
        "washing machine": "private_laundry", "waschmaschine": "private_laundry",
        "fireplace": "fireplace", "cheminée": "fireplace", "kamin": "fireplace",
        "pets": "pets_allowed", "haustiere": "pets_allowed",
        "child": "child_friendly", "kinder": "child_friendly",
    }
    
    features = []
    for kw, feat in feature_keywords.items():
        if kw in query_lower:
            features.append(feat)
    if features:
        facts["features"] = list(set(features))

    facts["offer_type"] = "RENT"
    return HardFilters(**facts)