#!/bin/bash

files=(
  "version"
  "./backend/config.py"
  "./deploy/kustomize/incident-bot/overlays/production/kustomization.yaml"
  "./docs/deploy/overlays/production/kustomization.yaml"
)

CURRENT=`cat version`
NEXT=$1

if [[ "$CURRENT" == "$NEXT" ]]; then
  echo "already at this version"
  exit 0
fi

for file in ${files[@]}; do
  sed -i '' "s/$CURRENT/$NEXT/g" ${file}
  echo "updated ${file}"
done
