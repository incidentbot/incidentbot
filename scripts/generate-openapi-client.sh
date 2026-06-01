#! /usr/bin/env bash

set -e
set -x

python -c "import incidentbot.api.main; import json; print(json.dumps(incidentbot.api.main.app.openapi()))" > openapi.json
mv openapi.json ../console
cd ../console
npm run generate-client
npx biome format --write ./src/client
