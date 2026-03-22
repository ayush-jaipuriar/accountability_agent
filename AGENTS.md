# Accountability Agent Project Rules

These rules apply to all future work in this repository unless the user explicitly overrides them.

## Deployment Rules

### Canonical Production Target

- Production Cloud Run service name: `accountability-agent`
- Production Cloud Run region: `us-central1`
- Production project: `accountability-agent`
- Production URL: `https://accountability-agent-450357249483.us-central1.run.app`

### Non-Negotiable Deployment Safety Rules

- Always update the existing Cloud Run service in place.
- Never create a second production Cloud Run service name for routine deployments.
- Never deploy production to a different region unless the user explicitly approves a migration.
- Never use a variant service name such as `-v2`, `-new`, `-test`, or `-staging` for production replacement.
- Treat a new Cloud Run revision as acceptable; treat a new Cloud Run service as a deployment mistake unless explicitly requested.

### Required Pre-Deploy Checks

Before any production deployment:

1. Confirm the active GCP project is `accountability-agent`.
2. Confirm the existing Cloud Run service exists:
   - `gcloud run services list --platform=managed --region=us-central1`
3. Snapshot the current live service config outside the repository:
   - `gcloud run services describe accountability-agent --platform=managed --region=us-central1 --format=export > /tmp/accountability-agent.predeploy.yaml`
4. Run the project test gate:
   - `pytest tests`
5. Run source compilation sanity check:
   - `python3 -m compileall src`
6. If Docker is available, validate the deployable artifact path:
   - `docker build -t accountability-agent:preflight .`

### Build Rules

- Build a uniquely tagged image for every deployment.
- Use Artifact Registry in `us-central1`.
- Canonical image repository:
  - `us-central1-docker.pkg.dev/accountability-agent/cloud-run-source-deploy/accountability-agent`
- Preferred image tag format:
  - `manual-YYYYMMDD-HHMMSS`

### Approved Production Deploy Method

Use an in-place service update that changes only the image:

```bash
gcloud run services update accountability-agent \
  --platform=managed \
  --region=us-central1 \
  --image us-central1-docker.pkg.dev/accountability-agent/cloud-run-source-deploy/accountability-agent:<tag>
```

Why this is the default:

- it targets the existing service directly,
- it preserves the current service identity and URL,
- it creates a new revision instead of a duplicate service.

### Forbidden Production Deploy Patterns

- Do not use `gcloud run deploy` with a new service name.
- Do not change region during a routine release.
- Do not overwrite runtime config blindly with freshly typed flags.
- Do not export Cloud Run service definitions containing live secrets into the repository.
- Do not commit service exports, env dumps, or credentials.

### Configuration Preservation Rules

- Treat the currently running Cloud Run service as the source of truth for production config.
- Preserve existing service account, env vars, secrets, CPU, memory, concurrency, timeout, ingress, and autoscaling unless the user explicitly asks to change them.
- If config changes are needed, pause and call them out before deployment.
- Store temporary pre/post deploy service exports in `/tmp`, not in the repo, because the current service may contain sensitive environment variables.

### Required Post-Deploy Verification

After every production deployment:

1. Verify there is still only one production Cloud Run service:
   - `gcloud run services list --platform=managed --region=us-central1`
2. Verify the rollout produced a new revision on the same service:
   - `gcloud run revisions list --service=accountability-agent --region=us-central1`
3. Verify the live health endpoint:
   - `curl -fsS https://accountability-agent-450357249483.us-central1.run.app/health`
4. Verify the service still has the expected runtime shape:
   - service account
   - env var names
   - CPU / memory
   - timeout
   - concurrency
   - autoscaling annotations
5. Record the deployment in a dated markdown log in the repo.

## Testing Notes

- Root-level `pytest` currently collects `test_docker_phase3f.py`, which is an executable verification script and can abort collection via `sys.exit()`.
- The canonical automated test command for this repository is:
  - `pytest tests`

## Secrets Handling Rules

- Never paste production secret values into documentation, commits, or summaries.
- Never commit raw Cloud Run service exports if they include live environment variable values.
- If a command output includes secrets, summarize the configuration without reproducing the sensitive values.

## Current Deployment Reference

The deployment process validated on 2026-03-14 is documented in:

- `DEPLOYMENT_LOG_2026-03-14.md`

That deployment successfully:

- updated the existing `accountability-agent` service in `us-central1`,
- created revision `accountability-agent-00007-fsj`,
- preserved the single-service topology,
- and verified healthy post-deploy behavior.
