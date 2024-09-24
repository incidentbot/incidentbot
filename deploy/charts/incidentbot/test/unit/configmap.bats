#!/usr/bin/env bats

load _helpers

#--------------------------------------------------------------------
# ConfigMap

@test "configmap: no configmap created by default" {
    cd $(chart_dir)
    run helm template \
        --show-only templates/configmap.yaml .
    [ "$status" -eq 1 ]
}

@test "configmap: created with data" {
    cd $(chart_dir)
    local object=$(helm template \
        --show-only templates/configmap.yaml \
        --set 'configMap.create=true' \
        --set 'configMap.data.foo=bar' \
        . | tee /dev/stderr |
        yq -r '.' | tee /dev/stderr)

    local actual=$(echo "$object" | yq '.data["config.yaml"]' | tee /dev/stderr)
    [ "${actual}" = "foo: bar" ]
}
