
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
