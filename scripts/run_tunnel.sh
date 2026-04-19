#!/bin/sh
echo "启动 Cloudflare 隧道..."
mkdir -p /tmp

# 等待 MCP 服务启动
echo "等待 MCP 服务启动..."
sleep 5

# 运行隧道
cloudflared tunnel --url http://mcp:8001 2>&1 | while read line; do
    echo "$line"
    # 提取 trycloudflare URL
    echo "$line" | grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com' | head -1 | while read url; do
        if [ ! -z "$url" ]; then
            echo "发现隧道 URL: $url"
            echo "$url" > /tmp/tunnel_url.txt
        fi
    done
done