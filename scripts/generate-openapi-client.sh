#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONSOLE_DIR="${CONSOLE_DIR:-${REPO_ROOT}/../console}"

if [[ ! -d "${CONSOLE_DIR}" ]]; then
    echo "console directory not found: ${CONSOLE_DIR}"
    exit 1
fi

cd "${REPO_ROOT}"
poetry run python -c "import incidentbot.api.main; import json; print(json.dumps(incidentbot.api.main.app.openapi()))" > openapi.json
mv openapi.json "${CONSOLE_DIR}/openapi.json"

cd "${CONSOLE_DIR}"
npm run generate-client
npx biome format --write ./src/client
