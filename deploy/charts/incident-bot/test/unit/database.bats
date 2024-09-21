#!/usr/bin/env bats

load _helpers

#--------------------------------------------------------------------
# Database

@test "database: creates deployment if enabled" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/database-deployment.yaml \
        --set 'database.enabled=true' \
        --set 'database.password=somepassword' \
        . | tee /dev/stderr |
        yq 'length > 0' | tee /dev/stderr)
    [ "${actual}" = "true" ]
}

@test "database: creates service if enabled" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/database-service.yaml \
        --set 'database.enabled=true' \
        --set 'database.password=somepassword' \
        . | tee /dev/stderr |
        yq 'length > 0' | tee /dev/stderr)
    [ "${actual}" = "true" ]
}
