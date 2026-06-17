#!/usr/bin/env bash
#
# demo.sh — One-command end-to-end demo of the Therapy Session Analyzer.
#
# What it does:
#   1. Pre-flight checks (Docker, .env with real API keys, a sample video).
#   2. Brings up the full stack with docker compose.
#   3. Waits for the upload + report APIs to be healthy.
#   4. Uploads a video and captures its video_id.
#   5. Watches the pipeline status advance through Mongo:
#        uploaded -> audio_extracted -> transcribed -> analyzed
#   6. Fetches and pretty-prints the final analysis from the report API.
#
# Usage:
#   ./demo.sh [path-to-video]      # defaults to ./sample.mp4
#   ./demo.sh --fresh [video]      # wipe previous data/volumes first
#
set -euo pipefail

# ---------------------------------------------------------------------------
# pretty output
# ---------------------------------------------------------------------------
if [ -t 1 ]; then
  BOLD=$'\033[1m'; DIM=$'\033[2m'; RED=$'\033[31m'; GRN=$'\033[32m'
  YLW=$'\033[33m'; BLU=$'\033[36m'; RST=$'\033[0m'
else
  BOLD=""; DIM=""; RED=""; GRN=""; YLW=""; BLU=""; RST=""
fi
step() { printf "\n${BOLD}${BLU}==> %s${RST}\n" "$*"; }
ok()   { printf "    ${GRN}✔ %s${RST}\n" "$*"; }
info() { printf "    %s\n" "$*"; }
warn() { printf "    ${YLW}! %s${RST}\n" "$*"; }
die()  { printf "\n${RED}✗ %s${RST}\n" "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# args
# ---------------------------------------------------------------------------
FRESH=0
SAMPLE=""
for arg in "$@"; do
  case "$arg" in
    --fresh) FRESH=1 ;;
    *) SAMPLE="$arg" ;;
  esac
done
SAMPLE="${SAMPLE:-sample.mp4}"

cd "$(dirname "$0")"
DC="docker compose"

# ---------------------------------------------------------------------------
# 1. pre-flight
# ---------------------------------------------------------------------------
step "Pre-flight checks"

command -v docker >/dev/null 2>&1 || die "Docker is not installed or not on PATH."
docker compose version >/dev/null 2>&1 || die "Docker Compose v2 is required (got none)."
docker info >/dev/null 2>&1 || die "Docker is installed but the engine isn't running. Start Docker Desktop and re-run."
ok "Docker engine running + Compose available"

if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    die ".env was missing — I created one from .env.example.
       Open .env and set ASSEMBLYAI_API_KEY and GEMINI_API_KEY, then re-run."
  fi
  die ".env is missing and no .env.example to copy from."
fi
# load keys for validation (without polluting the shell beyond what we need)
ASSEMBLYAI_API_KEY="$(grep -E '^ASSEMBLYAI_API_KEY=' .env | tail -1 | cut -d= -f2- || true)"
GEMINI_API_KEY="$(grep -E '^GEMINI_API_KEY=' .env | tail -1 | cut -d= -f2- || true)"
case "$ASSEMBLYAI_API_KEY" in ""|your_assemblyai_key) die "Set a real ASSEMBLYAI_API_KEY in .env";; esac
case "$GEMINI_API_KEY"     in ""|your_gemini_key)     die "Set a real GEMINI_API_KEY in .env";;     esac
ok ".env present with API keys set"

if [ ! -f "$SAMPLE" ]; then
  die "Sample video '$SAMPLE' not found.
       Drop a short therapy-style clip (two speakers) here as sample.mp4,
       or pass a path:  ./demo.sh /path/to/clip.mp4"
fi
ok "Sample video: $SAMPLE ($(du -h "$SAMPLE" | cut -f1))"

need_jq=1; command -v jq >/dev/null 2>&1 || need_jq=0
pp() { if [ "$need_jq" = 1 ]; then jq .; else python3 -m json.tool; fi; }

# ---------------------------------------------------------------------------
# 2. bring up the stack
# ---------------------------------------------------------------------------
if [ "$FRESH" = 1 ]; then
  step "Tearing down previous run (--fresh)"
  $DC down -v --remove-orphans >/dev/null 2>&1 || true
  rm -rf data >/dev/null 2>&1 || true
  ok "Clean slate"
fi

step "Starting the stack (build may take a minute the first time)"
$DC up -d --build
ok "Containers started"
$DC ps --format '    {{.Name}}\t{{.Status}}' 2>/dev/null || true

# ---------------------------------------------------------------------------
# 3. wait for HTTP health
# ---------------------------------------------------------------------------
wait_health() {  # name url
  local name="$1" url="$2" i
  for i in $(seq 1 60); do
    if curl -fs "$url" >/dev/null 2>&1; then ok "$name healthy"; return 0; fi
    sleep 2
  done
  die "$name did not become healthy at $url — check: $DC logs"
}
step "Waiting for services to be healthy"
wait_health "upload_service" "http://localhost:8000/health"
wait_health "report_service" "http://localhost:8001/health"

step "Infrastructure consoles (open these to narrate the demo)"
info "Upload API docs : ${BOLD}http://localhost:8000/docs${RST}"
info "Report API docs : ${BOLD}http://localhost:8001/docs${RST}"
info "RabbitMQ mgmt   : ${BOLD}http://localhost:15672${RST}  ${DIM}(guest / guest)${RST}"
info "MinIO console   : ${BOLD}http://localhost:9001${RST}  ${DIM}(minioadmin / minioadmin)${RST}"

# ---------------------------------------------------------------------------
# 4. upload
# ---------------------------------------------------------------------------
step "Uploading video  ->  POST /videos"
UPLOAD_JSON="$(curl -fs -F "file=@${SAMPLE}" http://localhost:8000/videos)" \
  || die "Upload failed. Logs: $DC logs upload_service"
echo "$UPLOAD_JSON" | pp
VIDEO_ID="$(printf '%s' "$UPLOAD_JSON" | python3 -c 'import sys,json;print(json.load(sys.stdin)["video_id"])')"
[ -n "$VIDEO_ID" ] || die "Could not parse video_id from upload response."
ok "video_id = $VIDEO_ID"

# ---------------------------------------------------------------------------
# 5. watch the pipeline advance (status lives in Mongo's videos collection)
# ---------------------------------------------------------------------------
step "Watching the pipeline (uploaded → audio_extracted → transcribed → analyzed)"
mongo_status() {
  $DC exec -T mongo mongosh therapy_analysis --quiet --eval \
    "const d=db.videos.findOne({video_id:'$VIDEO_ID'}); print(d?d.status:'pending')" 2>/dev/null \
    | tr -d '[:space:]'
}
LAST=""; DEADLINE=$(( $(date +%s) + 600 ))   # up to 10 min for transcription + 3 LLM calls
while :; do
  S="$(mongo_status || true)"
  if [ -n "$S" ] && [ "$S" != "$LAST" ]; then
    printf "    ${DIM}%s${RST}  ${BOLD}%s${RST}\n" "$(date +%H:%M:%S)" "$S"
    LAST="$S"
  fi
  [ "$S" = "analyzed" ] && break
  [ "$S" = "failed" ] && die "Pipeline marked this video as 'failed'. Logs: $DC logs analysis_service"
  [ "$(date +%s)" -ge "$DEADLINE" ] && die "Timed out waiting for analysis. Logs: $DC logs -f"
  sleep 3
done
ok "Analysis complete"

# ---------------------------------------------------------------------------
# 6. fetch the result from the read API
# ---------------------------------------------------------------------------
step "Fetching the report  ->  GET /videos/$VIDEO_ID"
for i in $(seq 1 10); do
  if RESULT="$(curl -fs "http://localhost:8001/videos/$VIDEO_ID")"; then break; fi
  sleep 2
done
[ -n "${RESULT:-}" ] || die "Report API returned nothing. Logs: $DC logs report_service"
echo "$RESULT" | pp

step "Done 🎉"
info "List all analyzed videos:  ${BOLD}curl -s http://localhost:8001/videos | jq .${RST}"
info "Re-run instantly (Redis cache hit):  ${BOLD}./demo.sh${RST}"
info "Stop everything:  ${BOLD}$DC down${RST}   (add -v to also wipe data)"
