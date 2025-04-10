#!/bin/bash

files=(
    "version"
    "./incidentbot/configuration/settings.py"
    "pyproject.toml"
)

CURRENT=$(cat version)
CURRENT_NO_V_PREFIX=$(echo $CURRENT | sed 's/^v//')
NEXT=$1
NEXT_NO_V_PREFIX=$(echo $NEXT | sed 's/^v//')

if [[ "$CURRENT" == "$NEXT" ]]; then
    echo "already at this version"
    exit 0
fi

for file in ${files[@]}; do
    if [ -f "$file" ]; then
        sed -i '' "s/$CURRENT_NO_V_PREFIX/$NEXT_NO_V_PREFIX/g" "$file"
        echo "updated $file"
    else
        echo "skipping $file (file not found)"
    fi
done

echo "don't forget to update pyproject.toml manually"
