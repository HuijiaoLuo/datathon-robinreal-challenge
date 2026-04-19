#!/bin/sh
echo " Starting Cloudflare tunnel..."
mkdir -p /tmp

# Wait for the MCP service to be ready before starting the tunnel
echo "Waiting for MCP service to start..."
sleep 5

# Start the Cloudflare tunnel and extract the public URL
cloudflared tunnel --url http://mcp:8001 2>&1 | while read line; do
    echo "$line"
    # Extract the trycloudflare URL
    echo "$line" | grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com' | head -1 | while read url; do
        if [ ! -z "$url" ]; then
            echo "Found tunnel URL: $url"
            echo "$url" > /tmp/tunnel_url.txt
        fi
    done
done