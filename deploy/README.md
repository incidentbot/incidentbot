# Deploying incident-bot (BenefexLtd fork)

This fork is deployed to GKE with the **upstream Helm chart** (published at
`https://docs.incidentbot.io/charts`, chart `incidentbot/incidentbot`) — the
chart is not vendored in this repo. We only keep our **values**, a
**ServiceMonitor**, and the **CircleCI pipeline** here.

```
deploy/
  values.yaml          # Helm values for our deployment
  servicemonitor.yaml  # Prometheus Operator scrape config for /metrics
.circleci/config.yml   # build -> push to Artifact Registry -> helm upgrade
```

## How it works

On every push to `main`, CircleCI:
1. Builds the image from this repo's `Dockerfile` (target `app`) so our custom
   code (Prometheus metrics, Slack fixes, multi-select components) is included.
   The upstream image does **not** contain these changes.
2. Pushes it to Artifact Registry as `…/incident-bot:sha-<short>` and `:latest`.
3. `helm upgrade --install`s the chart with `deploy/values.yaml`, overriding the
   image to our freshly-built one.
4. Applies `deploy/servicemonitor.yaml` so Prometheus scrapes `/metrics`.

## Required CircleCI configuration

Set these in a context named `gcp` (or as project env vars):

| Variable | Purpose |
|---|---|
| `GCLOUD_SERVICE_KEY` | GCP service-account JSON key (full file contents) |
| `GCP_PROJECT` | GCP project ID |
| `GAR_LOCATION` | Artifact Registry region, e.g. `europe-west2` |
| `GAR_REPO` | Artifact Registry repository name, e.g. `incident-bot` |
| `GKE_CLUSTER` | GKE cluster name |
| `GKE_LOCATION` | GKE cluster region/zone |
| `K8S_NAMESPACE` | target namespace, e.g. `incidentbot` |

The service account needs **Artifact Registry Writer** and **Kubernetes Engine
Developer** (on the target cluster). Create the Artifact Registry repo once:

```bash
gcloud artifacts repositories create incident-bot \
  --repository-format=docker --location="$GAR_LOCATION" --project="$GCP_PROJECT"
```

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
