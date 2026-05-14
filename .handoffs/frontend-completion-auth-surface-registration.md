# Frontend Completion Artifact

**Issue ID:** auth-surface-registration
**Issue title:** Fix silent registration — surface auth state to the user
**Agent:** Frontend Engineer
**Timestamp:** 2026-05-14T00:00:00Z

---

## Files created or modified

| File | Change |
|------|--------|
| `ui/src/store/auth.ts` | Added optional `isNewUser?: boolean` to `AuthState` interface; `registerDevice` now includes `isNewUser: res.is_new_user` in the returned state |
| `ui/src/hooks/useAuth.ts` | Added `isNewUser` state variable; populated from `registerDevice` result (`state.isNewUser ?? false`); exposed in hook return value alongside `auth`, `loading`, `error`, `retry` |
| `ui/src/components/FirstLaunchModal.tsx` | Added optional `isNewUser` prop (defaults to `false`); when `true`, bypasses `first_launch_seen` storage check and renders the modal immediately; `first_launch_seen` is still written on dismiss in both paths |
| `ui/app/_layout.tsx` | Destructures `isNewUser` from `useAuth()`; passes it as `<FirstLaunchModal isNewUser={isNewUser} />` |

---

## Implementation summary

The `is_new_user` field from `POST /auth/register` was already present in `AuthResponse` but was discarded in `registerDevice`. This change threads it through the auth store (`AuthState.isNewUser`), the `useAuth` hook, and into `_layout.tsx` where it is passed to `FirstLaunchModal`.

`FirstLaunchModal` now has two trigger paths: the existing storage-based path (`first_launch_seen` key absent) and a new auth-signal path (`isNewUser === true`). Both paths are satisfied by the same UI and the same `handleStart` dismiss handler, which writes `first_launch_seen` so the modal does not re-appear.

The auth error recovery UI in `(tabs)/_layout.tsx` already contained a Retry button alongside the dismiss control — this satisfies the retry CTA requirement with no further changes. Decision DEC-008 records this finding.

All existing tests continue to pass: `isNewUser` is optional and defaults to `false`, so existing `<FirstLaunchModal />` usages (including those in tests) are unaffected. `MOCK_AUTH_STATE` in the `useAuth` tests does not include `isNewUser`, which correctly produces `isNewUser === false` via `state.isNewUser ?? false`.

---

## Deviations from spec

None. The API contract field `is_new_user` is consumed exactly as documented in `AuthResponse`. No undocumented endpoint behaviour was used.

---

## Design gaps

| Gap | Decision | What's needed to revisit |
|-----|----------|--------------------------|
| No visual design reference for `FirstLaunchModal` (pre-existing, logged as DEC-006) | Implemented using existing design tokens (`C.surface`, `C.primary`, etc.) | Designer pass with Figma mockup |
| After banner dismiss, no persistent retry CTA remains visible (logged as DEC-008) | Accepted as-is; existing banner satisfies immediate retry path | PM decision on whether a persistent connection status indicator is needed (e.g., in Settings tab) |

---

## Test suite result

Command: `cd /Users/alexweinstein/Documents/Code/aurafractor/ui && npm test -- --watchAll=false`

```
Test Suites: 5 passed, 5 total
Tests:       33 passed, 33 total
Snapshots:   0 total
Time:        3.994 s
```

No failures. No regressions.

---

Status: READY FOR PHASE-2 VERIFICATION
