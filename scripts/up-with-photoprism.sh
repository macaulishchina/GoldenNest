#!/usr/bin/env bash
set -euo pipefail
# Helper to run the project compose together with the external PhotoPrism compose
# Usage:
#   ./scripts/up-with-photoprism.sh up      # bring services up (detached)
#   ./scripts/up-with-photoprism.sh down    # take services down
#   ./scripts/up-with-photoprism.sh logs    # follow logs

COMPOSE_FILES=(docker-compose.yml external/PhotoPrism/compose.yaml)
if ! command -v docker &>/dev/null; then
  echo "docker is required" >&2
  exit 2
fi

CMD=${1:-up}
shift || true

case "$CMD" in
  up)
    docker compose -f "${COMPOSE_FILES[0]}" -f "${COMPOSE_FILES[1]}" up -d "$@"
    ;;
  down)
    docker compose -f "${COMPOSE_FILES[0]}" -f "${COMPOSE_FILES[1]}" down "$@"
    ;;
  logs)
    docker compose -f "${COMPOSE_FILES[0]}" -f "${COMPOSE_FILES[1]}" logs -f "$@"
    ;;
  *)
    echo "Usage: $0 {up|down|logs} [SERVICE...]" >&2
    exit 1
    ;;
esac
