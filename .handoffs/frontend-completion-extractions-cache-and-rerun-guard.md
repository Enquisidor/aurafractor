# Frontend Completion Artifact
## Issue: extractions-cache-and-rerun-guard
**Agent:** Frontend Engineer
**Timestamp:** 2026-05-14T00:00:00Z

---

## Files Created or Modified

| File | Change |
|------|--------|
| `ui/src/store/extractionsSlice.ts` | NEW — Redux Toolkit slice with `upsertExtraction`, `clearExtractions`, `hydrateExtractions`, `selectExtraction`; persists to `'extractions_cache'` storage key on every upsert |
| `ui/src/store/store.ts` | MODIFIED — added `extractions: extractionsReducer` to configureStore reducer map; updated `RootState` type |
| `ui/app/_layout.tsx` | MODIFIED — added `hydrateExtractions` dispatch in startup `useEffect` alongside `hydrateUploadQueue` |
| `ui/src/hooks/useExtraction.ts` | NOTE — `useDispatch` was NOT added (see DEC-014); hook remains Redux-free; dispatch responsibility stays in calling screen |
| `ui/app/extraction/[id].tsx` | MODIFIED — cache-first strategy via `useSelector(selectExtraction)`; `useEffect` dispatches `upsertExtraction` on each poll result; `handleRerun` with `Alert.alert` confirmation dialog; "Re-run Extraction" button on `failed` status |
| `ui/jest.config.js` | MODIFIED — added `react-redux`, `@reduxjs/toolkit`, `immer` to `transformIgnorePatterns` so ESM dist files are transpiled by babel-jest |

---

## Implementation Summary

Task A: `extractionsSlice.ts` stores a map of `extraction_id → ExtractionResponse` in Redux. On every `upsertExtraction` dispatch, the full map is written to platform storage under `'extractions_cache'`. On app startup, `hydrateExtractions` reads and restores the map. The extraction detail screen (`[id].tsx`) reads from the store via `selectExtraction` before starting a poll — if a terminal result (`completed` or `failed`) is already cached, polling is skipped and the cached result is displayed immediately.

Task B: The `failed` status block in `[id].tsx` now includes a "Re-run Extraction" `Pressable` button. Tapping it calls `handleRerun`, which opens an `Alert.alert` with title "Re-run extraction?" and a message that includes the credit cost from `ExtractionResponse.cost_credits` if available, or the fallback text "This will use credits. Continue?" if not. The alert has two buttons: "Cancel" (dismisses, no action) and "Re-run" (proceeds with `extraction.extract`).

---

## Deviations from Spec

- **DEC-013:** Storage key `'extractions_cache'` chosen (not `'extractions'`) to communicate advisory cache semantics.
- **DEC-014:** `useDispatch` not added to `useExtractionPoll` hook — kept Redux-free to preserve test compatibility. Dispatch moved to extraction screen.
- **DEC-015:** `hydrateExtractions` dispatched in the existing startup `useEffect` in `_layout.tsx` alongside `hydrateUploadQueue`.
- **DEC-016:** Re-run action calls `extraction.extract(track_id, [])` with empty sources array. The spec does not define backend behaviour for zero sources — see ISS-004. PM/Architect review required before shipping.

---

## Design Gaps

- No visual design reference exists for the "Re-run Extraction" button. Implemented using `C.primary` background, white text, and 12px border radius consistent with existing action buttons in the extraction screen. This is a design gap: a designer may specify a different treatment (e.g., secondary/destructive style, warning colour).
- The confirmation Alert dialog uses React Native's platform-native `Alert.alert`. On web, this is rendered as a browser `confirm` dialog which has no custom styling. A custom in-screen confirmation UI may be desired for web — this is a design gap.

---

## Test Suite Result

Command: `cd /Users/alexweinstein/Documents/Code/aurafractor/ui && npm test -- --watchAll=false`

```
Test Suites: 5 passed, 5 total
Tests:       33 passed, 33 total
Snapshots:   0 total
Time:        ~6s
```

All 33 tests pass. No regressions. The `console.error act()` warnings are pre-existing (confirmed in session notes for prior tasks) and are not test failures.

---

## Open Questions / Escalations

1. **ISS-004 (P2):** What should the backend do when `POST /extraction/extract` receives an empty `sources` array? Three options: (a) use the track's original source configuration, (b) return 422 requiring non-empty sources, (c) include original sources in `ExtractionResponse` so the frontend can re-use them. PM/Architect must resolve before the re-run feature ships.

2. **DEC-016 (PM/Tech Lead review required):** The re-run UX (in-place immediate re-run vs. navigate to label-selection flow) should be confirmed with the PM.

---

Status: AWAITING TECH LEAD REVIEW — do not proceed to phase-2 until ISS-004 and DEC-016 are resolved
