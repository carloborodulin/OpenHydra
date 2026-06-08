#!/usr/bin/env bash
# Pull a sample from each FBI CDE API endpoint family so we can see the data
# shapes and plan a project. Idempotent: re-run to refresh data/samples/.
#
# Usage: ./explore.sh
set -uo pipefail

# --- load config from .env -------------------------------------------------
set -a; source "$(dirname "$0")/.env"; set +a
BASE="${FBI_CDE_BASE_URL:?set FBI_CDE_BASE_URL in .env}"
KEY="${FBI_CDE_API_KEY:?set FBI_CDE_API_KEY in .env}"

OUT="$(dirname "$0")/data/samples"
mkdir -p "$OUT"
LOG="$OUT/_manifest.tsv"
: > "$LOG"
printf "name\tstatus\tbytes\tendpoint\n" >> "$LOG"

# pull <name> <path-with-query-but-no-key>
# Survives the gateway's intermittent 503s via curl --retry.
pull () {
  local name="$1" path="$2" sep="?"
  [[ "$path" == *\?* ]] && sep="&"
  local url="${BASE}${path}${sep}API_KEY=${KEY}"
  local file="${OUT}/${name}.json"
  local code
  code=$(curl -s --retry 6 --retry-delay 2 --retry-all-errors \
              -o "$file" -w "%{http_code}" "$url")
  local bytes; bytes=$(wc -c < "$file" | tr -d ' ')
  printf "%-46s %s  %7sB\n" "$name" "$code" "$bytes"
  printf "%s\t%s\t%s\t%s\n" "$name" "$code" "$bytes" "$path" >> "$LOG"
  sleep 1   # be polite to the gateway
}

echo "== Agencies =="
pull agency_by_state_NY        "/agency/byStateAbbr/NY"

echo "== Summarized (counts known to law enforcement) =="
for off in violent-crime homicide rape robbery aggravated-assault \
           property-crime burglary larceny motor-vehicle-theft arson; do
  pull "summarized_national_${off//-/_}" "/summarized/national/${off}?from=01-2020&to=12-2022"
done
pull summarized_state_NY_violent  "/summarized/state/NY/violent-crime?from=01-2020&to=12-2022"
pull summarized_agency_violent    "/summarized/agency/NY0303000/violent-crime?from=01-2020&to=12-2022"

echo "== Arrests (type = totals | counts) =="
pull arrest_national_all_totals   "/arrest/national/all?type=totals&from=01-2020&to=12-2022"
pull arrest_national_all_counts   "/arrest/national/all?type=counts&from=01-2020&to=12-2022"
pull arrest_state_NY_all          "/arrest/state/NY/all?type=totals&from=01-2020&to=12-2022"

echo "== Police employment (PE / LEOKA) -- NB: uses 4-digit YEARS, not MM-YYYY =="
pull pe_national                  "/pe/national?from=2018&to=2022"
pull pe_state_NY                  "/pe/state/NY?from=2018&to=2022"

# NOTE: /estimate/* and /nibrs/* demographic routes return 404 on this `cde`
# base with every path variant tried (they appear to live on the legacy
# `sapi` base / Swagger UI). Revisit if we need national estimates or
# incident-level NIBRS victim/offender demographics.

echo
echo "Done. Manifest: $LOG"
