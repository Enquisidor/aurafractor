# Completion Artifact — IaC/DevOps Engineer

**Issue ID:** ISS-003
**Issue title:** Cloud Run container_port/gunicorn port mismatch causing 502 responses with no CORS headers
**Agent:** IaC/DevOps Engineer
**Timestamp:** 2026-05-06T14:00:00Z

---

## Files created or modified

| File | Change |
|---|---|
| `terraform/cloud_run.tf` | Changed `container_port` from `5000` to `8080`; added explanatory comment documenting the mismatch and its CORS symptom |
| `backend/Dockerfile` | Changed gunicorn CMD from exec-form with hardcoded `8080` to shell-form reading `${PORT}` env var so the binding stays in sync with Cloud Run's injected value and the Terraform declaration |

---

## Implementation summary

The root cause of the persistent production CORS errors was a port mismatch between the Cloud Run Terraform configuration and the gunicorn process in the container. `terraform/cloud_run.tf` declared `container_port = 5000`. The Dockerfile set `ENV PORT=8080` and gunicorn's CMD hardcoded `--bind 0.0.0.0:8080`. Cloud Run's ingress uses `container_port` to determine where to forward incoming requests; with nothing listening on port 5000, every request returned a 502 from Cloud Run's own load balancer infrastructure. A 502 from Cloud Run's infrastructure carries no application-level response headers — in particular, no `Access-Control-Allow-Origin`. The browser receives a cross-origin response with no CORS headers and reports a CORS error, even though the Flask CORS configuration (correctly written) was never reached.

The fix changes `container_port` to `8080` in Terraform (matching the gunicorn binding) and changes the gunicorn CMD in the Dockerfile to read `$PORT` from the environment, so the two values are kept in sync by Cloud Run's injected `PORT=8080` variable.

---

## Investigation findings — what was checked

**Firebase Hosting (`ui/firebase.json`):** No `headers` block. Only a SPA rewrite (`**` → `/index.html`). Firebase Hosting is not setting CORS headers and is not proxying API calls. Clean.

**Cloud Run IAM:** `google_cloud_run_v2_service_iam_member.public` grants `roles/run.invoker` to `allUsers`. Unauthenticated requests (including OPTIONS preflights which carry no auth headers) are permitted at the IAM layer. Clean.

**No load balancer or API Gateway:** There is no `google_compute_url_map`, `google_compute_backend_service`, `google_compute_target_https_proxy`, or API Gateway resource in Terraform. The only upstream resource is `google_cloud_run_domain_mapping`. No CORS policy configuration is required at an LB level because there is no LB.

**Deploy workflow:** `.github/workflows/backend-deploy.yml` uses `google-github-actions/deploy-cloudrun@v2` without `--no-traffic` — deploys the new revision and migrates 100% of traffic to it immediately. No staged rollout. Clean — the latest code is serving all traffic.

**`TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST` in Terraform:** Correct. Cloud Run will always route to the most recently deployed revision.

**Root cause confirmed:** `container_port = 5000` vs gunicorn binding on 8080.

---

## Deviations from spec

None. This is a bug fix to a misconfiguration.

---

## Environments affected

- Production (the mismatch is in the shared `cloud_run.tf`; both staging and production share this resource definition)
- Staging (same fix applies; the mismatch exists there too)

---

## Secrets required before first apply

None. This change requires no new secrets.

---

## Rollback procedure

If the `terraform apply` causes an unexpected problem:
1. Revert `container_port` in `terraform/cloud_run.tf` to `5000` (though this restores the broken state).
2. Run `terraform plan -out=tfplan` and review.
3. Run `terraform apply tfplan`.

More practically: Cloud Run's `terraform apply` with a changed `container_port` triggers a new revision. Cloud Run supports instant rollback via traffic splitting — redirect 100% of traffic to the previous revision using `gcloud run services update-traffic aurafractor-api --to-revisions=<previous-revision>=100 --region=<region>`. This is instant and does not require a new deployment.

---

## Sizing or configuration decisions proposed for tech lead review

None. This fix changes a port number from an incorrect value to the correct value. No sizing decisions were made.

---

## Self-check status

- Security Module (IaC/DevOps): Complete. No new secrets hardcoded. No new IAM grants. No new network exposure. No supply chain changes. Existing ISS-001 (SA key auth) remains open from prior session.
- Performance Module (IaC/DevOps): Complete. No resource sizing changes. Port fix has no cost or performance implications.

---

## Required actions before CORS is resolved in production

The file changes alone do not fix production. Two deployment steps are required:

1. **`terraform apply`** — updating the Cloud Run service definition to `container_port = 8080` triggers a new Cloud Run revision with the corrected port declaration. This step alone may be sufficient if the currently deployed container image happens to have gunicorn already listening on 8080 (which it does, based on the hardcoded CMD). However:

2. **New Docker image build + Cloud Run deploy** — the Dockerfile CMD change (`$PORT` variable expansion) should be included in the next image build so the binding is explicitly driven by the injected environment variable rather than a hardcoded value. The build/deploy pipeline is triggered automatically on push to `main` via `.github/workflows/backend-build.yml` → `backend-deploy.yml`.

The minimum viable fix for immediate unblocking is step 1 (terraform apply). Step 2 removes the residual hardcoded port and is good hygiene.

---

Status: READY FOR PHASE-2 VERIFICATION
