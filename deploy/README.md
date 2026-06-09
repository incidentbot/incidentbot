# Deploying incident-bot (BenefexLtd fork)

This fork is deployed to GKE with the **upstream Helm chart** (published at
`https://docs.incidentbot.io/charts`, chart `incidentbot/incidentbot`) — the
chart is not vendored in this repo. We only keep our **values**, a
**ServiceMonitor**, and the **CircleCI pipeline** here.

```
deploy/
  values.yaml          # Helm values for our deployment
  servicemonitor.yaml  # Prometheus Operator scrape config for /metrics
.circleci/config.yml   # build (benefex/docker orb) -> helm upgrade
```

## How it works

On every push to `main`, CircleCI:
1. **`build-push`** — uses the shared **`benefex/docker`** orb to build this
   repo's `Dockerfile` (so our custom code — Prometheus metrics, Slack fixes,
   multi-select components — is included; the upstream image does not contain
   these). It pushes to
   `europe-docker.pkg.dev/benefex-assets/benefex-images/incident-bot:latest`
   and persists the image digest to the workspace.
2. **`deploy`** — uses the **`benefex/helm`** orb's `configure-kubernetes` for
   GKE auth, then `helm upgrade --install`s the **external** `incidentbot`
   chart with `deploy/values.yaml`, pointing the image at our build, and applies
   `deploy/servicemonitor.yaml`.

> The upstream chart's image template is `repository:tag` only (no digest), so
> we deploy the `:latest` tag and set a `commit-sha` pod annotation each build
> to force a fresh rollout (pods pull `:latest`, which is the new build).
>
> We don't use the `benefex/helm` orb's `deploy` command because it's wired to
> Benefex's own base charts (`benefex/<chart>`, `--set image/deploymentEnv/...`)
> and can't drive this third-party chart.

## Required CircleCI configuration

The pipeline relies on the standard Benefex contexts:

| Context | Provides | Used for |
|---|---|---|
| `gcloud` | `GCLOUD_GCR_SERVICE_ACCOUNT` | push/pull the image in Artifact Registry |
| `gcp_prod` | `GCLOUD_GKE_PROD_SERVICE_ACCOUNT`, `GCLOUD_GKE_PROD_CLUSTER_NAME`, `GCLOUD_GKE_PROD_PROJECT_NAME` | authenticate to the prod GKE cluster |

Plus one project/env var:

| Variable | Purpose | Default |
|---|---|---|
| `K8S_NAMESPACE` | target namespace | `incidentbot` |

The orb pushes to `benefex-images` and names the image after the repo
(`incident-bot`). If you want a different image name, set `BUILD_RELEASE_NAME`.

## Required Kubernetes Secret (not committed)

`values.yaml` sets `envFromSecret.secretName: incidentbot-secret`. Create it in
the target namespace with at least:

```bash
kubectl create secret generic incidentbot-secret -n "$K8S_NAMESPACE" \
  --from-literal=SLACK_APP_TOKEN=xapp-... \
  --from-literal=SLACK_BOT_TOKEN=xoxb-... \
  --from-literal=SLACK_USER_TOKEN=xoxp-... \
  --from-literal=SECRET_KEY=<stable-random-string> \
  --from-literal=POSTGRES_HOST=<cloud-sql-host-or-proxy> \
  --from-literal=POSTGRES_PORT=5432 \
  --from-literal=POSTGRES_DB=incident_bot \
  --from-literal=POSTGRES_USER=<user> \
  --from-literal=POSTGRES_PASSWORD=<password> \
  --from-literal=ATLASSIAN_API_URL=https://benefex.atlassian.net/ \
  --from-literal=ATLASSIAN_API_USERNAME=<email> \
  --from-literal=ATLASSIAN_API_TOKEN=<token>
```

For Cloud SQL, point `POSTGRES_HOST` at the private IP or a Cloud SQL Auth Proxy
sidecar/service.

## ⚠️ Database migrations — read before the first v3 rollout

The image entrypoint runs `alembic upgrade head` on **every pod start**. We keep
`replicaCount: 1` so migrations never run concurrently. This is convenient but
means a bad migration surfaces as a crash-looping pod, not a clean gate.

**The real risk is the v1/v2 → v3 jump against the existing production Cloud SQL
(Postgres 17) database.** This fork carries upstream's rewritten v3 Alembic
chain. Before pointing the new image at the production DB:

1. **Check the current revision** on prod:
   `SELECT version_num FROM alembic_version;`
2. **Clone the Cloud SQL instance** (`gcloud sql instances clone …`) and run the
   new image against the clone first. Confirm `alembic upgrade head` applies
   cleanly end-to-end with real data — the v3 "initial"-style revisions can
   conflict with an existing v1/v2 schema.
3. **Back up** prod (`gcloud sql backups create …`) immediately before the real
   rollout.
4. If the chain doesn't apply cleanly on the clone, resolve it deliberately
   (e.g. `alembic stamp` to align history, or a hand-written bridge migration)
   rather than letting a pod attempt it against prod.

If you'd prefer migrations gated as an explicit pre-deploy step (a one-off Job
that must succeed before pods roll out, with auto-migrate disabled via the
chart's `command` override), that can be added — open an issue / ask.

## Verifying metrics after deploy

```bash
kubectl -n "$K8S_NAMESPACE" port-forward svc/incidentbot 3000:3000
curl -s localhost:3000/metrics | grep incidentbot_
```

Then confirm the target is `UP` in Prometheus (the ServiceMonitor's `release:`
label must match your Prometheus Operator's `serviceMonitorSelector`).
