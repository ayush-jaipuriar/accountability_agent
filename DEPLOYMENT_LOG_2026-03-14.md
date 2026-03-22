# Deployment Log - 2026-03-14

## Scope

Deploy the ghosting partner-alert fix to the existing Cloud Run service without creating any duplicate service.

## Target

- Cloud Run service: `accountability-agent`
- Region: `us-central1`
- URL: `https://accountability-agent-450357249483.us-central1.run.app`

## Safety Goal

Replace the currently running service in place by creating a new revision on the same Cloud Run service.

This deployment intentionally did **not** create a second Cloud Run service name.

## Pre-Deploy Verification

Confirmed there was exactly one live Cloud Run service in the target region:

- `accountability-agent`

Saved a pre-deploy service export outside the repository:

- `/tmp/accountability-agent.predeploy.yaml`

## Build

Built and pushed a uniquely tagged image with Cloud Build:

- Image: `us-central1-docker.pkg.dev/accountability-agent/cloud-run-source-deploy/accountability-agent:manual-20260314-003137`
- Digest: `sha256:d004a19428816504e7fc9440b8a59622e2df18382794ccd48a57d193572d7517`
- Cloud Build ID: `7b4e2959-1a82-4c63-aa67-2838294a78f6`

## Deploy Method

Used an in-place update of the existing service:

```bash
gcloud run services update accountability-agent \
  --platform=managed \
  --region=us-central1 \
  --image us-central1-docker.pkg.dev/accountability-agent/cloud-run-source-deploy/accountability-agent:manual-20260314-003137
```

Why this method:

- targets the existing Cloud Run service directly,
- creates a new revision under the same service,
- avoids accidental duplicate service creation from a new service name.

## Deployment Result

Cloud Run created and activated:

- New revision: `accountability-agent-00007-fsj`

Traffic result:

- `100%` routed to `accountability-agent-00007-fsj`

## Post-Deploy Verification

### Service Count

Verified there is still exactly one Cloud Run service in `us-central1`:

- `accountability-agent`

### Revision History

Verified the rollout created a new revision on the same service rather than a new service:

- Active revision: `accountability-agent-00007-fsj`
- Previous revision remains listed as historical revision: `accountability-agent-00006-ppb`

### Health Check

Verified live health endpoint:

```json
{"status":"healthy","service":"constitution-agent","version":"1.0.0","environment":"production","uptime":"0h 0m","checks":{"firestore":"ok"},"metrics_summary":{"checkins_total":0,"commands_total":0,"errors_total":0}}
```

### Runtime Configuration Sanity Check

Confirmed the deployed service is still running with the expected operational shape:

- service account preserved
- concurrency: `80`
- timeout: `300`
- cpu: `1`
- memory: `512Mi`
- maxScale: `3`
- expected environment variable names still present

## Verdict

Deployment succeeded.

The previous Cloud Run service was replaced in place by a new revision on the **same** service:

- no duplicate Cloud Run service created
- service URL unchanged
- health check passing

## Files Touched This Iteration

- `DEPLOYMENT_LOG_2026-03-14.md` - deployment audit log
