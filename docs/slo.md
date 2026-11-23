# Service objectives

These objectives are the starting point. Measure for one month before you
use them for alerts. The uptime workflow (`.github/workflows/uptime.yml`)
checks the public service every 30 minutes and opens an issue on a failure.

| Objective | Target | Measured by |
|---|---|---|
| Warehouse availability | 99.9% of checks per month answer 200 (`/health`, `/api/meta`, one metric route, `/`) | uptime workflow |
| Warehouse latency | 95% of warehouse requests under 500 ms | Railway HTTP logs (`duration_ms` in the JSON access log) |
| Live agency data | Not an objective of this service: it depends on the FBI CDE API. Errors have stable codes (see `api/README.md`). | access log `upstream` field |
| FBI API contract | The routes that the extract uses answer once a day | fbi-contract workflow |
| Data freshness | A data release each month, after review | data-refresh workflow and its issue |

## What happens on a failure

1. The workflow opens an issue (or adds a comment to the open one).
2. Check `/health`: a 503 names the mart that is missing or empty.
3. Check the Railway deploy and its logs (each request has a request ID).
4. To roll back, redeploy the last good deployment in Railway.

GitHub stops scheduled workflows in a repository with no activity for 60
days. Check the Actions tab after a quiet period.
