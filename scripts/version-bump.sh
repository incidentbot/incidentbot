#!/bin/bash

files=(
    "version"
    "./deploy/charts/incidentbot/Chart.yaml"
    "./docs/deploy/overlays/production/kustomization.yaml"
    "./incidentbot/configuration/settings.py"
)

CURRENT=$(cat version)
CURRENT_NO_V_PREFIX=$(echo $CURRENT | sed 's/\v//g')
NEXT=$1
NEXT_NO_V_PREFIX=$(echo $NEXT | sed 's/\v//g')

if [[ "$CURRENT" == "$NEXT" ]]; then
    echo "already at this version"
    exit 0
fi

for file in ${files[@]}; do
    sed -i '' "s/$CURRENT_NO_V_PREFIX/$NEXT_NO_V_PREFIX/g" ${file}
    echo "updated ${file}"
done

echo "don't forget to update pyproject.toml manually"
