#!/bin/bash

files=(
  "version"
  "./backend/config.py"
  "./deploy/kustomize/incident-bot/overlays/production/kustomization.yaml"
  "./docs/setup.md"
  "./docs/deploy/overlays/production/kustomization.yaml"
)

for file in ${files[@]}; do
  sed -i '' "s/$1/$2/g" ${file}
  echo "updated ${file}"
done
