# Services — Business Logic Layer

## Rule: Services are Pure Python
No FastAPI imports. No Request/Response objects. Only:
- SQLAlchemy sessions (passed in as argument)
- Pydantic models or dataclasses
- Other service classes

## Service Subdirectories
| Folder | Responsibility |
|---|---|
| `fetcher/` | ReAct agent + SearXNG + hosted Scrapling pipeline |
| `parser/` | JD text extraction + email finding |
| `llm/` | LLM provider abstraction + email composer |
| `scheduler/` | Daily scan orchestration |
| `fetcher/quality.py` | Deterministic relevance gates and score calibration |

## Dependency Flow
```
routes/ → services/ → llm/base.py
                    → fetcher/ → searxng_client.py
                               → scrapling_client.py
                    → parser/
                    → models/
```

## Error Handling in Services
- Services raise domain-specific exceptions (e.g., `ScrapingError`, `LLMError`, `JobNotFoundError`)
- Routes catch these and convert to appropriate `HTTPException`
- Never let raw library exceptions (e.g., `groq.APIError`) leak to routes

## Documentation Rule
- Whenever a service module changes, update the nearest relevant `agent.md` in the same task.
- Quality/scoring changes must be reflected in `fetcher/agent.md`.
