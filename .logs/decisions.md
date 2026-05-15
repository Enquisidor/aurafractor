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

---
**Decision ID:** DEC-009
**Agent:** Frontend Engineer
**Task ID:** ux-first-launch-account-creation
**Timestamp:** 2026-05-14T00:00:00Z

**Context:**
The `FirstLaunchModal` previously showed identical copy ("You're all set!" / "Welcome to Aurafractor") regardless of whether the user was a brand-new registrant or a returning user who had cleared their storage. The PM raised that the `isNewUser` prop (already wired to the auth API's `is_new_user` field) should be used to differentiate the modal's tone: when a new account has just been created, the moment should feel like an active confirmation the user did something, not a passive welcome. A decision was needed on how to structure the two variants.

**Options considered:**
1. Render two separate JSX branches within the same component, each with distinct heading, body copy, CTA text, and accessibility announcement — no separate component files required; the `isNewUser` boolean is the only branch condition
2. Extract two separate components (`AccountCreatedModal` and `WelcomeModal`) — cleaner isolation, but adds two new component files and an indirection layer for a feature that is a single controlled Boolean

**Decision:** Option 1 — two conditional JSX branches within `FirstLaunchModal`. When `isNewUser` is true: heading is "Account created", body copy explains device-tied account and no password requirement, CTA reads "Start using Aurafractor". When `isNewUser` is false: original heading/copy/CTA unchanged ("Welcome to Aurafractor" / "Get started").

**Rationale:** The two variants share identical structural markup (backdrop, card, title, body, CTA), identical animation, and identical dismiss logic — they differ only in text. Extracting two components would duplicate that structure for no functional benefit. A single boolean branch within one component is readable and matches the existing prop signature.

**Trade-offs accepted:** Both variants share the same `StyleSheet` — if the designer specifies a visually distinct treatment for the "Account created" variant (e.g., a success icon or green accent), the shared styles would need to be split. This is a low-effort future change contained entirely within `FirstLaunchModal.tsx`.

**Reversibility:** Easy — revering to the original copy requires removing the conditional branch.

**PM/Tech Lead review required:** Yes — the new copy ("Account created", "Your Aurafractor account is tied to this device…", "Start using Aurafractor") is user-facing and should be reviewed by the PM before shipping.

---
**Decision ID:** DEC-010
**Agent:** Frontend Engineer
**Task ID:** ux-settings-device-id
**Timestamp:** 2026-05-14T00:00:00Z

**Context:**
The Settings screen previously showed the backend User ID (from `auth.userId`) but did not explain how the app recognises returning users, which the PM flagged as confusing. The device ID (the stable local identifier stored under `'device_id'` in platform storage) is more meaningful as a user-facing identifier because it is what the app actually uses to recognise the device on each launch. The `useAuth` hook generates and stores this value but does not expose it in its return value. A decision was needed on how to surface it in the Settings screen.

**Options considered:**
1. Read the device ID directly from `storage.getItem('device_id')` in a `useEffect` inside the Settings screen — no changes to `useAuth` or any other shared module; the device ID is a single stable value that does not change after creation
2. Add `deviceId` to `useAuth`'s return value — makes the device ID part of the auth context and available to any future screen that needs it; requires modifying a shared hook

**Decision:** Option 1 — read from storage directly in Settings. The device ID is a static value after first creation; there is no reactivity requirement (it never changes during a session), so a one-shot `useEffect` with `storage.getItem` is sufficient. The `DEVICE_ID_KEY` constant is co-located with the existing constant in `useAuth.ts` — re-declaring it locally in `settings.tsx` is a minor duplication but avoids coupling the settings screen to the hook's internals.

**Rationale:** Option 2 would expose a storage key implementation detail through a domain hook whose primary concern is auth state. The device ID is not an auth concern — it is a device identity concern. Reading it locally in the one screen that needs to display it is the lower-coupling choice. If a second screen ever needs the device ID, that is the right time to promote it to a shared abstraction.

**Trade-offs accepted:** The `DEVICE_ID_KEY = 'device_id'` string is now duplicated in `useAuth.ts` and `settings.tsx`. A key rename would require updating both files. This is a known acceptable duplication for a stable, low-change string constant.

**Reversibility:** Easy — removing the Device section from settings.tsx removes the read.

**PM/Tech Lead review required:** No.

---
**Decision ID:** DEC-011
**Agent:** Frontend Engineer
**Task ID:** ux-extraction-back-navigation
**Timestamp:** 2026-05-14T00:00:00Z

**Context:**
On web, navigating to `/extraction/<id>` via a direct URL (e.g., copy-pasted or bookmarked) leaves the browser history stack empty. Expo Router's automatic back arrow in the Stack header relies on `router.canGoBack()` being true — when the stack is empty, no arrow is rendered. The extraction screen had no fallback, leaving web users with no way to navigate away without using the browser's own back button or manually changing the URL.

**Options considered:**
1. Add an explicit back button rendered unconditionally inside the screen's `ScrollView` content area, using `router.canGoBack()` to choose between `router.back()` and `router.replace('/(tabs)/history')` as the fallback — works on both native and web; always visible regardless of header state
2. Use `useNavigation().setOptions({ headerLeft: ... })` to inject a custom back button into the Stack header — keeps the button in the header position consistent with native conventions, but the header is controlled by `_layout.tsx` and the screen option injection is fragile across Expo Router versions; also does not help when `headerShown: true` but the auto back button is suppressed

**Decision:** Option 1 — explicit back button rendered inside the screen content, above the header metadata row. The button uses a left-arrow glyph and "Back" label. The fallback destination is `/(tabs)/history` (the extractions history tab), which is the most logical prior context for an extraction detail view.

**Rationale:** Option 1 is entirely self-contained in `extraction/[id].tsx` with no dependency on layout options or navigation internals. The button is always present and therefore always testable. On native, it appears alongside (not instead of) the Stack header's automatic back arrow — this slight redundancy is acceptable; the native back arrow will be the primary affordance and the in-content button serves as a fallback for web.

**Trade-offs accepted:** On native, the screen will show two back affordances: the Stack header arrow and the in-content button. This is mildly redundant but not harmful. A designer may choose to hide the in-content button on native using `Platform.select` in a future pass — this is a documented design gap.

**Reversibility:** Easy — removing the `topBar` and `backButton` styles and the `handleBack` handler reverts to the prior state.

**PM/Tech Lead review required:** No — this is a cross-platform navigation correctness fix.

---
**Decision ID:** DEC-012
**Agent:** Frontend Engineer
**Task ID:** first-launch-modal-returning-device
**Timestamp:** 2026-05-14T00:00:00Z

**Context:**
The `FirstLaunchModal` previously had two display states keyed on the `isNewUser` prop: a "new user" branch (account-creation confirmation) and a catch-all `false` branch (generic "Get started" copy). A PM bug report identified that a returning user — one whose device was already registered in a prior session but whose `first_launch_seen` storage flag is absent (e.g. after app reinstall or storage clear) — sees the generic "Get started" copy and then discovers they are already logged into an existing account with no explanation. This creates confusion: the user does not know their device was recognised.

The modal needed a third distinguishable state within the `isNewUser === false` branch to differentiate "returning device, account auto-restored" from "genuine first launch, registration pending." The challenge is that the `isNewUser` prop alone cannot make this distinction — it is `false` in both cases (the auth hook sets it `false` when loading from existing storage, which happens before the modal's `useEffect` runs for the storage-check path, and it is also `false` on a genuine first launch before registration completes).

**Options considered:**
1. Check for a stored session token (`'session_token'` key, same key used by `src/store/auth.ts`) inside the modal's `useEffect`, alongside the existing `first_launch_seen` check. If a token is present when the modal would otherwise show, the user is a returning device. This check is self-contained within the component and requires no prop changes or hook modifications.
2. Add a third `variant` prop to `FirstLaunchModal` (e.g. `variant: 'new-user' | 'returning' | 'first-launch'`) and resolve the variant in the calling `_layout.tsx` — moves the discrimination logic to the call site. Requires the caller to also read the session token from storage, adding async logic to `_layout.tsx` that is not currently there.

**Decision:** Option 1 — check for `'session_token'` in storage within the modal's `useEffect`, using `Promise.all` to read both `first_launch_seen` and `session_token` in parallel. If `first_launch_seen` is absent and a session token exists, render the "Welcome back" variant. If `first_launch_seen` is absent and no token exists, render the original "Get started" variant. The internal `variant` state (`'new-user' | 'returning-device' | 'first-launch'`) replaces the `isNewUser` boolean as the rendering discriminator, while the `isNewUser` prop interface is preserved unchanged.

**Rationale:** Option 1 keeps the discrimination logic co-located with the modal's own storage reads. The modal already reads `first_launch_seen` from storage; reading `session_token` in the same `Promise.all` adds no additional async round-trips. Adding a new prop (Option 2) would expose an implementation detail (the three-way split) through the component's public interface and require the caller to perform an async storage read it currently does not need to do. The `'session_token'` key is a stable constant defined in `src/store/auth.ts`; it is duplicated as a local constant (`SESSION_TOKEN_KEY`) in the modal — the same acceptable duplication pattern already used for `DEVICE_ID_KEY` in `settings.tsx` (DEC-010).

**Trade-offs accepted:** If the session token key in `src/store/auth.ts` is ever renamed, `SESSION_TOKEN_KEY` in `FirstLaunchModal.tsx` must also be updated. This duplication is low-risk: the key is a stable, rarely-changed constant, and a mismatch would cause the "returning device" variant never to render (falling back to "Get started") — a degraded but not broken experience.

**Reversibility:** Easy — reverting to the two-branch `isNewUser` boolean condition removes the storage check and the `variant` state.

**PM/Tech Lead review required:** Yes — the new copy ("Welcome back", "We recognised your device and restored your account automatically. No password needed — your account is always tied to this device.") is user-facing and should be reviewed before shipping.

---
**Decision ID:** DEC-013
**Agent:** Frontend Engineer
**Task ID:** extractions-cache-and-rerun-guard
**Timestamp:** 2026-05-14T00:00:00Z

**Context:**
The new `extractionsSlice` requires a storage key under which the extractions map is persisted to platform storage. The uploadQueueSlice uses `'upload_queue'`. A consistent naming convention is needed for the new key.

**Options considered:**
1. Use `'extractions_cache'` — describes the purpose (a cache of ExtractionResponse objects) and follows the same noun_noun pattern as `'upload_queue'`
2. Use `'extractions'` — shorter but ambiguous; could be confused with a canonical source of record rather than a client-side cache

**Decision:** Option 1 — storage key `'extractions_cache'`.

**Rationale:** The `_cache` suffix communicates that this is a local performance optimisation rather than an authoritative data source. The backend is the source of truth; the cache is advisory. This distinction matters for future developers deciding how to handle stale data.

**Trade-offs accepted:** If the cache key ever needs to change (e.g. schema migration), all existing cached data will be silently ignored (key won't match). This is acceptable — the cache is re-built from polling.

**Reversibility:** Trivial — change the `PERSIST_KEY` constant in `extractionsSlice.ts`.

**PM/Tech Lead review required:** No.

---
**Decision ID:** DEC-014
**Agent:** Frontend Engineer
**Task ID:** extractions-cache-and-rerun-guard
**Timestamp:** 2026-05-14T00:00:00Z

**Context:**
The `useExtractionPoll` hook needed to dispatch `upsertExtraction` after each successful poll so the Redux store stays current. Two implementation approaches were available: (1) add `useDispatch` directly inside the hook, or (2) keep the hook Redux-free and have the calling screen dispatch the poll result.

**Options considered:**
1. Add `useDispatch` inside `useExtractionPoll` — the hook becomes the single responsible unit for both fetching and storing
2. Return `data` from the hook unchanged; the calling screen (ExtractionScreen) dispatches `upsertExtraction` in a `useEffect` watching `polledData` — the hook stays a pure data-fetching primitive

**Decision:** Option 2 — keep `useExtractionPoll` Redux-free; dispatch from the screen.

**Rationale:** Option 1 was initially implemented but caused the existing `hooks.useExtraction.test.ts` tests to fail because the test renders the hook without a Redux Provider. Since tests cannot be modified, the hook must be usable without a Provider context. Option 2 is also the architecturally cleaner separation: the hook is a reusable fetching primitive; Redux side effects belong in the component or screen layer that is always wrapped in a Provider.

**Trade-offs accepted:** Any future component that uses `useExtractionPoll` must remember to also dispatch `upsertExtraction` if it wants the result cached. This is a documentation and convention concern, not a correctness risk — the worst case is a cache miss on next mount.

**Reversibility:** Easy — adding `useDispatch` back to the hook (with a provider requirement) reverts to Option 1.

**PM/Tech Lead review required:** No.

---
**Decision ID:** DEC-015
**Agent:** Frontend Engineer
**Task ID:** extractions-cache-and-rerun-guard
**Timestamp:** 2026-05-14T00:00:00Z

**Context:**
The `hydrateExtractions` thunk needs to be called at app startup alongside `hydrateUploadQueue`. The correct call site is `RootLayoutInner` in `app/_layout.tsx`, which already dispatches `hydrateUploadQueue` in a `useEffect` on mount.

**Options considered:**
1. Dispatch `hydrateExtractions` in the same `useEffect` as `hydrateUploadQueue` in `_layout.tsx` — co-locates all startup hydration in one effect; both dispatches fire simultaneously (Promise.all semantics via independent async thunks)
2. Create a dedicated `useHydrateStore` hook that encapsulates all startup hydration — cleaner abstraction but adds an indirection file for a simple two-line dispatch pattern

**Decision:** Option 1 — dispatch both thunks in the existing `useEffect` in `RootLayoutInner`.

**Rationale:** The current codebase has two startup side effects (hydrate + sync). Adding a third dispatch to the existing effect keeps all startup data loading visible in one place. The `useEffect` comment is updated to reflect both dispatches. A dedicated hook would be worthwhile if the number of startup dispatches grows significantly, but that is a future refactor decision.

**Trade-offs accepted:** None significant.

**Reversibility:** Trivial — remove the `hydrateExtractions()` dispatch line.

**PM/Tech Lead review required:** No.

---
**Decision ID:** DEC-016
**Agent:** Frontend Engineer
**Task ID:** extractions-cache-and-rerun-guard
**Timestamp:** 2026-05-14T00:00:00Z

**Context:**
Task B requires an `Alert.alert` confirmation before any extraction re-run. The re-run button is placed on the `failed` status state of the extraction detail screen. A question arose about what API call the re-run should make — the `ExtractionResponse` for a failed extraction has a `track_id` but not the original source list (labels/models). The only re-extraction API available is `POST /extraction/extract` which requires `sources[]`.

**Options considered:**
1. Call `extraction.extract(track_id, [])` with an empty sources array — technically non-standard but acceptable as a "re-run with defaults" intent; the backend decides what to do with no sources
2. Navigate back to the upload flow with the track_id pre-populated so the user explicitly picks labels for the re-run — safer but changes the re-run UX from the extraction detail screen
3. Show the Alert confirmation and, if confirmed, navigate to the home tab for the user to pick labels and then re-extract — preserves correct source selection but removes the "re-run in-place" experience

**Decision:** Option 1 — call `extraction.extract(track_id, [])` after confirmation. The Alert message and button text ("Re-run extraction?", "Re-run") communicate that this consumes credits. The empty sources array is documented with a comment in the code.

**Rationale:** The task specifies the Alert dialog content verbatim and says "proceeds" after confirmation — implying an immediate action, not a navigation. Option 1 satisfies the spec literally. If the API rejects an empty sources array, the error is surfaced in the UI via `rerunError` state. This is an escalatable scenario — if the API spec clarifies that sources must be non-empty, this call site needs to be updated to navigate to the label-selection flow instead.

**Trade-offs accepted:** The re-run with empty sources may behave unexpectedly if the backend does not support zero sources. This is flagged as a potential spec ambiguity (see issue log).

**Reversibility:** Easy — the `handleRerun` callback is self-contained. Changing the action to navigation requires only modifying the `onPress` handler.

**PM/Tech Lead review required:** Yes — the re-run UX (in-place vs. navigate to label selection) and the empty sources behaviour should be confirmed with the PM before shipping.

---
**Decision ID:** DEC-017
**Agent:** Frontend Engineer
**Task ID:** extraction-hung-state-timeout
**Timestamp:** 2026-05-14T00:00:00Z

**Context:**
The `useExtractionPoll` hook needed a threshold after which a long-running `processing` extraction is considered "hung" and a user-facing warning is surfaced. No threshold value was specified in the task's issue spec. The threshold determines both how long a user waits before seeing the warning and how often the warning is incorrectly shown for legitimate slow extractions (e.g., long tracks processed by Demucs on a busy worker).

**Options considered:**
1. 10 minutes — aligns with observed Demucs processing times for tracks up to ~10 minutes; long enough to avoid false positives for typical extractions while short enough that a genuinely stuck extraction is surfaced within a reasonable user session window. This is the value specified in the bug report directive.
2. 5 minutes — surfaces the warning sooner but risks false positives for long tracks; would require backend-side data on typical processing durations to tune safely.
3. 15 minutes — reduces false positives further but leaves users waiting without feedback for an excessively long period.

**Decision:** Option 1 — 10 minutes (600,000 ms), exported as `HUNG_THRESHOLD_MS` from `useExtraction.ts` so tests and future callers can reference the constant without a magic number.

**Rationale:** The bug report directive specifies 10 minutes as the default threshold. In the absence of backend-provided p95 processing time data, 10 minutes is a conservative choice that prevents false positives while still surfacing genuinely stuck extractions within a user session. The constant is exported to allow tests to assert on the exact value and to make future tuning (if backend metrics show a different p95) a single-file change.

**Trade-offs accepted:** If the backend's actual p95 processing time exceeds 10 minutes for common inputs (long tracks, high source count), some users will see the warning for extractions that eventually succeed. This is acceptable: the message explicitly says "may still be running" and polling continues — no data is lost and no action is forced on the user.

**Reversibility:** Easy — change `HUNG_THRESHOLD_MS` in `src/hooks/useExtraction.ts`. No UI component needs to change.

**PM/Tech Lead review required:** Yes — the 10-minute threshold should be reviewed against actual backend processing time p95 data before shipping. If workers typically take longer than 10 minutes for studio-tier extractions, the threshold should be raised.
