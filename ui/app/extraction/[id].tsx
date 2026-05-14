/**
 * Extraction status + results screen.
 *
 * Polls every 5 s until completed/failed, then shows playable audio stems.
 *
 * Includes an explicit back button that works cross-platform:
 * - If router.canGoBack() is true (native stack or web navigation that has
 *   history), calls router.back().
 * - If router.canGoBack() is false (direct URL navigation on web with an
 *   empty history stack), navigates to /(tabs)/history as a safe fallback.
 * The button is always rendered — it does not rely on Expo Router's
 * automatic header back arrow, which is absent on web when the stack is empty.
 */

import { router, useLocalSearchParams } from 'expo-router';
import React, { useCallback, useMemo } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { ErrorView } from '../../src/components/ErrorView';
import { StatusBadge } from '../../src/components/StatusBadge';
import { StemPlayer } from '../../src/components/StemPlayer';
import { useTheme } from '../../src/contexts/ThemeContext';
import { useExtractionPoll } from '../../src/hooks/useExtraction';
import { Theme } from '../../src/theme';

export default function ExtractionScreen() {
  const { C } = useTheme();
  const s = useMemo(() => makeStyles(C), [C]);
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data, error } = useExtractionPoll(id ?? null);

  const handleBack = useCallback(() => {
    if (router.canGoBack()) {
      router.back();
    } else {
      router.replace('/(tabs)/history');
    }
  }, []);

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

      {!isTerminal && (
        <View style={s.center}>
          <ActivityIndicator color={C.primary} />
          <Text style={s.hint}>Separating sources…</Text>
        </View>
      )}

      {data.status === 'failed' && (
        <ErrorView message="Extraction failed. Please try again." />
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
  });
}
