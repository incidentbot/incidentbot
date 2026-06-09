# incident-bot umbrella chart (ops cluster)

Deploys the BenefexLtd fork of incident-bot to the **ops cluster**
(`onehub-ew3-ops-p`) via ArgoCD GitOps — the same pattern as `benifex-backstage`
and `platform-agent-gateway`.

```
helm/
  Chart.yaml                     # wraps upstream incidentbot 3.0.3 as a dependency
  values.yaml                    # values for the subchart + ExternalSecret + ServiceMonitor
  Chart.lock                     # pinned dependency (committed)
  charts/incidentbot-3.0.3.tgz   # vendored dependency (committed)
  templates/
    external-secret.yaml         # materialises incident-bot-secrets from GCP Secret Manager
    servicemonitor.yaml          # Prometheus Operator scrape of /metrics
```

## How it deploys (no `helm upgrade` in CI)

On `main`, `.circleci/config.yml`:
1. **build-push** (`benefex/docker` orb) builds this repo's `Dockerfile` and
   pushes `europe-docker.pkg.dev/benefex-assets/benefex-images/incident-bot`,
   capturing the image digest.
2. **deploy** copies `helm/` into
   `kubernetes-resources/gitops/onehub-ew3-ops-p/charts/incident-bot/`, writes an
   ArgoCD `Application` (`services/incident-bot.yaml`) that pins the image to the
   build's digest via `helm.parameters`, and pushes to the gitops repo.
3. **ArgoCD** auto-syncs (prune + selfHeal) to the ops cluster.

The upstream chart's image template is `repository:tag` only (no digest field),
so the pin is expressed as `tag: latest@sha256:<digest>` — a valid, immutable
reference that changes every build, so ArgoCD always rolls out the exact image.

## Required CircleCI contexts

| Context | Provides |
|---|---|
| `gcloud` | `GCLOUD_GCR_SERVICE_ACCOUNT` (image push) |
| `argocd` | `GITHUB_APP_ID`, `GITHUB_APP_INSTALLATION_ID`, `GITHUB_APP_PRIVATE_KEY` (push to the gitops repo) |

## Secrets — ExternalSecret

`templates/external-secret.yaml` (`kubernetes-client.io/v1`, matching backstage)
materialises the `incident-bot-secrets` Kubernetes Secret from GCP Secret
Manager (`externalSecret.dataFrom`). The Secret Manager secret(s) must contain:

```
SLACK_APP_TOKEN, SLACK_BOT_TOKEN, SLACK_USER_TOKEN, SECRET_KEY,
POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD,
ATLASSIAN_API_URL, ATLASSIAN_API_USERNAME, ATLASSIAN_API_TOKEN
```

Point `POSTGRES_HOST` at the Cloud SQL (Postgres 17) private IP / proxy. Adjust
`externalSecret.projectId` if the secrets live in a different GCP project.

## ⚠️ Database migrations — read before the first v3 rollout

The app image runs `alembic upgrade head` on **every pod start**;
`replicaCount: 1` keeps that from racing. The real risk is the **v1/v2 → v3
jump against the existing production Cloud SQL database** — this fork carries
upstream's rewritten v3 Alembic chain.

Before the first rollout:
1. Check the current revision: `SELECT version_num FROM alembic_version;`
2. **Clone the Cloud SQL instance** and run the new image against the clone;
   confirm `alembic upgrade head` applies cleanly with real data (v3
   "initial"-style revisions can clash with an existing v1/v2 schema).
3. **Back up** prod immediately before the real rollout.
4. If it doesn't apply cleanly on the clone, resolve deliberately (`alembic
   stamp` to align history, or a bridge migration) rather than letting a pod
   attempt it against prod.

## Verifying metrics after deploy

```bash
kubectl -n incident-bot port-forward svc/incident-bot-incidentbot 3000:3000
curl -s localhost:3000/metrics | grep incidentbot_
```

Then confirm the target is `UP` in Prometheus (the ServiceMonitor's `release:`
label must match your Prometheus Operator's `serviceMonitorSelector`).
