/**
 * Waveform visualiser with playback cursor and drag-to-select segment annotation.
 *
 * Fetches a `{ peaks: number[] }` JSON from `waveformUrl` and renders it as a
 * bar chart.  While the JSON is loading a placeholder wave is shown at low
 * opacity so the layout does not shift.
 *
 * Interaction:
 *   - Tap (no drag) → seek to that position (calls onSeek with ms value).
 *   - Drag when selectionMode is true → draws a segment; calls
 *     onSegmentChange(startSeconds, endSeconds) on release.
 *   - Tap anywhere when selectionMode is false always seeks.
 *
 * Visual layers (bottom → top):
 *   1. Bar chart — each bar coloured by state:
 *      • inside selected segment  → fuchsia
 *      • already played           → primary
 *      • future                   → border (muted)
 *   2. Semi-transparent segment overlay rectangle.
 *   3. Thin playback cursor line.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  PanResponder,
  StyleSheet,
  View,
} from 'react-native';
import { useTheme } from '../contexts/ThemeContext';

interface Props {
  waveformUrl: string;
  /** Total duration in milliseconds (from useAudioPlayer). */
  durationMs: number;
  /** Current playback position in milliseconds. */
  positionMs: number;
  /** Called with position in milliseconds when user taps to seek. */
  onSeek: (ms: number) => void;
  /** When true, drag gestures create a segment instead of seeking. */
  selectionMode: boolean;
  /** Selected segment start in seconds (null = no selection). */
  segmentStartS: number | null;
  /** Selected segment end in seconds. */
  segmentEndS: number | null;
  /** Called when the user finishes dragging a new segment selection. */
  onSegmentChange: (startS: number, endS: number) => void;
}

const WAVEFORM_HEIGHT = 64;
const MAX_BARS = 100;
/** Minimum drag distance (px) before a gesture is treated as a drag vs. a tap. */
const DRAG_THRESHOLD = 6;

/** Placeholder peaks rendered while the real data is loading. */
const PLACEHOLDER_PEAKS = Array.from(
  { length: MAX_BARS },
  (_, i) => 0.2 + 0.15 * Math.abs(Math.sin(i * 0.28)),
);

export function WaveformAnnotator({
  waveformUrl,
  durationMs,
  positionMs,
  onSeek,
  selectionMode,
  segmentStartS,
  segmentEndS,
  onSegmentChange,
}: Props) {
  const { C } = useTheme();
  const [peaks, setPeaks] = useState<number[] | null>(null);
  const [containerW, setContainerW] = useState(0);

  // ── Refs so PanResponder handlers always see current prop values ──────────
  const selectionModeRef = useRef(selectionMode);
  selectionModeRef.current = selectionMode;

  const durationMsRef = useRef(durationMs);
  durationMsRef.current = durationMs;

  const containerWRef = useRef(containerW);
  containerWRef.current = containerW;

  const onSeekRef = useRef(onSeek);
  onSeekRef.current = onSeek;

  const onSegmentChangeRef = useRef(onSegmentChange);
  onSegmentChangeRef.current = onSegmentChange;

  // ── Fetch waveform JSON ───────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    fetch(waveformUrl)
      .then((r) => r.json())
      .then((d: { peaks: number[] }) => {
        if (!cancelled && Array.isArray(d?.peaks)) {
          setPeaks(d.peaks.slice(0, MAX_BARS));
        }
      })
      .catch(() => {
        // Fall back to placeholder displayed at full opacity
        if (!cancelled) setPeaks([]);
      });
    return () => {
      cancelled = true;
    };
  }, [waveformUrl]);

  // ── Coordinate → seconds conversion ─────────────────────────────────────
  const xToSeconds = useCallback(
    (x: number): number => {
      const w = containerWRef.current;
      const durS = durationMsRef.current / 1000;
      if (w <= 0 || durS <= 0) return 0;
      return Math.max(0, Math.min(durS, (x / w) * durS));
    },
    [],
  );

  // ── Gesture handling ─────────────────────────────────────────────────────
  const dragStartXRef = useRef<number | null>(null);

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: (evt) => {
        dragStartXRef.current = evt.nativeEvent.locationX;
      },
      onPanResponderRelease: (evt) => {
        const releaseX = evt.nativeEvent.locationX;
        const startX = dragStartXRef.current ?? releaseX;
        const moved = Math.abs(releaseX - startX);
        dragStartXRef.current = null;

        if (selectionModeRef.current && moved > DRAG_THRESHOLD) {
          // Drag in selection mode → create segment
          const s = xToSeconds(Math.min(startX, releaseX));
          const e = xToSeconds(Math.max(startX, releaseX));
          if (e > s) onSegmentChangeRef.current(s, e);
        } else {
          // Tap (any mode) → seek
          onSeekRef.current(xToSeconds(releaseX) * 1000);
        }
      },
    }),
  ).current;

  // ── Derived display values ───────────────────────────────────────────────
  const durationS = durationMs / 1000;
  const cursorPct = durationS > 0 ? (positionMs / 1000) / durationS : 0;

  const segStartPct =
    segmentStartS != null && durationS > 0 ? segmentStartS / durationS : null;
  const segEndPct =
    segmentEndS != null && durationS > 0 ? segmentEndS / durationS : null;

  const displayPeaks = peaks ?? PLACEHOLDER_PEAKS;
  const isLoading = peaks === null;

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <View
      style={[styles.container, { backgroundColor: C.surface }]}
      onLayout={(e) => setContainerW(e.nativeEvent.layout.width)}
      {...panResponder.panHandlers}
    >
      {/* Bar chart */}
      <View style={styles.barsRow}>
        {displayPeaks.map((peak, i) => {
          const barPct = i / displayPeaks.length;
          const inSegment =
            segStartPct != null &&
            segEndPct != null &&
            barPct >= segStartPct &&
            barPct <= segEndPct;
          const played = barPct <= cursorPct;

          const color = inSegment ? C.fuchsia : played ? C.primary : C.border;

          return (
            <View
              key={i}
              style={[
                styles.bar,
                {
                  height: Math.max(2, peak * (WAVEFORM_HEIGHT - 8)),
                  backgroundColor: color,
                  opacity: isLoading ? 0.35 : 1,
                },
              ]}
            />
          );
        })}
      </View>

      {/* Segment overlay */}
      {segStartPct != null && segEndPct != null && containerW > 0 && (
        <View
          pointerEvents="none"
          style={[
            styles.segmentOverlay,
            {
              left: segStartPct * containerW,
              width: Math.max(2, (segEndPct - segStartPct) * containerW),
              backgroundColor: C.fuchsia + '28',
              borderColor: C.fuchsia + '80',
            },
          ]}
        />
      )}

      {/* Playback cursor */}
      {containerW > 0 && (
        <View
          pointerEvents="none"
          style={[
            styles.cursor,
            {
              left: Math.max(0, cursorPct * containerW - 1),
              backgroundColor: C.primary,
            },
          ]}
        />
      )}

      {/* Loading spinner */}
      {isLoading && (
        <View pointerEvents="none" style={[StyleSheet.absoluteFill, styles.loadingOverlay]}>
          <ActivityIndicator size="small" color={C.textMuted} />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    height: WAVEFORM_HEIGHT,
    borderRadius: 6,
    overflow: 'hidden',
    position: 'relative',
  },
  barsRow: {
    position: 'absolute',
    left: 2,
    right: 2,
    bottom: 0,
    top: 0,
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 1,
  },
  bar: {
    flex: 1,
    borderRadius: 1,
  },
  segmentOverlay: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    borderWidth: 1,
    borderRadius: 3,
  },
  cursor: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    width: 2,
    borderRadius: 1,
  },
  loadingOverlay: {
    alignItems: 'center',
    justifyContent: 'center',
  },
});
