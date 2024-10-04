# Incident Bot Helm Chart

A Helm chart for deploying Incident Bot to Kubernetes.

https://docs.incidentbot.io/installation/#helm

## Configuration

| Parameter                         | Description                                                                                                        | Default                          |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------ | -------------------------------- |
| `affinity`                        | Affinity configuration for the `Deployment`.                                                                       | `{}`                             |
| `args`                            | A list of `args` to supply to the main process container.                                                          | `[]`                             |
| `command`                         | A `command` to supply to the main process container.                                                               | `[]`                             |
| `configMap.create`                | Whether or not to create the `ConfigMap` that will be mounted for application configuration.                       | `false`                          |
| `configMap.data`                  | If creating a `ConfigMap`, it's `yaml` data.                                                                       | `{}`                             |
| `database.enabled`                | Whether or not to enable the built-in database.                                                                    | `false`                          |
| `database.user`                   | The username to use if creating the built-in database. Passed as the `POSTGRES_USER` env to the database `Pod`.    | `incident_bot`                   |
| `database.password`               | The password for the built-in database.                                                                            | `null`                           |
| `deploymentAnnotations`           | Annotations to apply to the `Deployment`.                                                                          | `{}`                             |
| `envFromSecret.enabled`           | Whether or not to mount environment variables in the main process containers and init containers using a `Secret`. | `false`                          |
| `envFromSecret.secretName`        | The name of the `Secret` to use if setting `envFromSecret.enabled` to `true`.                                      | `null`                           |
| `envVars`                         | Variables in the format `KEY: value` to supply to the main process containers.                                     | `{}`                             |
| `extraContainers`                 | A list of raw `yaml` specifying any additional containers to create alongside the main one.                        | `[]`                             |
| `extraPodLabels`                  | A list of raw `yaml` specifying any additional labels to add to the `pod`.                                         | `{}`                             |
| `healthCheck.enabled`             | Whether or not to enable the health check for the main process container.                                          | `true`                           |
| `healthCheck.path`                | The path to use for the health check.                                                                              | `/api/v1/health`                 |
| `healthCheck.scheme`              | The health check scheme.                                                                                           | `HTTP`                           |
| `healthCheck.initialDelaySeconds` |                                                                                                                    | `10`                             |
| `healthCheck.periodSeconds`       |                                                                                                                    | `30`                             |
| `healthCheck.timeoutSeconds`      |                                                                                                                    | `1`                              |
| `image.repository`                | Image repository to pull from.                                                                                     | `eb129/incidentbot`              |
| `image.pullPolicy`                |                                                                                                                    | `Always`                         |
| `image.suffix`                    | Whether or not to apply a suffix to the image. Useful if using `arm64`.                                            | `null`                           |
| `image.tag`                       | Override the image tag. Will prefix with `v`.                                                                      | `null`                           |
| `imagePullSecrets`                | A list of pull secrets to apply to the `Deployment`.                                                               | `[]`                             |
| `ingress.enabled`                 | Whether or not to enable the `Ingress`.                                                                            | `false`                          |
| `ingress.className`               | `Ingress` class name.                                                                                              | `''`                             |
| `ingress.annotations`             |                                                                                                                    | `{}`                             |
| `ingress.hosts`                   | Host configuration for `Ingress`.                                                                                  | See `values.yaml`                |
| `ingress.tls`                     | TLS configuration for `Ingress`.                                                                                   | `[]`                             |
| `init.enabled`                    | Whether or not to enable init container for checking for and running database migrations..                         | `true`                           |
| `init.command`                    | The `command` to supply to the `init` container.                                                                   | `['/bin/sh']`                    |
| `init.args`                       | The `args` to supply to the `init` container.                                                                      | `['-c', 'alembic upgrade head']` |
| `init.image.tag`                  | Override tag used for `init` container image.                                                                      | `null`                           |
| `nodeSelector`                    |                                                                                                                    | `{}`                             |
| `podAnnotations`                  | Annotations to apply directly to the `Pod` spawned by the `Deployment`.                                            | `{}`                             |
| `podSecurityContext`              | Security context for the `Pod`.                                                                                    | `{}`                             |
| `resources.limits.cpu`            |                                                                                                                    | `500m`                           |
| `resources.limits.memory`         |                                                                                                                    | `512M`                           |
| `resources.requests.cpu`          |                                                                                                                    | `250m`                           |
| `resources.requests.memory`       |                                                                                                                    | `128M`                           |
| `securityContext`                 | Security context for the main process container.                                                                   | `{}`                             |
| `service.type`                    |                                                                                                                    | `ClusterIP`                      |
| `service.port`                    |                                                                                                                    | `3000`                           |
| `serviceAccount.create`           |                                                                                                                    | `true`                           |
| `serviceAccount.annotations`      |                                                                                                                    | `{}`                             |
| `serviceAccount.name`             |                                                                                                                    | `''`                             |
| `tolerations`                     |                                                                                                                    | `[]`                             |
