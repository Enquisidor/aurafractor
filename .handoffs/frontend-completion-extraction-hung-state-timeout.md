# Completion Artifact — Frontend Engineer

**Issue ID:** extraction-hung-state-timeout
**Issue title:** Extraction stuck in "processing" with no feedback — hung-state timeout
**Agent:** Frontend Engineer
**Timestamp:** 2026-05-14T00:00:00Z

---

## Files created or modified

| File | Change |
|------|--------|
| `ui/src/hooks/useExtraction.ts` | Added `isHung` boolean state; `processingStartedAtRef` for fallback elapsed-time tracking; hung-state detection logic per poll tick; `HUNG_THRESHOLD_MS` constant (10 min) exported; `isHung` returned from hook |
| `ui/src/components/ExtractionProgressBar.tsx` | Added optional `isHung` prop; hung-state render branch showing warning message and accessible Dismiss button with `router.canGoBack()` back-navigation pattern; `expo-router` import added |
| `ui/app/extraction/[id].tsx` | Destructured `isHung` from `useExtractionPoll`; passed `isHung` to `<ExtractionProgressBar>` |

---

## Implementation summary

`useExtractionPoll` now tracks how long an extraction has been in `processing` status. On each poll tick, when the status is `processing`, the hook computes elapsed time from `started_at` (backend-provided ISO 8601 timestamp) if available, or from a `useRef`-stored local timestamp of the first `processing` observation if `started_at` is null. When elapsed time exceeds `HUNG_THRESHOLD_MS` (600,000 ms / 10 minutes), `isHung` is set to `true`. Polling is not stopped — the backend may still complete. When the status reaches a terminal state (`completed` or `failed`), `isHung` is cleared and the fallback timer ref is reset.

`ExtractionProgressBar` gains an optional `isHung` prop (defaults to `false`). When `isHung` is true and `status === 'processing'`, the normal progress bar is replaced by a warning card reading "This is taking longer than expected. The extraction may still be running — check back later." with a Dismiss button. The Dismiss button uses the established back-navigation pattern: `router.canGoBack() ? router.back() : router.replace('/(tabs)/history')`. The warning card uses `accessibilityRole="alert"` to ensure screen readers announce it on render.

`extraction/[id].tsx` is updated to destructure `isHung` from `useExtractionPoll` and pass it through to `ExtractionProgressBar`.

---

## Deviations from spec

None. Implementation matches the directive exactly:
- `isHung` boolean in hook — done
- Elapsed time from `started_at` with `useRef` fallback — done
- Hung-state message text matches spec verbatim — done
- Dismiss button uses specified back-navigation pattern — done
- Polling continues when hung — done

---

## Design gaps

None. No visual design reference was specified. The hung-state card uses the existing `C.warningDim` / `C.warning` / `C.surface` / `C.border` design tokens, consistent with the ambiguous-labels warning card already present in the same screen. This design choice is documented: if the designer specifies a different visual treatment for the hung state (e.g., a distinct colour or icon), the change is contained within the `hungContainer` / `hungMessage` / `dismissButton` styles in `ExtractionProgressBar.tsx`.

---

## Test suite result

Command: `cd ui && npm test -- --watchAll=false`

```
Test Suites: 5 passed, 5 total
Tests:       33 passed, 33 total
Snapshots:   0 total
Time:        6.045 s
```

No failures. Pre-existing `act(...)` console warnings are unchanged from before this implementation (same pattern in `hooks.useAuth.test.ts` and `hooks.useExtraction.test.ts`).

---

Status: READY FOR PHASE-2 VERIFICATION
