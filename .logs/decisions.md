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

---
**Decision ID:** DEC-004
**Agent:** Frontend Engineer
**Task ID:** firebase-hosting-404-fix
**Timestamp:** 2026-05-14T00:00:00Z

**Context:**
The live website at https://aurafractor.web.app was returning a "Page Not Found" error on every page load. Firebase Hosting was configured to serve files from `ui/dist/`, but the web build workflow exports the site to `ui/dist/web/` (using `npx expo export --platform web --output-dir dist/web`). Because the configured public directory did not match the actual output directory, Firebase was looking for `ui/dist/index.html` which never existed — the real file was at `ui/dist/web/index.html`. Every visitor saw a 404.

**Options considered:**
1. Change `"public": "dist"` to `"public": "dist/web"` in `ui/firebase.json` — aligns the Hosting public directory with the actual build output; zero application code changes required
2. Change the Expo export command in the build workflow to output to `dist/` instead of `dist/web/` — would also fix the mismatch, but requires changing the source of truth (the build workflow) and risks breaking the artifact upload/download path which already uses `dist/web/`

**Decision:** Option 1 — update `ui/firebase.json` to `"public": "dist/web"`.

**Rationale:** The build workflow (`web-build.yml`) and the artifact download path in `web-deploy.yml` both use `dist/web/` as the canonical output location. Changing `firebase.json` to match the established output path is the minimal, non-breaking fix. Changing the export command's output directory (Option 2) would require coordinating changes across two workflow files and risks invalidating already-uploaded build artifacts.

**Trade-offs accepted:** None — this is a pure correction of a misconfiguration with no trade-offs.

**Reversibility:** Trivial — reverting one JSON field restores the previous (broken) state. No data or state is affected.

**PM/Tech Lead review required:** No — this is a bug fix that restores the site to working condition. No user-facing behavior changes beyond the site loading correctly.

---
**Decision ID:** DEC-005
**Agent:** Frontend Engineer
**Task ID:** firebase-hosting-404-fix
**Timestamp:** 2026-05-14T00:00:00Z

**Context:**
The `web-deploy.yml` workflow can be triggered in two ways: automatically after the "Web — Build" workflow completes (`workflow_run` event), or manually by a developer pressing "Run workflow" in GitHub Actions (`workflow_dispatch` event). The artifact download step that fetches the compiled site from the build workflow is guarded by `if: github.event_name == 'workflow_run'`, meaning it is intentionally skipped on manual runs. However, no build step existed to replace it — so a manual dispatch would proceed to the Firebase Deploy step with an empty checkout and no compiled files, deploying nothing (or overwriting the live site with an empty directory).

**Options considered:**
1. Add conditional build steps (setup-node, npm ci, expo export) that run only when `github.event_name == 'workflow_dispatch'` — ensures manual deploys always produce a fresh artifact from the current branch before deploying
2. Remove the `workflow_dispatch` trigger entirely — eliminates the broken path, but also removes the ability to perform a manual redeploy without pushing a new commit (useful for hotfixes and rollback scenarios)
3. Add a hard failure step when `workflow_dispatch` is used without a prebuilt artifact — safe but defeats the purpose of supporting manual dispatch

**Decision:** Option 1 — add three conditional steps (setup-node@v4 with node-version 20, `npm ci --legacy-peer-deps`, `npx expo export --platform web --output-dir dist/web`) each gated on `github.event_name == 'workflow_dispatch'`.

**Rationale:** Manual dispatch is a legitimate operational tool — it allows redeployment from a known-good commit without waiting for the full CI pipeline. Removing the trigger (Option 2) would take that capability away. Building inline on manual dispatch (Option 1) keeps the capability intact and mirrors what the automated `workflow_run` path does, just within a single job rather than two. The build steps are identical to those in `web-build.yml`, so there is no risk of producing a different artifact.

**Trade-offs accepted:** A manual dispatch takes longer than an automated deploy (it must run the full build before deploying), but this is the correct behaviour — a manual deploy should build from source rather than deploying a stale or empty artifact.

**Reversibility:** Easy — removing the three conditional steps reverts to the broken manual-dispatch behaviour. No data or state is affected.

**PM/Tech Lead review required:** No — this is a bug fix restoring correct CI behaviour. No user-facing product changes.

---
**Decision ID:** DEC-006
**Agent:** Frontend Engineer
**Task ID:** ad936f4d9b4f2170d
**Timestamp:** 2026-05-14T00:00:00Z

**Context:**
The task required implementing a first-launch onboarding moment (a modal or banner shown once when the user opens the app for the first time). No visual design reference was provided — no Figma file, mockup, or design token specification exists for this screen. The app uses a neon-pastel theme with design tokens already defined in `src/theme.ts` and `ThemeContext`. A decision was needed on how to implement the visual design in the absence of a spec.

**Options considered:**
1. Implement the modal using the existing project design tokens (`C.surface`, `C.primary`, `C.textPrimary`, `C.textSecondary`, `C.border`) from `ThemeContext` — produces a visually consistent result that matches the app's established aesthetic; can be replaced with a finalized design later with no structural changes
2. Block implementation pending a design reference — correct process in a fully staffed design pipeline, but this is a scope-defined task with no design resource assigned; blocking indefinitely would stall the feature

**Decision:** Option 1 — implement `FirstLaunchModal` using existing design tokens. Document the gap so the PM and designer can schedule a design pass.

**Rationale:** The modal's structure (title, body copy, CTA button) is stable regardless of the final visual design. Using existing tokens ensures the modal is theme-aware (light/dark), accessible, and visually consistent with the rest of the app. The component can be reskinned to a finalized design without changing its logic or tests. Blocking on a design reference would delay the auth retry work, which is also part of this task and has no design dependency.

**Trade-offs accepted:** The current visual design is functional but not finalized. A designer may choose different typography sizes, spacing, illustration, or animation. All of these are contained within `FirstLaunchModal.tsx` and require no changes to other files.

**Reversibility:** Easy — the modal is a standalone component. Any visual changes are confined to `src/components/FirstLaunchModal.tsx`. The storage key (`first_launch_seen`) and the dismissal logic are stable.

**PM/Tech Lead review required:** Yes — a designer should review the modal copy ("Welcome to Aurafractor", "No account needed…") and visual treatment before the feature ships to production. The current implementation is a functional placeholder.

---
**Decision ID:** DEC-007
**Agent:** Frontend Engineer
**Task ID:** auth-surface-registration
**Timestamp:** 2026-05-14T00:00:00Z

**Context:**
The `AuthResponse` from `POST /auth/register` includes an `is_new_user` boolean, but this field was not being used anywhere in the frontend. The task required surfacing a confirmation to the user after successful first-time registration. The `FirstLaunchModal` already existed and was already being shown on first launch via a storage-based flag (`first_launch_seen`). A decision was needed on whether to replace the storage-based trigger with an auth-based trigger, or to add an auth-based trigger that works alongside the storage-based one.

**Options considered:**
1. Replace the `first_launch_seen` storage trigger entirely with `is_new_user` from the auth API — cleaner, single source of truth; but requires a successful API call before the modal can ever appear, meaning a network failure on first launch would silently suppress the onboarding moment
2. Keep the storage-based trigger and add `is_new_user` as an additional signal that forces the modal visible (overrides the storage check) — provides belt-and-suspenders coverage: the modal appears immediately from the API signal, or falls back to the storage check if the API call has not yet resolved; on-dismiss, `first_launch_seen` is written in both paths so the modal never appears again

**Decision:** Option 2 — add `isNewUser` prop to `FirstLaunchModal`. When `isNewUser` is true the modal skips the storage read and renders immediately. On dismiss in both paths, `first_launch_seen` is written to storage so the modal never re-appears. The storage-based fallback remains for edge cases where the API flag is not available (e.g., tests that render the component without auth context).

**Rationale:** Option 2 preserves the robustness of the existing storage path while adding the new auth-signal path. The storage path continues to satisfy the existing tests without modification. The `isNewUser` prop defaults to `false`, so all existing call sites (including tests that render `<FirstLaunchModal />` without props) are unaffected.

**Trade-offs accepted:** If a user clears app storage manually (e.g., uninstalling and reinstalling), the storage flag will be gone and the modal may re-appear even if the backend still has their device registered. In that scenario, `loadAuth()` would return null (no stored token), `registerDevice` would be called again, and the backend may return `is_new_user: false` for the known device — which means the modal would not appear via the API path, and the storage path would show it (no `first_launch_seen` key). This is acceptable — reinstalling is effectively a fresh start for the local app state.

**Reversibility:** Easy — the `isNewUser` prop is optional and defaults to false. Removing the prop from `_layout.tsx` reverts to pure storage-based behaviour.

**PM/Tech Lead review required:** No — this is an internal implementation choice with no user-visible behaviour change from the prior release (modal continues to show once on first launch).

---
**Decision ID:** DEC-008
**Agent:** Frontend Engineer
**Task ID:** auth-surface-registration
**Timestamp:** 2026-05-14T00:00:00Z

**Context:**
The task description stated that the error UI shows "only a dismissible 'Backend unreachable' banner with no retry path." A review of the current `ui/app/(tabs)/_layout.tsx` showed that a Retry button already exists in the error banner alongside the dismiss button. The banner currently reads "Could not connect — some features unavailable" with a "Retry" button and a dismiss (X) button. This appears to have been implemented in a prior session. A decision was needed on whether to make further changes to the error UI or treat this as already complete.

**Options considered:**
1. Accept the existing error banner with Retry button as satisfying requirement 2 of the task — no additional changes needed; the retry CTA is already present and functional
2. Replace the banner with a more prominent full-screen error state (e.g., a blocking modal with a Retry button that cannot be dismissed) — stronger enforcement of the "retry path" intent, but would block the user from using the app in degraded mode

**Decision:** Option 1 — the existing error banner with Retry button already satisfies the "proper retry CTA" requirement. No additional changes to the tabs layout error UI.

**Rationale:** The banner exposes `retry` from `useAuth`, resets `dismissed` state on retry, and shows a loading spinner while the retry attempt is in flight. The error cannot become a dead end because the Retry button is always present alongside the dismiss control. The existing implementation is accessible (role="alert", aria-live="polite", accessibilityRole="button" on the Retry) and functional. A full-screen blocking error modal (Option 2) would reduce usability for users with intermittent connectivity who may want to read content already loaded.

**Trade-offs accepted:** The error banner can be dismissed, leaving no persistent retry CTA in view. A user who dismisses the banner has no way to retry without restarting the app. This is a known limitation and a design gap — a persistent connection status indicator (e.g., in the Settings tab) would address it.

**Reversibility:** N/A — no changes were made.

**PM/Tech Lead review required:** No.
