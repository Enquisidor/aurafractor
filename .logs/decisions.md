# Decision Log

---
**Decision ID:** DEC-001
**Agent:** IaC/DevOps Engineer
**Task ID:** cors-infra-investigation
**Timestamp:** 2026-05-06T13:30:00Z

**Context:**
The custom domain `api.aurafractor.com` was not managed in Terraform — it existed only as a manual configuration in GCP. This meant there was no way to verify from the codebase that the domain mapping was correctly configured to route traffic directly to the Cloud Run service, and no audit trail for changes to the routing. The absence of IaC management for the domain mapping is a likely contributing cause of the production CORS failures, because a misconfigured or unverified domain mapping results in responses from Google's verification pages rather than the Flask app — which the browser reports as a CORS error.

**Options considered:**
1. Add `google_cloud_run_domain_mapping` to `cloud_run.tf` — brings domain routing under Terraform, makes the configuration auditable, and ensures the mapping is applied on every `terraform apply`
2. Leave domain mapping unmanaged in Terraform and document the manual steps — preserves the current approach but provides no drift detection and no fix for the routing gap

**Decision:** Option 1 — add `google_cloud_run_domain_mapping` resource to `cloud_run.tf`, controlled by a new `var.api_custom_domain` variable that defaults to empty string (no domain mapping created when unset).

**Rationale:** The root cause of the CORS errors is that requests to `api.aurafractor.com` may not be reaching the Flask app. The only way to verify this from the codebase is to bring the domain mapping into Terraform state. Without Terraform management, there is no way to confirm the mapping is active and pointing to the correct revision. The `count = var.api_custom_domain != "" ? 1 : 0` guard allows staging environments without a custom domain to skip this resource without changing the resource definition.

**Trade-offs accepted:** The first `terraform apply` after adding this resource will either create a new domain mapping (if one does not exist) or adopt an existing one (if it does). If the existing manual domain mapping has a different configuration, Terraform will update it to match — this is the intended behavior but requires human review of the plan before apply.

**Reversibility:** Easy — removing the resource block from `cloud_run.tf` and running `terraform apply` will destroy the Terraform-managed domain mapping. The domain itself (DNS records) is not managed by this resource and will not be affected.

**PM/Tech Lead review required:** Yes — the first `terraform plan` after this change must be reviewed before applying, to confirm that the existing manual domain mapping has the same configuration as the new Terraform resource.

---
**Decision ID:** DEC-002
**Agent:** IaC/DevOps Engineer
**Task ID:** cors-infra-investigation
**Timestamp:** 2026-05-06T13:30:00Z

**Context:**
The Flask application reads CORS allowed origins from the `ALLOWED_ORIGINS` environment variable, falling back to a hardcoded default in `backend/app.py`. The Terraform configuration did not set this variable, meaning the production Cloud Run service was relying on the hardcoded default. If the default ever diverges from the actual deployed origins (e.g., a Firebase project rename or the addition of a staging frontend), the mismatch would cause CORS failures that are invisible from the Terraform config.

**Options considered:**
1. Add `ALLOWED_ORIGINS` as an explicit env var in the Cloud Run container block with a new `var.allowed_origins` Terraform variable — makes the value auditable in IaC and environment-specific
2. Leave the value in the application code default — simpler, no Terraform change required, but not auditable from IaC

**Decision:** Option 1 — add explicit `ALLOWED_ORIGINS` env var to the Cloud Run container block.

**Rationale:** Infrastructure configuration belongs in infrastructure code. The CORS origin list is a deployment-time configuration value that differs per environment — it is not application logic. Expressing it in Terraform makes the value visible in the deployment config, allows per-environment overrides via `terraform.tfvars`, and ensures it cannot silently diverge from the Flask default. The Flask app already supports this variable; no backend code changes are needed.

**Trade-offs accepted:** The `var.allowed_origins` default includes both Firebase Hosting domains but not localhost. If a developer wants to use production Cloud Run with local frontend (unusual), they would need to override this variable — but that scenario is already handled by the `FLASK_ENV=development` path in the Flask app.

**Reversibility:** Easy — removing the env block from `cloud_run.tf` reverts to the Flask default, which is identical to the Terraform default value.

**PM/Tech Lead review required:** No

---
**Decision ID:** DEC-003
**Agent:** IaC/DevOps Engineer
**Task ID:** cors-port-fix
**Timestamp:** 2026-05-06T14:00:00Z

**Context:**
The production Dockerfile bound gunicorn to port 8080 (hardcoded in the CMD) but the Terraform `cloud_run.tf` declared `container_port = 5000`. Cloud Run's ingress layer uses the declared `container_port` to route incoming requests. When the declared port does not match the port the process is actually listening on, Cloud Run returns a 502 from its own infrastructure. A 502 from Cloud Run's ingress carries no application-level response headers, so the browser receives a response with no `Access-Control-Allow-*` headers and reports a CORS error — even though the Flask CORS configuration is entirely correct. This is the most likely root cause of the persistent CORS failures in production.

**Options considered:**
1. Change `container_port` in Terraform to 8080 and update the Dockerfile CMD to use `$PORT` — aligns the declared port with the actual listener; the `$PORT` binding ensures the two stay in sync if the default port ever changes
2. Change the Dockerfile gunicorn CMD to bind to port 5000 — works, but 5000 is not the Cloud Run default; Cloud Run injects `PORT=8080` and expects containers to use it

**Decision:** Option 1 — set `container_port = 8080` in Terraform and update the Dockerfile CMD to `gunicorn --bind "0.0.0.0:${PORT}" ...` so the binding reads the injected `PORT` value rather than hardcoding it.

**Rationale:** 8080 is the Cloud Run default and the value Cloud Run injects as `PORT`. Aligning both the Terraform declaration and the gunicorn binding to the injected `$PORT` value eliminates the possibility of this mismatch recurring if the default port is ever changed. It also follows the Cloud Run documentation's recommended pattern of reading the `PORT` environment variable in the container startup command.

**Trade-offs accepted:** The shell-form CMD (`CMD gunicorn --bind "0.0.0.0:${PORT}" ...`) differs from the previous exec-form CMD (`CMD ["gunicorn", ...]`). Shell form is required to expand environment variables. The behavior is otherwise identical.

**Reversibility:** Easy — this is a non-destructive change to a container startup command and a Terraform port declaration. No data or state is affected.

**PM/Tech Lead review required:** No — this is a bug fix correcting a misconfiguration. No functional behavior changes.
