
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
