#!/bin/bash

set -euo pipefail

cNone='\033[00m'
cRed='\033[01;31m'
cGreen='\033[01;32m'

CHART_REPOSITORY_URL="https://charts.echoboomer.net"
CHART_REPOSITORY_NAME="echoboomer-charts"

# Directory for chart source.
cd deploy/charts

# Enable helm cm-push.
helm plugin install https://github.com/chartmuseum/helm-push.git
echo

echo -e "${cGreen}[!] Analyzing and packaging Helm charts..."

echo -e "${cGreen}[!] Adding Helm repository...${cNone}"

# Add repo.
helm repo add $CHART_REPOSITORY_NAME $CHART_REPOSITORY_URL --username "$HELM_REPO_USER" --password "$HELM_REPO_PASS"
echo
helm repo update
echo

# Lint all charts and add dependencies if there are any.
if [ "$CIRCLE_BRANCH" != "main" ]; then
    echo -e "${cGreen}[!] Linting charts...${cNone}"
    echo
    for f in $(ls .); do
        helm dependency build "$f"
        echo
        helm lint ${f}
        echo
    done
    echo
fi

# Run tests if present.
if [ "$CIRCLE_BRANCH" != "main" ]; then
    echo -e "${cGreen}[!] Checking for chart unit tests...${cNone}"
    echo
    for f in $(ls .); do
        if [[ -d "$f/test" ]]; then
            echo -e "${cGreen}[!] Running unit tests for $f...${cNone}"
            bats "$f/test/unit"
            echo
        else
            echo "No unit tests found for $f."
            echo
        fi
    done
    echo
fi


# Package on merge.
if [ "$CIRCLE_BRANCH" = "main" ]; then
    echo -e "${cGreen}[!] Packaging charts...${cNone}"
    for f in $(ls .); do
        CHART_VERSION=$(helm show chart $f | grep '^version' | sed 's/^version: //')
        helm cm-push "$f" $CHART_REPOSITORY_NAME
        echo
    done
    echo
fi
