/**
 * Extraction status + results screen.
 *
 * Polls every 5 s until completed/failed, then shows audio stems.
 * Pressing a stem navigates to the feedback screen.
 */

import { router, useLocalSearchParams } from 'expo-router';
import React from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { ExtractionResult } from '../../src/api/client';
import { ErrorView } from '../../src/components/ErrorView';
import { StatusBadge } from '../../src/components/StatusBadge';
import { useExtractionPoll } from '../../src/hooks/useExtraction';

export default function ExtractionScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data, error } = useExtractionPoll(id ?? null);

  if (error) return <ErrorView message={error} />;

  if (!data) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#6366F1" />
        <Text style={styles.hint}>Loading…</Text>
      </View>
    );
  }

  const isTerminal = data.status === 'completed' || data.status === 'failed';

  return (
    <ScrollView contentContainerStyle={styles.scroll}>
      <View style={styles.header}>
        <StatusBadge status={data.status} />
        {data.cost_credits != null && (
          <Text style={styles.meta}>{data.cost_credits} credits used</Text>
        )}
        {data.processing_time_seconds != null && (
          <Text style={styles.meta}>{data.processing_time_seconds}s</Text>
        )}
      </View>

      {!isTerminal && (
        <View style={styles.center}>
          <ActivityIndicator color="#6366F1" />
          <Text style={styles.hint}>Separating sources…</Text>
        </View>
      )}

      {data.status === 'failed' && (
        <ErrorView message="Extraction failed. Please try again." />
      )}

      {data.status === 'completed' && data.results?.sources.map((source) => (
        <StemCard
          key={source.label}
          source={source}
          extractionId={data.extraction_id}
        />
      ))}

      {data.status === 'awaiting_confirmation' && data.ambiguous_labels && (
        <View style={styles.warning}>
          <Text style={styles.warningTitle}>Ambiguous labels detected</Text>
          {data.ambiguous_labels.map((a) => (
            <Text key={a.label} style={styles.warningItem}>
              "{a.label}" — {a.suggestion}
            </Text>
          ))}
          <Text style={styles.warningHint}>{data.message}</Text>
        </View>
      )}
    </ScrollView>
  );
}

function StemCard({
  source,
  extractionId,
}: {
  source: ExtractionResult;
  extractionId: string;
}) {
  return (
    <View style={styles.card}>
      <Text style={styles.stemLabel}>{source.label}</Text>
      <Text style={styles.stemMeta}>
        {source.model_used} · {source.duration_seconds}s · {source.sample_rate / 1000}kHz
      </Text>
      <Pressable
        style={styles.feedbackButton}
        onPress={() =>
          router.push({
            pathname: '/extraction/feedback',
            params: { extractionId, label: source.label },
          })
        }
      >
        <Text style={styles.feedbackButtonText}>Give Feedback</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 20, gap: 16 },
  center: { alignItems: 'center', justifyContent: 'center', padding: 32, gap: 8 },
  hint: { color: '#64748B', fontSize: 14 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 12, flexWrap: 'wrap' },
  meta: { fontSize: 13, color: '#94A3B8' },
  card: {
    backgroundColor: '#F8FAFC',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    gap: 6,
  },
  stemLabel: { fontSize: 16, fontWeight: '600', color: '#1E293B' },
  stemMeta: { fontSize: 13, color: '#94A3B8' },
  feedbackButton: {
    marginTop: 8,
    alignSelf: 'flex-start',
    backgroundColor: '#EEF2FF',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
  },
  feedbackButtonText: { color: '#4338CA', fontWeight: '600', fontSize: 13 },
  warning: {
    backgroundColor: '#FFFBEB',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#FCD34D',
    gap: 6,
  },
  warningTitle: { fontWeight: '600', color: '#92400E' },
  warningItem: { fontSize: 13, color: '#78350F' },
  warningHint: { fontSize: 12, color: '#B45309', marginTop: 4 },
});
