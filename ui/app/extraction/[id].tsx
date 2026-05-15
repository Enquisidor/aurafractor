/**
 * Extraction status + results screen.
 *
 * Polls every 5 s until completed/failed, then shows playable audio stems.
 *
 * Cache-first strategy: if the Redux extractions store already holds a
 * terminal result (completed | failed) for this extraction_id, it is used
 * immediately and polling is skipped.
 *
 * Store sync: every successful poll response is dispatched as upsertExtraction
 * so the cache stays current across navigation.
 *
 * Re-run guard: any action that would re-run an extraction (consuming credits)
 * requires explicit user confirmation via Alert.alert before proceeding.
 *
 * Cancel: when status is queued or processing, a Cancel button is shown.
 *   - When isHung is true, the button appears below the hung-state card
 *     (which already contains the Dismiss button), rendered as a standalone
 *     destructive button — same position as the non-hung case.
 *   - When not yet hung, it appears as a standalone button below the
 *     progress bar.
 *   An Alert.alert confirmation is required before the cancel request is
 *   sent. On success the screen navigates back. On failure (e.g. 409 —
 *   extraction already in a terminal state) an error Alert is shown.
 *
 * Includes an explicit back button that works cross-platform:
 * - If router.canGoBack() is true (native stack or web navigation that has
 *   history), calls router.back().
 * - If router.canGoBack() is false (direct URL navigation on web with an
 *   empty history stack), navigates to /(tabs)/history as a safe fallback.
 * The button is always rendered — it does not rely on Expo Router's
 * automatic header back arrow, which is absent on web when the stack is empty.
 *
 * Progress display:
 * - `queued`: shows queue position when available, otherwise "Queued…"
 * - `processing`: shows an animated progress bar + percentage derived from
 *   elapsed time against `estimated_time_seconds`. Capped at 95% so it never
 *   falsely reaches 100% before the backend confirms completion. When
 *   `estimated_time_seconds` is absent, shows an indeterminate animated bar
 *   with no percentage label.
 * - `processing` (hung): when processing exceeds 10 minutes, replaces the
 *   progress bar with a "taking longer than expected" message and a Dismiss
 *   button. Polling continues — the backend may eventually complete.
 * - `completed` / `failed`: progress display is hidden; results or error takes over.
 */

import { router, useLocalSearchParams } from 'expo-router';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import { extraction as extractionApi, ExtractionResponse } from '../../src/api/client';
import { ErrorView } from '../../src/components/ErrorView';
import { ExtractionProgressBar } from '../../src/components/ExtractionProgressBar';
import { StatusBadge } from '../../src/components/StatusBadge';
import { StemPlayer } from '../../src/components/StemPlayer';
import { useTheme } from '../../src/contexts/ThemeContext';
import { useExtractionPoll } from '../../src/hooks/useExtraction';
import { selectExtraction, upsertExtraction } from '../../src/store/extractionsSlice';
import { AppDispatch } from '../../src/store/store';
import { Theme } from '../../src/theme';

const TERMINAL_STATUSES = new Set<ExtractionResponse['status']>(['completed', 'failed']);

export default function ExtractionScreen() {
  const { C } = useTheme();
  const s = useMemo(() => makeStyles(C), [C]);
  const dispatch = useDispatch<AppDispatch>();
  const { id } = useLocalSearchParams<{ id: string }>();

  // Check the cache for a terminal result before starting a poll.
  const cached = useSelector(selectExtraction(id ?? ''));
  const cachedIsTerminal = cached != null && TERMINAL_STATUSES.has(cached.status);

  // Only poll when we do not already have a terminal cached result.
  const { data: polledData, error, isHung } = useExtractionPoll(
    id != null && !cachedIsTerminal ? id : null,
  );

  // Sync every successful poll result into the Redux store.
  useEffect(() => {
    if (polledData) {
      dispatch(upsertExtraction(polledData));
    }
  }, [polledData, dispatch]);

  // Merge: prefer live poll data (fresher); fall back to cached store value.
  const data: ExtractionResponse | null = polledData ?? cached ?? null;

  const [rerunning, setRerunning] = useState(false);
  const [rerunError, setRerunError] = useState<string | null>(null);

  const [cancelling, setCancelling] = useState(false);

  const handleBack = useCallback(() => {
    if (router.canGoBack()) {
      router.back();
    } else {
      router.replace('/(tabs)/history');
    }
  }, []);

  /**
   * Initiate a re-run of a failed extraction.
   * Requires the user to confirm via Alert because re-runs consume credits.
   *
   * The confirmation message includes the credit cost from the cached
   * ExtractionResponse.cost_credits field if known, otherwise uses a
   * generic "will use credits" message.
   *
   * On confirmation, calls extraction.extract with the track_id. The
   * result is upserted into the store and the screen navigates to the
   * new extraction.
   */
  const handleRerun = useCallback(() => {
    if (!data) return;

    const creditCost = data.cost_credits;
    const message =
      creditCost != null
        ? `This will use ${creditCost} credit${creditCost !== 1 ? 's' : ''}. Continue?`
        : 'This will use credits. Continue?';

    Alert.alert(
      'Re-run extraction?',
      message,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Re-run',
          style: 'default',
          onPress: async () => {
            if (!data.track_id) return;
            setRerunning(true);
            setRerunError(null);
            try {
              // Re-run with no sources — the backend will use the track's
              // default source configuration. The user can refine labels
              // via the feedback flow on the new extraction.
              const res = await extractionApi.extract(data.track_id, []);
              dispatch(upsertExtraction(res));
              router.replace(`/extraction/${res.extraction_id}`);
            } catch (e) {
              setRerunError(e instanceof Error ? e.message : 'Re-run failed');
            } finally {
              setRerunning(false);
            }
          },
        },
      ],
    );
  }, [data, dispatch]);

  /**
   * Cancel a queued or processing extraction.
   * Requires explicit user confirmation because the action is irreversible
   * and credits are not refunded.
   *
   * On confirmation, calls extraction.cancel(extractionId). On success,
   * navigates back. On failure (e.g. 409 — extraction already terminal),
   * shows an error Alert so the user understands why the cancel did not work.
   */
  const handleCancel = useCallback(() => {
    if (!id) return;

    Alert.alert(
      'Cancel extraction?',
      'This will stop the extraction. Credits will not be refunded.',
      [
        { text: 'Keep running', style: 'cancel' },
        {
          text: 'Cancel extraction',
          style: 'destructive',
          onPress: async () => {
            setCancelling(true);
            try {
              await extractionApi.cancel(id);
              handleBack();
            } catch (e) {
              setCancelling(false);
              Alert.alert(
                'Could not cancel',
                e instanceof Error ? e.message : 'Cancel failed',
              );
            }
          },
        },
      ],
    );
  }, [id, handleBack]);

  if (error) return <ErrorView message={error} />;

  if (!data) {
    return (
      <View style={[s.center, { backgroundColor: C.bg, flex: 1 }]}>
        <ActivityIndicator size="large" color={C.primary} />
        <Text style={s.hint}>Loading…</Text>
      </View>
    );
  }

  const isTerminal = data.status === 'completed' || data.status === 'failed';
  const showProgress = data.status === 'queued' || data.status === 'processing';
  // Cancellable while the extraction is still in-flight (queued or processing,
  // which also covers the hung sub-state).
  const cancellable = data.status === 'queued' || data.status === 'processing';

  return (
    <ScrollView style={{ backgroundColor: C.bg }} contentContainerStyle={s.scroll}>
      <View style={s.topBar}>
        <Pressable
          onPress={handleBack}
          style={({ pressed }) => [s.backButton, pressed && s.backButtonPressed]}
          accessibilityRole="button"
          accessibilityLabel="Go back"
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <Text style={[s.backArrow, { color: C.primary }]}>{'←'}</Text>
          <Text style={[s.backLabel, { color: C.primary }]}>Back</Text>
        </Pressable>
      </View>

      <View style={s.header}>
        <StatusBadge status={data.status} />
        {data.cost_credits != null && (
          <Text style={s.meta}>{data.cost_credits} credits used</Text>
        )}
        {data.processing_time_seconds != null && (
          <Text style={s.meta}>{data.processing_time_seconds}s</Text>
        )}
      </View>

      {showProgress && (
        <ExtractionProgressBar
          status={data.status}
          estimatedTimeSeconds={data.estimated_time_seconds}
          startedAt={data.started_at}
          queuePosition={data.queue_position}
          isHung={isHung}
        />
      )}

      {/* Cancel button — shown for any in-flight extraction (queued or
          processing, including the hung sub-state). Placed directly below
          ExtractionProgressBar so it is adjacent to the hung-state card when
          isHung is true, and adjacent to the progress bar when not yet hung.
          The Dismiss button in the hung-state card (inside ExtractionProgressBar)
          navigates back; this button cancels the extraction on the backend. */}
      {cancellable && (
        <Pressable
          style={[s.cancelButton, cancelling && s.cancelButtonDisabled]}
          onPress={handleCancel}
          disabled={cancelling}
          accessibilityRole="button"
          accessibilityLabel="Cancel extraction"
        >
          {cancelling ? (
            <ActivityIndicator color={C.error} />
          ) : (
            <Text style={[s.cancelButtonText, { color: C.error }]}>Cancel extraction</Text>
          )}
        </Pressable>
      )}

      {!isTerminal && !showProgress && (
        <View style={s.center}>
          <ActivityIndicator color={C.primary} />
          <Text style={s.hint}>Processing…</Text>
        </View>
      )}

      {data.status === 'failed' && (
        <>
          <ErrorView message="Extraction failed. Please try again." />
          {rerunError && <Text style={s.rerunError}>{rerunError}</Text>}
          <Pressable
            style={[s.rerunButton, rerunning && s.rerunButtonDisabled]}
            onPress={handleRerun}
            disabled={rerunning}
            accessibilityRole="button"
            accessibilityLabel="Re-run extraction"
          >
            {rerunning ? (
              <ActivityIndicator color="#FFF" />
            ) : (
              <Text style={s.rerunButtonText}>Re-run Extraction</Text>
            )}
          </Pressable>
        </>
      )}

      {data.status === 'completed' &&
        data.results?.sources.map((source) => (
          <StemPlayer
            key={source.label}
            source={source}
            extractionId={data.extraction_id}
          />
        ))}

      {data.status === 'awaiting_confirmation' && data.ambiguous_labels && (
        <View style={s.warning}>
          <Text style={s.warningTitle}>Ambiguous labels detected</Text>
          {data.ambiguous_labels.map((a) => (
            <Text key={a.label} style={s.warningItem}>
              "{a.label}" — {a.suggestion}
            </Text>
          ))}
          <Text style={s.warningHint}>{data.message}</Text>
        </View>
      )}
    </ScrollView>
  );
}

function makeStyles(C: Theme) {
  return StyleSheet.create({
    scroll:       { padding: 20, gap: 16, maxWidth: 600, width: '100%', alignSelf: 'center' },
    center:       { alignItems: 'center', justifyContent: 'center', padding: 32, gap: 8 },
    hint:         { color: C.textMuted, fontSize: 14 },
    topBar: {
      flexDirection: 'row',
      alignItems: 'center',
      marginBottom: 4,
    },
    backButton: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 4,
      paddingVertical: 4,
      paddingHorizontal: 2,
      borderRadius: 6,
    },
    backButtonPressed: {
      opacity: 0.6,
    },
    backArrow: {
      fontSize: 18,
      fontWeight: '600',
      lineHeight: 22,
    },
    backLabel: {
      fontSize: 15,
      fontWeight: '500',
    },
    header:       { flexDirection: 'row', alignItems: 'center', gap: 12, flexWrap: 'wrap' },
    meta:         { fontSize: 13, color: C.textMuted },
    warning: {
      backgroundColor: C.warningDim,
      borderRadius: 12,
      padding: 16,
      borderWidth: 1,
      borderColor: C.warning,
      gap: 6,
    },
    warningTitle: { fontWeight: '600', color: C.warning },
    warningItem:  { fontSize: 13, color: C.textSecondary },
    warningHint:  { fontSize: 12, color: C.textMuted, marginTop: 4 },
    rerunButton: {
      backgroundColor: C.primary,
      paddingVertical: 13,
      borderRadius: 12,
      alignItems: 'center',
      marginTop: 8,
    },
    rerunButtonDisabled: { opacity: 0.5 },
    rerunButtonText: { color: '#FFF', fontSize: 15, fontWeight: '600' },
    rerunError: { color: C.error, fontSize: 13, textAlign: 'center' },
    cancelButton: {
      paddingVertical: 12,
      borderRadius: 12,
      alignItems: 'center',
      borderWidth: 1,
      borderColor: C.error,
    },
    cancelButtonDisabled: { opacity: 0.5 },
    cancelButtonText: { fontSize: 15, fontWeight: '600' },
  });
}
