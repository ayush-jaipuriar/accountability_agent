# Deployment Log - 2026-03-22

## Scope

Deploy the stress-guidance fix and partner check-in notification feature to the existing production Cloud Run service without creating any duplicate service.

## Target

- Cloud Run service: `accountability-agent`
- Region: `us-central1`
- URL: `https://accountability-agent-450357249483.us-central1.run.app`

## Safety Goal

Replace the currently running service in place by creating a new revision on the same Cloud Run service.

This deployment intentionally did **not** create a second Cloud Run service name.

## Pre-Deploy Verification

Confirmed the active GCP project:

- `accountability-agent`

Confirmed there was exactly one live Cloud Run service in the target region:

- `accountability-agent`

Saved a pre-deploy service export outside the repository:

- `/tmp/accountability-agent.predeploy.yaml`

Verified the local quality gates:

- `pytest tests`
- `python3 -m compileall src`

Attempted Docker preflight build locally, but Docker daemon was not running on the machine at deploy time. Used Cloud Build for artifact creation instead.

After deployment, once the Docker daemon was restarted locally, re-ran the Docker preflight successfully:

- `docker build -t accountability-agent:preflight .`
- Local image tag created: `accountability-agent:preflight`

## Build

Built and pushed a uniquely tagged image with Cloud Build:

- Image: `us-central1-docker.pkg.dev/accountability-agent/cloud-run-source-deploy/accountability-agent:manual-20260322-180048`
- Digest: `sha256:cf7d92ba5a3d8aed6e9837fcb36bd0aa3e088dd9cf2aeaf3049f4fbb51d6ad0a`
- Cloud Build ID: `77a35fbd-6270-4a8d-938f-8b4bc2deb821`

## Deploy Method

Used an in-place update of the existing service:

```bash
gcloud run services update accountability-agent \
  --platform=managed \
  --region=us-central1 \
  --image us-central1-docker.pkg.dev/accountability-agent/cloud-run-source-deploy/accountability-agent:manual-20260322-180048
```

Why this method:

- targets the existing Cloud Run service directly,
- creates a new revision under the same service,
- avoids accidental duplicate service creation from a new service name.

## Deployment Result

Cloud Run created and activated:

- New revision: `accountability-agent-00008-qvq`

Traffic result:

- `100%` routed to `accountability-agent-00008-qvq`

## Post-Deploy Verification

### Service Count

Verified there is still exactly one Cloud Run service in `us-central1`:

- `accountability-agent`

### Revision History

Verified the rollout created a new revision on the same service rather than a new service:

- Active revision: `accountability-agent-00008-qvq`
- Previous revision remains listed as historical revision: `accountability-agent-00007-fsj`

### Health Check

Verified live health endpoint:

```json
{"status":"healthy","service":"constitution-agent","version":"1.0.0","environment":"production","uptime":"0h 0m","checks":{"firestore":"ok"},"metrics_summary":{"checkins_total":0,"commands_total":0,"errors_total":0}}
```

### Runtime Configuration Sanity Check

Compared the live service against the pre-deploy snapshot and confirmed the runtime shape still matches:

- service account preserved
- expected environment variable names preserved
- concurrency: `80`
- timeout: `300`
- cpu: `1`
- memory: `512Mi`
- service-level ingress preserved
- autoscaling controls preserved

## Verdict

Deployment succeeded.

The previous Cloud Run service was replaced in place by a new revision on the **same** service:

- no duplicate Cloud Run service created
- service URL unchanged
- health check passing
- runtime configuration shape preserved
- local Docker preflight now also passing

## Files Touched This Iteration

- `DEPLOYMENT_LOG_2026-03-22.md` - deployment audit log
