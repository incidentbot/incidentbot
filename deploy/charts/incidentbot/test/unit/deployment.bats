#!/usr/bin/env bats

load _helpers

#--------------------------------------------------------------------
# Deployment

@test "deployment: creates" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        . | tee /dev/stderr |
        yq 'length > 0' | tee /dev/stderr)
    [ "${actual}" = "true" ]
}

@test "deployment: annotations" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        --set 'deploymentAnnotations.someVar=someValue' \
        . | tee /dev/stderr |
        yq -r '.metadata.annotations["someVar"]' | tee /dev/stderr)
    [ "${actual}" = "someValue" ]
}

@test "deployment: args" {
    cd $(chart_dir)
    local object=$(helm template \
        --show-only templates/deployment.yaml \
        --set 'args[0]=echo' \
        --set 'args[1]=test' \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].args' | tee /dev/stderr)

    local actual=$(echo "$object" | yq '.[0]' | tee /dev/stderr)
    [ "${actual}" = "echo" ]

    local actual=$(echo "$object" | yq '.[1]' | tee /dev/stderr)
    [ "${actual}" = "test" ]
}

@test "deployment: command" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        --set 'command[0]=override' \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].command[0]' | tee /dev/stderr)
    [ "${actual}" = "override" ]
}

@test "deployment: extraContainers" {
    cd $(chart_dir)
    local object=$(helm template \
        --show-only templates/deployment.yaml \
        --set 'extraContainers[0].name=test' \
        --set 'extraContainers[0].image=test' \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[1]' | tee /dev/stderr)

    local actual=$(echo "$object" | yq '.name' | tee /dev/stderr)
    [ "${actual}" = "test" ]

    local actual=$(echo "$object" | yq '.image' | tee /dev/stderr)
    [ "${actual}" = "test" ]
}

@test "deployment: extraPodLabels" {
    cd $(chart_dir)
    local object=$(helm template \
        --show-only templates/deployment.yaml \
        --set extraPodLabels.foo=bar \
        .)

    local actual=$(echo "$object" | yq -r '.spec.template.metadata.labels.foo' | tee /dev/stderr)
    [ "${actual}" = "bar" ]
}

@test "deployment: nodeSelector" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        --set 'nodeSelector.foo=bar' \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.nodeSelector.foo' | tee /dev/stderr)
    [ "${actual}" = "bar" ]
}

@test "deployment: podAnnotations" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        --set 'podAnnotations.someVar=someValue' \
        . | tee /dev/stderr |
        yq -r '.spec.template.metadata.annotations.someVar' | tee /dev/stderr)
    [ "${actual}" = "someValue" ]
}

@test "deployment: podSecurityContext" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        --set 'podSecurityContext.runAsUser=1000' \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.securityContext.runAsUser' | tee /dev/stderr)
    [ "${actual}" = "1000" ]
}

@test "deployment: securityContext" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        --set 'securityContext.runAsUser=1000' \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].securityContext.runAsUser' | tee /dev/stderr)
    [ "${actual}" = "1000" ]
}

@test "deployment: tolerations" {
    cd $(chart_dir)
    local object=$(helm template \
        --show-only templates/deployment.yaml \
        --set 'tolerations[0].key=example' \
        --set 'tolerations[0].operator=Exists' \
        --set 'tolerations[0].effect=NoSchedule' \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.tolerations[0]' | tee /dev/stderr)

    local actual=$(echo "$object" | yq '.key' | tee /dev/stderr)
    [ "${actual}" = "example" ]

    local actual=$(echo "$object" | yq '.operator' | tee /dev/stderr)
    [ "${actual}" = "Exists" ]

    local actual=$(echo "$object" | yq '.effect' | tee /dev/stderr)
    [ "${actual}" = "NoSchedule" ]
}

#--------------------------------------------------------------------
# Health Checks

@test "deployment: health checks" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].livenessProbe.initialDelaySeconds' | tee /dev/stderr)
    [ "${actual}" = "10" ]

    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].livenessProbe.periodSeconds' | tee /dev/stderr)
    [ "${actual}" = "30" ]

    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].livenessProbe.timeoutSeconds' | tee /dev/stderr)
    [ "${actual}" = "1" ]

    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].livenessProbe.httpGet.path' | tee /dev/stderr)
    [ "${actual}" = "/api/v1/health" ]

    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].livenessProbe.httpGet.port' | tee /dev/stderr)
    [ "${actual}" = "3000" ]

    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].readinessProbe.initialDelaySeconds' | tee /dev/stderr)
    [ "${actual}" = "10" ]

    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].readinessProbe.periodSeconds' | tee /dev/stderr)
    [ "${actual}" = "30" ]

    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].readinessProbe.timeoutSeconds' | tee /dev/stderr)
    [ "${actual}" = "1" ]

    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].readinessProbe.httpGet.path' | tee /dev/stderr)
    [ "${actual}" = "/api/v1/health" ]

    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].readinessProbe.httpGet.port' | tee /dev/stderr)
    [ "${actual}" = "3000" ]
}

#--------------------------------------------------------------------
# Images

@test "deployment: override image tag" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        --set 'image.tag=1234' \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].image' | tee /dev/stderr)
    [ "${actual}" = "eb129/incidentbot:v1234" ]
}

@test "deployment: override init image tag" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        --set 'init.image.tag=1234' \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.initContainers[1].image' | tee /dev/stderr)
    [ "${actual}" = "eb129/incidentbot:util-v1234" ]
}

@test "deployment: image suffix" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        --set 'image.suffix=arm64' \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].image' | tee /dev/stderr)
    [ "${actual}" = "eb129/incidentbot:v$(chart_version)-arm64" ]
}

@test "deployment: util image suffix" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        --set 'image.suffix=arm64' \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.initContainers[1].image' | tee /dev/stderr)
    [ "${actual}" = "eb129/incidentbot:util-v$(chart_version)-arm64" ]
}

#--------------------------------------------------------------------
# Variables

@test "deployment: envVars render" {
    cd $(chart_dir)
    local object=$(helm template \
        --show-only templates/deployment.yaml \
        --set 'envVars.MYVAR=myVarValue' \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].env[0]' | tee /dev/stderr)

    local actual=$(echo "$object" | yq '.name' | tee /dev/stderr)
    [ "${actual}" = "MYVAR" ]

    local actual=$(echo "$object" | yq '.value' | tee /dev/stderr)
    [ "${actual}" = "myVarValue" ]
}

@test "deployment: config file path is added if create set to true" {
    cd $(chart_dir)
    local object=$(helm template \
        --show-only templates/deployment.yaml \
        --set 'configMap.create=true' \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].env[0]' | tee /dev/stderr)

    local actual=$(echo "$object" | yq '.name' | tee /dev/stderr)
    [ "${actual}" = "CONFIG_FILE_PATH" ]

    local actual=$(echo "$object" | yq '.value' | tee /dev/stderr)
    [ "${actual}" = "/config/release-name-incidentbot/config.yaml" ]
}

@test "deployment: envFromSecret works on main container" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        --set 'envFromSecret.enabled=true' \
        --set 'envFromSecret.secretName=someSecret' \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.containers[0].envFrom[0].secretRef' | tee /dev/stderr)
    [ "${actual}" = "name: someSecret" ]
}

@test "deployment: envFromSecret works on init containers" {
    cd $(chart_dir)
    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        --set 'envFromSecret.enabled=true' \
        --set 'envFromSecret.secretName=someSecret' \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.initContainers[0].envFrom[0].secretRef' | tee /dev/stderr)
    [ "${actual}" = "name: someSecret" ]

    local actual=$(helm template \
        --show-only templates/deployment.yaml \
        --set 'envFromSecret.enabled=true' \
        --set 'envFromSecret.secretName=someSecret' \
        . | tee /dev/stderr |
        yq -r '.spec.template.spec.initContainers[1].envFrom[0].secretRef' | tee /dev/stderr)
    [ "${actual}" = "name: someSecret" ]
}
