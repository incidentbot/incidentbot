#!/usr/bin/env bats

load _helpers

#--------------------------------------------------------------------
# Resources

@test "deployment: default cpu request" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].resources.requests.cpu' | tee /dev/stderr)
    [ "${actual}" = "250m" ]
}

@test "deployment: default memory request" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].resources.requests.memory' | tee /dev/stderr)
    [ "${actual}" = "128M" ]
}

@test "deployment: default cpu limit" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].resources.limits.cpu' | tee /dev/stderr)
    [ "${actual}" = "500m" ]
}

@test "deployment: default memory limit" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].resources.limits.memory' | tee /dev/stderr)
    [ "${actual}" = "512M" ]
}
