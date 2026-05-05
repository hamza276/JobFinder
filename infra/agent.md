# Infrastructure - Docker Compose

## Services In `docker-compose.yml`
1. **postgres** - PostgreSQL 15
2. **redis** - Redis 7 for Celery broker/cache
3. **searxng** - optional local fallback meta-search engine

## SearXNG Configuration
The backend currently defaults to the hosted search endpoint:

```env
SEARXNG_URL=https://searxngapp.app.digitalsgalaxy.com
```

Use the Docker SearXNG service only when testing a local fallback endpoint at `http://localhost:8888`.

For local fallback, `searxng/settings.yml` must keep:
- `search.formats` including `json`, because the backend calls `/search?format=json`.
- Engines that can surface job URLs.
- Reasonable timeout settings so scans do not hang.

## Ports
| Service | Port |
|---|---|
| PostgreSQL | 5432 |
| Redis | 6379 |
| SearXNG local fallback | 8888 |
| FastAPI manual run | 8000 |
| React manual run | 5173 |

## Starting Local Infrastructure
```powershell
cd infra
docker compose up -d

# Verify local fallback SearXNG
curl http://localhost:8888/search?q=test&format=json
```

## Notes
- The production/default search component is the hosted SearXNG URL in backend config.
- Docker SearXNG is optional local fallback infrastructure.
- FastAPI and React run directly in development.
- Scrapling scraping runs through `https://scraplingbackend.app.digitalsgalaxy.com`; no local Scrapling browser install is required.
- If infrastructure behavior changes, update this `agent.md` in the same task.
