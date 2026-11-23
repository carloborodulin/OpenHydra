#!/usr/bin/env bash
# Pull a sample from each FBI CDE API endpoint family so we can see the data
# shapes. Re-run to refresh data/samples/. A failed request keeps the old file.
#
# Usage: ./explore.sh
set -uo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

# --- config ------------------------------------------------------------------
# Read only the two named keys from .env. Do not source the file: that runs it
# as shell code and exports every value to each child process. A value that is
# already in the environment wins over the file.
env_value () {
  local name="$1" file="$ROOT/.env"
  [[ -f "$file" ]] || return 0
  grep -E "^[[:space:]]*${name}=" "$file" | tail -n 1 | cut -d= -f2- \
    | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'$/\1/"
}
BASE="${FBI_CDE_BASE_URL:-$(env_value FBI_CDE_BASE_URL)}"
BASE="${BASE:-https://api.usa.gov/crime/fbi/cde}"
KEY="${FBI_CDE_API_KEY:-$(env_value FBI_CDE_API_KEY)}"
: "${KEY:?set FBI_CDE_API_KEY in the environment or in .env}"

OUT="$ROOT/data/samples"
mkdir -p "$OUT"
LOG_TMP="$(mktemp "$OUT/.manifest.XXXXXX")"
trap 'rm -f "$LOG_TMP" "$OUT"/.*.part' EXIT
printf "name\tstatus\tbytes\tendpoint\n" >> "$LOG_TMP"

# pull <name> <path-with-query-but-no-key>
# The URL (with the key) goes to curl on stdin as a config line, so the key is
# not in the process list. Each sample is written to a temporary file and moved
# into place only after a successful response.
pull () {
  local name="$1" path="$2" sep="?"
  [[ "$path" == *\?* ]] && sep="&"
  local file="${OUT}/${name}.json" part="${OUT}/.${name}.part" code
  code=$(printf 'url = "%s%s%sAPI_KEY=%s"\n' "$BASE" "$path" "$sep" "$KEY" \
    | curl -sS --fail --retry 6 --retry-delay 2 --retry-all-errors \
           -K - -o "$part" -w "%{http_code}" 2>/dev/null)
  local rc=$?
  if [[ $rc -eq 0 && -s "$part" ]]; then
    mv -f "$part" "$file"
  else
    rm -f "$part"
    code="${code:-000} (kept old file)"
  fi
  local bytes=0
  [[ -f "$file" ]] && bytes=$(wc -c < "$file" | tr -d ' ')
  printf "%-46s %s  %7sB\n" "$name" "$code" "$bytes"
  printf "%s\t%s\t%s\t%s\n" "$name" "${code%% *}" "$bytes" "$path" >> "$LOG_TMP"
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

echo "== Police employment (PE / LEOKA): uses 4-digit years, not MM-YYYY =="
# The canonical paths are /pe and /pe/{state}. The /pe/national and
# /pe/state/{ST} variants answer 200 with all-null values.
pull pe_national                  "/pe?from=2018&to=2022"
pull pe_state_NY                  "/pe/NY?from=2018&to=2022"

mv -f "$LOG_TMP" "$OUT/_manifest.tsv"
echo
echo "Done. Manifest: $OUT/_manifest.tsv"
