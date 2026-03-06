/**
 * Audio player card for a single extracted stem.
 *
 * Shows label, model, play/pause button, scrub bar, and a feedback button.
 */

import { router } from 'expo-router';
import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { ExtractionResult } from '../api/client';
import { useAudioPlayer } from '../hooks/useAudioPlayer';

interface Props {
  source: ExtractionResult;
  extractionId: string;
}

function formatMs(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, '0')}`;
}

export function StemPlayer({ source, extractionId }: Props) {
  const { isPlaying, isLoading, positionMs, durationMs, error, toggle, seek } =
    useAudioPlayer(source.audio_url);

  const progress = durationMs > 0 ? positionMs / durationMs : 0;

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <View style={styles.info}>
          <Text style={styles.label}>{source.label}</Text>
          <Text style={styles.meta}>
            {source.model_used} · {source.duration_seconds}s · {source.sample_rate / 1000}kHz
          </Text>
        </View>

        {isLoading ? (
          <ActivityIndicator color="#6366F1" />
        ) : (
          <Pressable
            style={styles.playButton}
            onPress={toggle}
            accessibilityRole="button"
            accessibilityLabel={isPlaying ? 'Pause' : 'Play'}
          >
            <Text style={styles.playIcon}>{isPlaying ? '⏸' : '▶️'}</Text>
          </Pressable>
        )}
      </View>

      {/* Scrub bar */}
      {!isLoading && durationMs > 0 && (
        <View style={styles.scrubRow}>
          <Text style={styles.timeText}>{formatMs(positionMs)}</Text>
          <Pressable
            style={styles.scrubBg}
            onPress={(e) => {
              const pct = e.nativeEvent.locationX / e.nativeEvent.target;
              seek(pct * durationMs);
            }}
          >
            <View style={[styles.scrubFill, { flex: progress }]} />
            <View style={{ flex: 1 - progress }} />
          </Pressable>
          <Text style={styles.timeText}>{formatMs(durationMs)}</Text>
        </View>
      )}

      {error && <Text style={styles.error}>{error}</Text>}

      <Pressable
        style={styles.feedbackButton}
        onPress={() =>
          router.push({
            pathname: '/extraction/feedback',
            params: { extractionId, label: source.label },
          })
        }
      >
        <Text style={styles.feedbackText}>Give Feedback</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#F8FAFC',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    gap: 10,
  },
  header: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  info: { flex: 1, gap: 3 },
  label: { fontSize: 16, fontWeight: '600', color: '#1E293B' },
  meta: { fontSize: 12, color: '#94A3B8' },
  playButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#EEF2FF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  playIcon: { fontSize: 18 },
  scrubRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  scrubBg: {
    flex: 1,
    height: 4,
    borderRadius: 2,
    backgroundColor: '#E2E8F0',
    flexDirection: 'row',
    overflow: 'hidden',
  },
  scrubFill: { backgroundColor: '#6366F1', borderRadius: 2 },
  timeText: { fontSize: 11, color: '#94A3B8', width: 36, textAlign: 'center' },
  error: { fontSize: 12, color: '#EF4444' },
  feedbackButton: {
    alignSelf: 'flex-start',
    backgroundColor: '#EEF2FF',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
  },
  feedbackText: { color: '#4338CA', fontWeight: '600', fontSize: 13 },
});
