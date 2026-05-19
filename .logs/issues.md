# Issue Log

---
**Issue ID:** ISS-001
**Timestamp:** 2026-05-06T13:30:00Z
**Reported by:** IaC/DevOps Engineer (security self-check)
**Task/Session ID:** cors-infra-investigation
**Status:** Open
**Status History:**

**Severity:** P2
**Category:** Security
**Title:** Backend deploy workflow authenticates to GCP using a service account key file rather than Workload Identity Federation.

**Description:**
`.github/workflows/backend-deploy.yml` uses `credentials_json: ${{ secrets.GCP_SA_KEY }}` to authenticate the `google-github-actions/auth@v2` step. This is a long-lived service account key stored as a GitHub Actions secret. Long-lived keys are a persistent secret that can be leaked, are not automatically rotated, and cannot be tied to a specific workflow run. GitHub Actions and GCP both recommend Workload Identity Federation (WIF) for keyless authentication — WIF issues short-lived, run-scoped credentials with no persistent secret to manage.

**Location:** `.github/workflows/backend-deploy.yml` — step "Authenticate", `credentials_json` field

**Spec reference:** DevOps Security Module — "Provider authentication in CI must use Workload Identity Federation, not downloaded service account key files."

**Suggested fix:**
1. Create a Workload Identity Pool and Provider in GCP for the GitHub Actions OIDC issuer (`token.actions.githubusercontent.com`).
2. Bind the pool to the deploy service account with a condition restricting to the `aurafractor` repository and `main` branch.
3. Replace `credentials_json` with `workload_identity_provider` and `service_account` fields in the `google-github-actions/auth@v2` step.
4. Remove the `GCP_SA_KEY` secret from GitHub Actions.

WIF can be provisioned in Terraform using `google_iam_workload_identity_pool` and `google_iam_workload_identity_pool_provider` resources. This fix is out of scope for the current CORS investigation but should be addressed in a dedicated security hardening task.

**Auto-fix attempted:** No

---
**Issue ID:** ISS-002
**Timestamp:** 2026-05-06T13:30:00Z
**Reported by:** IaC/DevOps Engineer (investigation finding)
**Task/Session ID:** cors-infra-investigation
**Status:** Open
**Status History:**

**Severity:** P1
**Category:** CI/CD
**Title:** `api.aurafractor.com` custom domain mapping was not managed in Terraform, making domain routing configuration invisible and unverifiable from the codebase.

**Description:**
No Terraform resource existed for the `api.aurafractor.com` Cloud Run domain mapping. The domain mapping was configured manually in GCP. This means there is no way to verify from the IaC whether the mapping is active, whether it is pointing to the correct Cloud Run service and revision, and whether it was configured correctly to serve traffic without HTTP-to-HTTPS redirects or verification pages. An unverified or misconfigured domain mapping returns responses from Google's infrastructure (redirect pages, verification pages) rather than the Flask app — the browser reports these as CORS failures because the redirect/verification responses do not include CORS headers.

A `google_cloud_run_domain_mapping` resource has been added to `terraform/cloud_run.tf` to bring this under IaC management. The first `terraform plan` after this change must be reviewed before applying.

**Location:** `terraform/cloud_run.tf` — new `google_cloud_run_domain_mapping.api` resource

**Spec reference:** DevOps behavioral rules — "All environments (dev, staging, production) are covered by the IaC. No environment is manually configured or undeclared."

**Suggested fix:**
1. Run `terraform plan -out=tfplan` and review the output. If the plan shows the domain mapping being created (rather than adopted), verify that no existing manual mapping will conflict.
2. Run `terraform apply tfplan`.
3. After apply, run `gcloud beta run domain-mappings describe --domain=api.aurafractor.com --region=<region> --project=<project>` and confirm the mapping status is `READY`.
4. If DNS records are not yet configured, add the A/AAAA records returned by the describe command to the DNS provider.

**Auto-fix attempted:** Yes — Terraform resource added to `terraform/cloud_run.tf`. Plan and apply not executed (requires human review per plan-before-apply policy).
**Auto-fix outcome:** Partial — IaC resource added; apply and DNS verification are manual steps.

---
**Issue ID:** ISS-003
**Timestamp:** 2026-05-06T14:00:00Z
**Reported by:** IaC/DevOps Engineer (CORS root-cause investigation)
**Task/Session ID:** cors-port-fix
**Status:** Fixed — pending deploy

**Severity:** P1
**Category:** Infrastructure misconfiguration
**Title:** Cloud Run `container_port` declared as 5000 but gunicorn binds to port 8080, causing all requests to return 502 with no CORS headers.

**Description:**
`terraform/cloud_run.tf` declared `container_port = 5000`. The production Dockerfile (`backend/Dockerfile`) sets `ENV PORT=8080` and the gunicorn CMD hardcodes `--bind 0.0.0.0:8080`. Cloud Run's ingress uses `container_port` to determine which port to forward incoming requests to. With `container_port = 5000` and no process listening on port 5000, Cloud Run returns 502 Bad Gateway responses from its own load balancer infrastructure. These 502 responses carry no application headers — in particular, no `Access-Control-Allow-Origin` or `Access-Control-Allow-Headers`. The browser receives a cross-origin response with no CORS headers and reports a CORS error.

This explains why the Flask CORS configuration (which is correctly written) produced no observable effect: no request was actually reaching the Flask process.

**Location:**
- `terraform/cloud_run.tf` line 59: `container_port = 5000` (changed to `8080`)
- `backend/Dockerfile` CMD: `gunicorn --bind 0.0.0.0:8080 ...` (changed to `gunicorn --bind "0.0.0.0:${PORT}" ...`)

**Spec reference:** N/A — this is a deployment configuration defect.

**Suggested fix (applied):**
1. `terraform/cloud_run.tf`: changed `container_port` from `5000` to `8080`.
2. `backend/Dockerfile`: changed gunicorn CMD from exec-form with hardcoded `8080` to shell-form reading `$PORT`, so the binding matches the Cloud Run injected value and the Terraform declaration stay in sync.

**Auto-fix attempted:** Yes
**Auto-fix outcome:** Files changed. Requires: (a) `terraform apply` to update the Cloud Run service definition, which triggers a new revision with `container_port=8080`; (b) a new backend Docker image build and Cloud Run deploy so the container CMD also uses `$PORT`. The terraform apply alone may be sufficient if the currently deployed image already guesses 8080 — but the image should be rebuilt to remove the ambiguity.

---
**Issue ID:** ISS-004
**Timestamp:** 2026-05-14T00:00:00Z
**Reported by:** Frontend Engineer (design accuracy self-check, architectural fidelity)
**Task/Session ID:** extractions-cache-and-rerun-guard
**Status:** Open

**Severity:** P2
**Category:** Spec ambiguity
**Title:** Re-run extraction API call uses empty sources array — spec does not define backend behaviour for zero sources.

**Description:**
The re-run button in `extraction/[id].tsx` calls `extraction.extract(track_id, [])` with an empty sources array when the user confirms the re-run dialog. The `POST /extraction/extract` API contract (from `src/api/client.ts`) defines `sources: ExtractionSource[]` but does not specify a minimum length or the expected backend behaviour when sources is empty. A failed extraction has no original source list in the `ExtractionResponse`, so the re-run cannot reconstruct the original label set.

If the backend rejects an empty sources array (e.g., returns 422), the error will surface in the `rerunError` state and the user will see a message. This is not a crash, but it does leave the user in a failed state with no actionable next step other than returning to the upload flow.

**Location:** `ui/app/extraction/[id].tsx` — `handleRerun` callback, line with `extractionApi.extract(data.track_id, [])`.

**Spec reference:** `.spec/api-contracts.md` (if it exists — not confirmed in this session). `src/api/client.ts` `extract` method definition.

**Suggested fix:**
Three options to escalate to the PM/Architect:
1. Define the backend behaviour for zero sources (e.g., "use original source list") and document it in the API contract — enables the current frontend implementation to work correctly
2. Include the original `sources` list in the `ExtractionResponse` so the frontend can re-use it without changes to the backend
3. Change the re-run UX to navigate the user back to the label-selection step rather than re-running immediately — eliminates the empty-sources problem but changes the UX from in-place to multi-step

**Auto-fix attempted:** No — awaiting PM/Architect decision on which option to pursue.

---
**Issue ID:** ISS-005
**Timestamp:** 2026-05-19T00:00:00Z
**Reported by:** IaC/DevOps Engineer (worker-url-wiring investigation)
**Task/Session ID:** worker-url-wiring
**Status:** Open

**Severity:** P1
**Category:** Infrastructure — missing dependency
**Title:** No ML worker Cloud Run service exists in Terraform; all extraction jobs fail silently after 3 retries.

**Description:**
`backend/services/tasks.py` reads `WORKER_URL` from its environment and uses it as the HTTP target for every Cloud Tasks extraction job. In the current production Cloud Run deployment, `WORKER_URL` is not set as an environment variable, so the application falls back to the hardcoded default `http://localhost:5001/worker/extract`. Cloud Tasks POSTs to this localhost address, which is not reachable from Cloud Run. The task fails, Cloud Tasks retries it twice more (3 attempts total per `retry_config` in `cloud_tasks.tf`), then the task is discarded. The extraction record in the database remains in `queued` status indefinitely — no processing occurs and no error is surfaced to the user.

A review of all Terraform files (`cloud_run.tf`, `cloud_tasks.tf`, `gcs.tf`, `main.tf`, `variables.tf`) and the Terraform state confirms that no worker Cloud Run service has ever been provisioned. The wiring infrastructure (variable `worker_url`, conditional env var block in the API service) has been added in this task, but it cannot be populated with a real URL until the worker service exists.

**Location:**
- `backend/services/tasks.py` line 19: `WORKER_URL = os.getenv('WORKER_URL', 'http://localhost:5001/worker/extract')`
- `terraform/cloud_run.tf` — `WORKER_URL` env var absent (now added as conditional; blocked on worker service URL)
- `terraform/` — no worker Cloud Run service resource exists

**Spec reference:** N/A — this is a missing infrastructure component blocking the core product feature.

**Suggested fix (partial — wiring ready, worker service required):**
The `WORKER_URL` env var wiring is now in place in `terraform/cloud_run.tf` and `terraform/variables.tf`. To resolve this issue completely:
1. Provision an ML worker Cloud Run service (a new Terraform resource, likely in a new `terraform/worker.tf` file) with a container image that handles `POST /worker/extract` requests and runs Demucs/Spleeter.
2. Create a service account for the worker with appropriate permissions (GCS read/write for stems, Cloud SQL access for status updates).
3. Set `worker_url` in `terraform.tfvars` to the worker's Cloud Run URI plus the `/worker/extract` path.
4. Run `terraform apply` to inject `WORKER_URL` into the API service environment, triggering a new Cloud Run revision.
5. Verify by enqueueing a test extraction and confirming the task reaches the worker.

**Auto-fix attempted:** Partial — `WORKER_URL` wiring infrastructure added to `terraform/variables.tf`, `terraform/cloud_run.tf`, and `terraform/terraform.tfvars.example`. Worker service provisioning and URL population are manual steps requiring tech lead approval.
**Auto-fix outcome:** Wiring ready; blocked on worker service existence and URL.
