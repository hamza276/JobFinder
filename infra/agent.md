# Infrastructure — Docker Compose

## Services in docker-compose.yml
1. **postgres** — PostgreSQL 15
2. **redis** — Redis 7 (Celery broker + cache)
3. **searxng** — Self-hosted meta-search engine

## SearXNG Configuration (`searxng/settings.yml`)
Key settings:
- `server.secret_key` — set a random string
- `search.formats` — enable `json` format (required for API use)
- Enable engines: google, bing, duckduckgo, indeed, linkedin (if available)
- Set `outgoing.request_timeout` to 10 seconds

## Ports
| Service | Port |
|---|---|
| PostgreSQL | 5432 |
| Redis | 6379 |
| SearXNG | 8888 |
| FastAPI (manual) | 8000 |
| React (manual) | 5173 |

## Starting Infrastructure
```bash
cd infra
docker-compose up -d

# Verify
docker-compose ps
curl http://localhost:8888/search?q=test&format=json   # test SearXNG
```

## Notes
- SearXNG is the only search component in Docker.
- FastAPI and React run directly (not in Docker) in development.
- For production, add Nginx reverse proxy and containerize all services.
- Scrapling runs inside the backend process. Install its browser dependencies with `scrapling install` if you use dynamic or stealth fetch modes.
