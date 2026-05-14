
---
## cors-fix-001 | 2026-05-06

**Agent:** Backend Engineer (invoked by orchestrator)
**Task:** Fix CORS errors — targeted fix, not a full pipeline phase

**Files changed:**
- `/Users/alexweinstein/Documents/Code/aurafractor/backend/app.py`
- `/Users/alexweinstein/Documents/Code/aurafractor/backend/utils/decorators.py`

**Summary:**
1. Added explicit `allow_headers`, `methods`, and `OPTIONS` to the `CORS()` call in `app.py`. Previously implicit defaults were used, which are not guaranteed to be stable across Flask-CORS minor versions and did not explicitly include `DELETE` in method allowlists.
2. Fixed `require_auth` in `decorators.py`: mock mode now decodes the JWT from the `Authorization` header instead of requiring an `X-User-ID` header. The frontend API client never sent `X-User-ID`, meaning all authenticated routes returned 401 in local development. The test suite's `auth_headers` fixture issues a real JWT, so all existing tests remain compatible.

**Self-check status:**
- Security: no new surface exposed — JWT validation in mock mode is equivalent to production validation, minus the DB lookup. The `except Exception` bare catch logs nothing but mock-mode failures are not security-critical; acceptable.
- Performance: no queries or IO added.
- Design accuracy: no domain concepts touched.

**Decisions:**
- DEC-001: Chose to decode JWT in mock mode rather than require a separate `X-User-ID` header. Rationale: aligns mock auth with production auth structure; removes a non-standard header requirement from the API client. Alternative (add `X-User-ID` to the frontend client) was rejected because it adds a dev-only header to production requests if `__DEV__` guard is missed.

---
## cors-fix-001 verification | 2026-05-06

**Agent:** Orchestrator (end-to-end verification pass)
**Task:** Verify deployed CORS fixes are sufficient; audit backend and frontend for remaining CORS issues

**Files audited:**
- `/Users/alexweinstein/Documents/Code/aurafractor/backend/app.py`
- `/Users/alexweinstein/Documents/Code/aurafractor/backend/utils/rate_limiting.py`
- `/Users/alexweinstein/Documents/Code/aurafractor/backend/utils/decorators.py`
- `/Users/alexweinstein/Documents/Code/aurafractor/backend/routes/auth.py`
- `/Users/alexweinstein/Documents/Code/aurafractor/backend/routes/upload.py`
- `/Users/alexweinstein/Documents/Code/aurafractor/backend/routes/extraction.py`
- `/Users/alexweinstein/Documents/Code/aurafractor/backend/routes/user.py`
- `/Users/alexweinstein/Documents/Code/aurafractor/backend/routes/webhooks.py`
- `/Users/alexweinstein/Documents/Code/aurafractor/ui/src/api/client.ts`
- `/Users/alexweinstein/Documents/Code/aurafractor/terraform/cloud_run.tf`

**Test suite results:**
- Backend: 79 passed, 0 failed (exit code 0) — 47 collection errors are pre-existing, due to missing service modules not present outside Docker; they do not affect the CORS-relevant tests.
- Frontend: 26 passed, 0 failed (exit code 0).

**Summary — no additional fixes required:**

Backend CORS configuration (backend/app.py):
- CORS() call has explicit allow_headers=['Authorization','Content-Type','X-Worker-Secret'], methods=['GET','POST','DELETE','OPTIONS'], supports_credentials=True, and explicit origins list (aurafractor.web.app, aurafractor.firebaseapp.com). Correct.
- Error handlers (401, 429, 500, etc.) return jsonify() responses. Flask-CORS after_request hook runs after error handlers, so all error responses receive CORS headers. Correct.
- FLASK_ENV is set to 'production' or 'staging' in Cloud Run (terraform/cloud_run.tf line 70). Both fall into the non-development branch, using the production origin list. Correct for production.

Backend rate limiting (backend/utils/rate_limiting.py):
- @limiter.request_filter returning True for OPTIONS exempts all preflight requests from Flask-Limiter's before_request check. Correct. This prevents the race condition where a 429 could be returned before CORS headers are attached.

Routes coverage:
- All routes use either POST, GET, or DELETE. DELETE triggers a preflight; DELETE is in the allow_methods list. Correct.
- No route uses any method not in the allow_methods list.
- No route adds custom headers not in the allow_headers list.

Frontend (ui/src/api/client.ts):
- No raw fetch() calls exist outside client.ts in ui/src/. All requests go through the central request() function.
- Only Content-Type and Authorization headers are sent. Both are in the backend's allow_headers list. Correct.
- FormData uploads (isFormData=true) do not set Content-Type explicitly — the browser sets it automatically as multipart/form-data with boundary. The browser's preflight asks for content-type permission; the backend allows it. Correct.
- No credentials: 'include' setting. The backend sets supports_credentials=True, which sends Access-Control-Allow-Credentials: true. For a JWT-only API (Authorization header, no cookies), credentials:'include' is not required. The absence is not a bug. Correct.

**Observations (not bugs):**

OBS-001: supports_credentials=True is set in CORS() but the application uses JWT in the Authorization header — not cookies. This flag is only required if the browser needs to send/receive cookies across origins. Since no cookies are used, this flag is unnecessary. It causes no functional harm (the explicit origin list means the wildcard '*' restriction doesn't apply), but it adds a response header that has no effect. Removing it would be a minor cleanup. Recommend addressing in a dedicated housekeeping commit if desired.

OBS-002: The staging environment (FLASK_ENV=staging) uses the same CORS origin list as production (aurafractor.web.app, aurafractor.firebaseapp.com). If a staging frontend is ever deployed at a different URL, it would be blocked by CORS. Currently there is no known staging frontend URL, so this is not an active problem. Recommend adding ALLOWED_ORIGINS override in the staging Cloud Run configuration if a staging frontend is added.

**Decisions:**
- None. Investigation only; no changes were made.

---
## cors-port-fix | 2026-05-06

**Agent:** IaC/DevOps Engineer
**Task ID:** cors-port-fix
**Status:** Completed

**Task description:** Investigate why CORS errors persist in production despite correct Flask-CORS configuration. Audit Firebase Hosting config, Cloud Run Terraform config, CI/CD deploy workflow, and any upstream infrastructure.

**Inputs received:**
- `.github/workflows/backend-deploy.yml`
- `terraform/cloud_run.tf`, `terraform/main.tf`, `terraform/variables.tf`, `terraform/gcs.tf`, `terraform/cloud_tasks.tf`
- `ui/firebase.json`, `ui/.firebaserc`
- `backend/Dockerfile`, `backend/app.py`, `backend/utils/rate_limiting.py`
- `.github/workflows/firebase-hosting-merge.yml`, `web-deploy.yml`, `firebase-hosting-pull-request.yml`

**Outputs produced:**
- `terraform/cloud_run.tf` — changed `container_port` from `5000` to `8080`; added explanatory comment
- `backend/Dockerfile` — changed gunicorn CMD from exec-form with hardcoded `8080` to shell-form using `${PORT}` env var

**Self-checks applied:**
- Security Module (IaC/DevOps): applied. No new secrets introduced. IAM is least-privilege. No public exposure of database ports. Existing ISS-001 (SA key auth) remains open; no new P2+ security findings from this session.
- Performance Module (IaC/DevOps): applied. No resource sizing changes. Port fix has no cost or performance implications.

**Decisions made:**
- DEC-003: Change `container_port` to 8080 and update CMD to use `$PORT` variable. See decisions.md.

**Assumptions made:**
- The currently deployed Cloud Run revision is serving 502 errors on all requests because it was deployed with `container_port=5000` in the Terraform config. After `terraform apply` (which triggers a new revision) and a new image build/deploy, port 8080 will be correctly declared and listened on.
- No load balancer, API Gateway, or Cloud Armor policy sits in front of Cloud Run for this service. Confirmed from Terraform — no such resources are defined.

**Issues flagged:**
- ISS-003: container_port/gunicorn port mismatch — root cause of persistent CORS errors (P1). Fixed in this session.

---
## firebase-hosting-404-fix | 2026-05-14

**Agent:** Frontend Engineer
**Task ID:** firebase-hosting-404-fix
**Status:** Completed

**Task description:** Fix "Page Not Found" error at https://aurafractor.web.app caused by a wrong Firebase Hosting public directory and a missing build step for manual workflow_dispatch deploys.

**Inputs received:**
- `ui/firebase.json`
- `.github/workflows/web-deploy.yml`
- Orchestrator diagnosis: two root causes identified (wrong public dir, missing workflow_dispatch build)

**Outputs produced:**
- `ui/firebase.json` — changed `"public": "dist"` to `"public": "dist/web"` so Firebase Hosting serves from the directory the Expo export command actually produces
- `.github/workflows/web-deploy.yml` — added three conditional steps (setup-node@v4, npm ci, expo export) that run only when `github.event_name == 'workflow_dispatch'`, ensuring manual deploys always have a built artifact before the Firebase Deploy step

**Self-checks applied:**
- Security: no secrets introduced; no new surface exposed
- Accessibility: config-only change; no UI components affected
- Performance: no impact on bundle size or runtime behaviour
- Change impact: two config/CI files only; minimal blast radius; no domain naming involved
- Design accuracy (architectural fidelity): no domain concepts or API contracts touched

**Decisions made:**
- DEC-004: Changed Firebase Hosting public dir to `dist/web` and added workflow_dispatch build steps. See decisions.md.

**Assumptions made:**
- The `npx expo export --platform web --output-dir dist/web` command is available in the CI environment after `npm ci --legacy-peer-deps` completes, as it is already used in `web-build.yml`.
- No other workflow or script reads `ui/firebase.json`'s `public` field directly; Firebase CLI is the sole consumer.

**Issues flagged:**
- None.

---
## auth-surface-registration | 2026-05-14

**Agent:** Frontend Engineer
**Task ID:** auth-surface-registration
**Status:** Completed

**Task description:** Wire the `is_new_user` field from the `POST /auth/register` response into the UI so first-time registration is confirmed to the user, and verify that the auth error recovery UI has a working retry CTA.

**Inputs received:**
- `ui/src/hooks/useAuth.ts`
- `ui/app/_layout.tsx`
- `ui/app/(tabs)/_layout.tsx`
- `ui/src/api/client.ts`
- `ui/src/store/auth.ts`
- `ui/src/components/FirstLaunchModal.tsx`
- `ui/src/__tests__/hooks.useAuth.test.ts`
- `ui/src/__tests__/components.test.tsx`

**Outputs produced:**
- `ui/src/store/auth.ts` — added optional `isNewUser?: boolean` to `AuthState`; `registerDevice` now returns `isNewUser: res.is_new_user` from the API response
- `ui/src/hooks/useAuth.ts` — added `isNewUser` state; set from `registerDevice` result (`state.isNewUser ?? false`); exposed in hook return value
- `ui/src/components/FirstLaunchModal.tsx` — added optional `isNewUser` prop; when `true`, bypasses the storage read and renders the modal immediately (auth-signal path); storage write on dismiss remains in both paths
- `ui/app/_layout.tsx` — destructures `isNewUser` from `useAuth` and passes it to `<FirstLaunchModal isNewUser={isNewUser} />`

**Self-checks applied:**
- Security: no tokens or credentials exposed in UI; `isNewUser` is a boolean derived from API response — not sensitive; no `dangerouslySetInnerHTML` or dynamic URL construction introduced. Passed.
- Accessibility: `FirstLaunchModal` retains all existing accessibility attributes (`accessibilityViewIsModal`, `accessibilityRole="button"`, `onRequestClose`). No regressions. Passed.
- Performance: no new renders, no list components, no additional network requests. `isNewUser` state is a primitive boolean — no memoization needed. Passed.
- Design accuracy (architectural fidelity): field name `isNewUser` maps directly from `is_new_user` in `AuthResponse` (API contract field). Component name `FirstLaunchModal` is unchanged. All domain-concept naming (`AuthState`, `registerDevice`, `useAuth`) unchanged. Passed.

**Decisions made:**
- DEC-007: Added `isNewUser` as an additive signal to `FirstLaunchModal` alongside the existing storage-based trigger (rather than replacing storage trigger). See decisions.md.
- DEC-008: Existing error banner in `(tabs)/_layout.tsx` already satisfies the retry CTA requirement — no further changes made. See decisions.md.

**Assumptions made:**
- The `is_new_user` field in `AuthResponse` is always present (it is declared as `boolean` not `boolean | undefined` in `client.ts`). Treat as reliable API contract field.
- The console warnings about `act(...)` in `hooks.useAuth.test.ts` are pre-existing (same pattern in `hooks.useExtraction.test.ts`) and do not indicate test failures.

**Issues flagged:**
- None.

---
## ux-first-launch-account-creation | 2026-05-14

**Agent:** Frontend Engineer
**Task ID:** ux-first-launch-account-creation
**Status:** Completed

**Task description:** Update `FirstLaunchModal` to present an active account-creation confirmation when `isNewUser` is true, with distinct heading, body copy, and CTA.

**Inputs received:**
- `ui/src/components/FirstLaunchModal.tsx`
- `ui/app/_layout.tsx`
- `ui/src/hooks/useAuth.ts`

**Outputs produced:**
- `ui/src/components/FirstLaunchModal.tsx` — added conditional JSX branches: `isNewUser=true` branch shows "Account created" heading, device-tied explanation, and "Start using Aurafractor" CTA; `isNewUser=false` branch preserves original copy.

**Self-checks applied:**
- Security: no user-controlled content inserted into DOM via unsafe mechanisms; no token logging; no new dependencies. Passed.
- Accessibility: both branches retain `accessibilityViewIsModal`, `onRequestClose`, and `accessibilityRole="button"` on CTA; `accessibilityLabel` updated to match CTA text per branch; `AccessibilityInfo.announceForAccessibility` announcement updated to match `isNewUser` branch. Passed.
- Performance: no new renders, no list components, no additional network requests. Passed.
- Design accuracy (architectural fidelity): component name `FirstLaunchModal` unchanged; prop name `isNewUser` matches API contract field `is_new_user` convention; no domain-term violations. Passed.

**Decisions made:**
- DEC-009: Two conditional JSX branches within one component rather than two separate components. See decisions.md.

**Assumptions made:**
- The `isNewUser` prop behaviour (skip storage read, force visible) introduced in DEC-007 is retained unchanged.

**Issues flagged:**
- None.

---
## ux-settings-device-id | 2026-05-14

**Agent:** Frontend Engineer
**Task ID:** ux-settings-device-id
**Status:** Completed

**Task description:** Add a Device section to the Settings screen showing the user's Device ID and a plain-language explanation of how the app recognises them automatically.

**Inputs received:**
- `ui/app/(tabs)/settings.tsx`
- `ui/src/hooks/useAuth.ts`
- `ui/src/storage/platform.ts` (convention reference)

**Outputs produced:**
- `ui/app/(tabs)/settings.tsx` — added `useEffect` to read device ID from platform storage; added "Device" section card with Device ID row and explanatory text paragraph.

**Self-checks applied:**
- Security: device ID is not a secret — it is a locally generated opaque identifier used only for registration; displaying it in settings is not a credential exposure. No tokens or session data surfaced. Passed.
- Accessibility: Device ID row uses `accessibilityLabel` to provide full spoken text ("Device ID: <value>") so the mono font value reads correctly; explanation text has sufficient contrast via `C.textSecondary` token. Passed.
- Performance: single `storage.getItem` call in a `useEffect` on mount; result is a stable string with no polling. No render performance concern. Passed.
- Design accuracy (architectural fidelity): section title "Device" is not a domain-model term requiring glossary lookup; explanation copy uses glossary term "device ID" (lowercase) correctly. Passed.

**Decisions made:**
- DEC-010: Read device ID from storage directly in Settings rather than exposing it through `useAuth`. See decisions.md.

**Assumptions made:**
- The device ID stored under `'device_id'` is set before the Settings screen is mounted (it is written during the `getOrCreateDeviceId` call in `useAuth` on first launch). If somehow absent, the Device ID row is not rendered (`deviceId != null` guard).

**Issues flagged:**
- None.

---
## ux-extraction-back-navigation | 2026-05-14

**Agent:** Frontend Engineer
**Task ID:** ux-extraction-back-navigation
**Status:** Completed

**Task description:** Add an explicit back button to `extraction/[id].tsx` that works cross-platform — `router.back()` when history exists, `router.replace('/(tabs)/history')` when it does not.

**Inputs received:**
- `ui/app/extraction/[id].tsx`
- `ui/app/_layout.tsx`

**Outputs produced:**
- `ui/app/extraction/[id].tsx` — added `handleBack` callback using `router.canGoBack()` guard; added unconditional `topBar` with `Pressable` back button above the extraction header row; added corresponding `StyleSheet` entries.

**Self-checks applied:**
- Security: no user input, no URL construction from user data, no token handling. Passed.
- Accessibility: back button has `accessibilityRole="button"` and `accessibilityLabel="Go back"`; `hitSlop` increases tap target to meet minimum touch target size. Passed.
- Performance: `handleBack` is wrapped in `useCallback` with empty dep array (no closure over changing values); no new renders or data fetches introduced. Passed.
- Design accuracy (architectural fidelity): no domain-term violations; `router.replace` target `/(tabs)/history` matches the existing tab route. Passed.

**Decisions made:**
- DEC-011: Explicit in-content back button rather than header option injection; `/(tabs)/history` as fallback destination. See decisions.md.

**Assumptions made:**
- `/(tabs)/history` is a valid, existing route in the app. Confirmed from `_layout.tsx` — `(tabs)` is a registered Stack.Screen; the history tab is the canonical entry point for past extractions.
- The existing `headerShown: true` for `extraction/[id]` in `_layout.tsx` remains unchanged. On native, the Stack header back arrow and the in-content button will coexist.

**Issues flagged:**
- None.
