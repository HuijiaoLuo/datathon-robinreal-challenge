#!/bin/bash
# 使用方法: ./search_public.sh "3 room in Zurich" 5

QUERY=${1:-"3 room apartment in Zurich"}
LIMIT=${2:-5}
# 使用你自己的 MCP 公网链接
PUBLIC_URL="https://princeton-sage-handheld-trunk.trycloudflare.com"

echo "🔍 Searching: $QUERY"
echo "📍 Using: $PUBLIC_URL"
echo ""

# 调用 MCP 搜索
curl -s -X POST "$PUBLIC_URL/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"id\": 1,
    \"method\": \"tools/call\",
    \"params\": {
      \"name\": \"search_listings\",
      \"arguments\": {
        \"query\": \"$QUERY\",
        \"limit\": $LIMIT
      }
    }
  }" | grep '^data: ' | head -1 | sed 's/^data: //' | \
  python -c "
import json, sys
try:
    data = json.load(sys.stdin)
    content = data.get('result', {}).get('content', [])
    if content:
        print(content[0].get('text', 'No results'))
    elif data.get('error'):
        print(f\"❌ Error: {data['error']}\")
    else:
        print('❌ No listings found')
except Exception as e:
    print(f'❌ Parse error: {e}')
"