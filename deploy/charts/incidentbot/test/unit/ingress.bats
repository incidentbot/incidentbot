#!/usr/bin/env bats

load _helpers

#--------------------------------------------------------------------
# Ingress

@test "ingress: creates" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/ingress.yaml \
        --set 'ingress.enabled=true' \
        --set 'ingress.hosts[0].host=incidentbot.mydomain.com' \
        --set 'ingress.hosts[0].paths[0].path="/"' \
        --set 'ingress.hosts[0].paths[0].pathType="ImplementationSpecific"' \
        . | tee /dev/stderr |
        yq 'length > 0' | tee /dev/stderr)
    [ "${actual}" = "true" ]
}
