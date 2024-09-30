# Web Interface

## Prerequisites

### API

Additional API routes are disabled by default. This flag only needs to be set to `true` if using the web interface.

Note that the API exposes a health check route.

!!! note

    The web interface is optional and is not required to use the application.

```yaml
api:
  enabled: true
```

With the API enabled, routes will be made available via `/api/v1`.

!!! warning

    API routes are only meant to serve the web interface. As such, they are secured using JWT and will not work without first running through the setup guide for the [web interface](ui.md).

### Authentication

!!! warning

    The default username and password for the web interface are set to `admin@example.com`:`changethis`. It is **strongly** recommended you change these variables before exposing the API.

    Set the environment variables `FIRST_SUPERUSER` and `FIRST_SUPERUSER_PASSWORD` to unique values before running the application the first time.

```python
# incidentbot/configuration/settings.py
FIRST_SUPERUSER: str = "admin@example.com"
FIRST_SUPERUSER_PASSWORD: str = "changethis"
```

Consult the API [documentation](configuration.md#api) for additional settings related to it.

## Running the Web Interface

### Building the Docker Image

There is a separate repository for the web interface located [here](https://github.com/incidentbot/console).

Since the client application must be built with the API URL as an argument, you will need to build and host the image for the web interface on your own.

The easiest way to do this is to use the base image which already contains the application logic:

```dockerfile
FROM eb129/incidentbot-console:v0.1.0 AS build
WORKDIR /app
ARG VITE_API_URL=${VITE_API_URL}
RUN npm run build
FROM nginx:1
COPY --from=build /app/dist/ /usr/share/nginx/html
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
COPY ./nginx-backend-not-found.conf /etc/nginx/extra-conf.d/backend-not-found.conf
```

You will need to provide the content of [nginx.conf](https://github.com/incidentbot/console/blob/main/nginx.conf) and [nginx-backend-not-found.conf](https://github.com/incidentbot/console/blob/main/nginx-backend-not-found.conf) in the build directory.

### Deploying via Helm

You can get started quickly by using the Helm chart:

```bash
helm repo add incidentbot https://charts.incidentbot.io
helm repo update
```

Create a `values.yaml` file. We'll call this one `incidentbot-console-values.yaml`:

```yaml
# Reference the image built earlier.
image:
  repository: myrepo/incidentbot-console
  tag: mytag
ingress:
  enabled: true
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: incidentbot-console.mydomain.com
      paths:
        - path: /
          pathType: ImplementationSpecific
  tls:
    - secretName: incidentbot-tls
      hosts:
        - incidentbot-console.mydomain.com
```

Install the chart:

```bash
VERSION=$(helm search repo incidentbot --output=json | jq '.[1].version' | tr -d '"')
helm install incidentbot/incidentbot-console --version $VERSION --values incidentbot-console-values.yaml --namespace incidentbot
```
