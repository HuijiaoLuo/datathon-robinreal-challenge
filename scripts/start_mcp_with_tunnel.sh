#!/bin/sh
echo "等待隧道 URL..."
# 等待隧道文件出现，最多等待 30 秒
TIMEOUT=30
COUNTER=0
while [ ! -f /tmp/tunnel_url.txt ] || [ ! -s /tmp/tunnel_url.txt ]; do
    echo "等待 cloudflared 生成隧道 URL... (${COUNTER}/${TIMEOUT})"
    sleep 2
    COUNTER=$((COUNTER + 1))
    if [ $COUNTER -ge $TIMEOUT ]; then
        echo "超时，使用 localhost 作为公网地址"
        TUNNEL_URL="http://localhost:8001"
        break
    fi
done

if [ -f /tmp/tunnel_url.txt ] && [ -s /tmp/tunnel_url.txt ]; then
    TUNNEL_URL=$(cat /tmp/tunnel_url.txt)
fi

echo "获取到隧道 URL: $TUNNEL_URL"

export APPS_SDK_PUBLIC_BASE_URL=$TUNNEL_URL
export APPS_SDK_LISTINGS_API_BASE_URL=http://api:8000
export APPS_SDK_PORT=8001

echo "启动 MCP 服务器"
echo "公网地址: $APPS_SDK_PUBLIC_BASE_URL"
echo "API 地址: $APPS_SDK_LISTINGS_API_BASE_URL"

exec uvicorn apps_sdk.server.main:app --host 0.0.0.0 --port 8001