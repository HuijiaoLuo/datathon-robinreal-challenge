# Deployment Guide

## Quick Start

```bash
unzip raw_data.zip -d raw_data/
docker compose up -d --build
curl http://localhost:8000/health

./search.sh "Zurich apartment" 5
./search_public.sh "apartment in Zurich" 5

cloudflared tunnel --url http://localhost:8001

{
  "mcpServers": {
    "datathon": {
      "url": "http://localhost:8001/mcp",
      "type": "sse"
    }
  }
}

docker compose logs -f api
docker compose restart
docker compose down -v && docker compose up -d --build

docker-compose.yml
search.sh
search_public.sh
app/
apps_sdk/
raw_data/
