/**
 * Progress indicator shown while an extraction is in `processing` or `queued` status.
 *
 * Processing state:
 *   - If `isHung` is true: shows a "taking longer than expected" message with a
 *     Dismiss button. Polling continues — the backend may eventually complete.
 *   - If `estimatedTimeSeconds` and `startedAt` are provided: shows an animated
 *     determinate progress bar derived from elapsed time, capped at 95% so it
 *     never falsely shows 100% before the backend confirms completion.
 *   - If either value is absent: shows an indeterminate animated bar with no
 *     percentage label (the backend did not give enough information to estimate).
 *
 * Queued state:
 *   - Shows `queuePosition` when available, otherwise "Queued…".
 */

import { router } from 'expo-router';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Animated,
  Easing,
  LayoutChangeEvent,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useTheme } from '../contexts/ThemeContext';
import { Theme } from '../theme';

interface Props {
  status: 'queued' | 'processing';
  estimatedTimeSeconds?: number | null;
  startedAt?: string | null;
  queuePosition?: number | null;
  /** True when processing has exceeded the hung-state threshold (10 min). */
  isHung?: boolean;
}

const PROGRESS_UPDATE_INTERVAL_MS = 1000;
const PROGRESS_CAP = 0.95;
// Shimmer element is 40% of the track width
const SHIMMER_WIDTH_RATIO = 0.4;

export function ExtractionProgressBar({
  status,
  estimatedTimeSeconds,
  startedAt,
  queuePosition,
  isHung = false,
}: Props) {
  const { C } = useTheme();
  const s = makeStyles(C);

  // ---------------------------------------------------------------------------
  // Hung-state dismissal
  // ---------------------------------------------------------------------------
  const handleDismiss = useCallback(() => {
    if (router.canGoBack()) {
      router.back();
    } else {
      router.replace('/(tabs)/history');
    }
  }, []);

  // ---------------------------------------------------------------------------
  // Determinate progress (processing + enough data to estimate)
  // ---------------------------------------------------------------------------
  const canEstimate =
    status === 'processing' &&
    typeof estimatedTimeSeconds === 'number' &&
    estimatedTimeSeconds > 0 &&
    typeof startedAt === 'string' &&
    startedAt.length > 0;

  const computeProgress = useCallback((): number => {
    if (!canEstimate) return 0;
    const elapsed = (Date.now() - new Date(startedAt!).getTime()) / 1000;
    return Math.min(elapsed / estimatedTimeSeconds!, PROGRESS_CAP);
  }, [canEstimate, estimatedTimeSeconds, startedAt]);

  const [progress, setProgress] = useState<number>(computeProgress);

  useEffect(() => {
    if (!canEstimate) return;
    setProgress(computeProgress()); // apply immediately when deps change
    const id = setInterval(() => setProgress(computeProgress()), PROGRESS_UPDATE_INTERVAL_MS);
    return () => clearInterval(id);
  }, [canEstimate, computeProgress]);

  // ---------------------------------------------------------------------------
  // Indeterminate shimmer animation (processing, no estimate available)
  // Measures track width so translateX can use absolute pixel values.
  // ---------------------------------------------------------------------------
  const [trackWidth, setTrackWidth] = useState(0);
  const shimmerAnim = useRef(new Animated.Value(0)).current;
  const shimmerLoopRef = useRef<Animated.CompositeAnimation | null>(null);

  const handleTrackLayout = useCallback((e: LayoutChangeEvent) => {
    setTrackWidth(e.nativeEvent.layout.width);
  }, []);

  useEffect(() => {
    if (status !== 'processing' || canEstimate || trackWidth === 0) {
      shimmerLoopRef.current?.stop();
      shimmerAnim.setValue(0);
      return;
    }

    const shimmerWidth = trackWidth * SHIMMER_WIDTH_RATIO;
    // Animate from just off the left edge to just off the right edge
    shimmerAnim.setValue(-shimmerWidth);
    const loop = Animated.loop(
      Animated.timing(shimmerAnim, {
        toValue: trackWidth,
        duration: 1400,
        easing: Easing.inOut(Easing.ease),
        useNativeDriver: true,
      }),
    );
    shimmerLoopRef.current = loop;
    loop.start();
    return () => loop.stop();
  }, [status, canEstimate, trackWidth, shimmerAnim]);

  // ---------------------------------------------------------------------------
  // Render: queued
  // ---------------------------------------------------------------------------
  if (status === 'queued') {
    const label =
      queuePosition != null ? `Position ${queuePosition} in queue` : 'Queued…';
    return (
      <View style={s.container}>
        <Text
          style={s.statusText}
          accessibilityRole="text"
          accessibilityLabel={label}
        >
          {label}
        </Text>
      </View>
    );
  }

  // ---------------------------------------------------------------------------
  // Render: hung state (processing exceeded threshold)
  // ---------------------------------------------------------------------------
  if (isHung) {
    return (
      <View
        style={s.hungContainer}
        accessibilityRole="alert"
        accessibilityLabel="This is taking longer than expected. The extraction may still be running — check back later."
      >
        <Text style={s.hungMessage}>
          This is taking longer than expected. The extraction may still be running — check back later.
        </Text>
        <Pressable
          onPress={handleDismiss}
          style={({ pressed }) => [s.dismissButton, pressed && s.dismissButtonPressed]}
          accessibilityRole="button"
          accessibilityLabel="Dismiss"
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <Text style={s.dismissButtonText}>Dismiss</Text>
        </Pressable>
      </View>
    );
  }

  // ---------------------------------------------------------------------------
  // Render: processing
  // ---------------------------------------------------------------------------
  const percentInt = Math.round(progress * 100);
  const accessibilityLabel = canEstimate
    ? `Extraction ${percentInt}% complete`
    : 'Extraction in progress';

  const shimmerWidth = trackWidth * SHIMMER_WIDTH_RATIO;

  return (
    <View style={s.container}>
      {canEstimate && (
        <View style={s.labelRow}>
          <Text style={s.statusText}>Separating sources…</Text>
          <Text style={s.percentText}>{percentInt}%</Text>
        </View>
      )}

      {/* Progress track */}
      <View
        style={s.track}
        onLayout={handleTrackLayout}
        accessibilityRole="progressbar"
        accessibilityLabel={accessibilityLabel}
        accessibilityValue={
          canEstimate
            ? { min: 0, max: 100, now: percentInt }
            : { min: 0, max: 100 }
        }
      >
        {canEstimate ? (
          // Determinate fill
          <View style={[s.fill, { width: `${percentInt}%` as `${number}%` }]} />
        ) : (
          // Indeterminate shimmer using absolute pixel translateX (cross-platform safe)
          <Animated.View
            style={[
              s.shimmer,
              {
                width: shimmerWidth > 0 ? shimmerWidth : '40%',
                transform: [{ translateX: shimmerAnim }],
              },
            ]}
          />
        )}
      </View>

      {!canEstimate && (
        <Text style={s.statusText}>Separating sources…</Text>
      )}
    </View>
  );
}

function makeStyles(C: Theme) {
  return StyleSheet.create({
    container: {
      gap: 8,
    },
    labelRow: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
    },
    statusText: {
      fontSize: 13,
      color: C.textMuted,
    },
    percentText: {
      fontSize: 13,
      fontWeight: '600',
      color: C.primary,
    },
    track: {
      height: 8,
      borderRadius: 4,
      backgroundColor: C.primaryDim,
      overflow: 'hidden',
    },
    fill: {
      height: '100%',
      borderRadius: 4,
      backgroundColor: C.fuchsia,
    },
    shimmer: {
      position: 'absolute',
      top: 0,
      height: '100%',
      borderRadius: 4,
      backgroundColor: C.fuchsia,
    },
    hungContainer: {
      gap: 12,
      padding: 16,
      borderRadius: 10,
      backgroundColor: C.warningDim,
      borderWidth: 1,
      borderColor: C.warning,
    },
    hungMessage: {
      fontSize: 14,
      color: C.textSecondary,
      lineHeight: 20,
    },
    dismissButton: {
      alignSelf: 'flex-start',
      paddingVertical: 8,
      paddingHorizontal: 16,
      borderRadius: 8,
      backgroundColor: C.surface,
      borderWidth: 1,
      borderColor: C.border,
    },
    dismissButtonPressed: {
      opacity: 0.6,
    },
    dismissButtonText: {
      fontSize: 14,
      fontWeight: '500',
      color: C.textPrimary,
    },
  });
}
