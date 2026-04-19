#!/bin/bash
# Usage: ./search.sh "3 room in Zurich" 5

QUERY=${1:-"3 room apartment in Zurich"}
LIMIT=${2:-5}

curl -s -X POST http://localhost:8000/listings \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"$QUERY\", \"limit\": $LIMIT}" | \
  python -c "
import json, sys
d = json.load(sys.stdin)
listings = d.get('listings', [])
print(f'\n🏠 Found {len(listings)} listings for: {d.get(\"meta\", {}).get(\"query\", \"$QUERY\")}\n')
for i, item in enumerate(listings, 1):
    l = item['listing']
    print(f'{i}. {l.get(\"title\", \"N/A\")[:60]}')
    print(f'   📍 {l.get(\"city\", \"N/A\")} | 🛏️ {l.get(\"rooms\", \"N/A\")} rooms | 💰 {l.get(\"price_chf\", \"N/A\")} CHF')
    print(f'   🔗 {l.get(\"original_listing_url\", \"N/A\")}')
    print()
"