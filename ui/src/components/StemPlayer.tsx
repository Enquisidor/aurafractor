/**
 * Audio player card for a single extracted stem.
 *
 * Shows label, model, play/pause button, scrub bar, and a feedback button.
 */

import { router } from 'expo-router';
import React, { useRef } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { ExtractionResult } from '../api/client';
import { useTheme } from '../contexts/ThemeContext';
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
  const { C } = useTheme();
  const { isPlaying, isLoading, positionMs, durationMs, error, toggle, seek } =
    useAudioPlayer(source.audio_url);

  const progress = durationMs > 0 ? positionMs / durationMs : 0;
  const barWidth = useRef(0);

  return (
    <View style={[styles.card, { backgroundColor: C.surface, borderColor: C.border }]}>
      <View style={styles.header}>
        <View style={styles.info}>
          <Text style={[styles.label, { color: C.textPrimary }]}>{source.label}</Text>
          <Text style={[styles.meta, { color: C.textMuted }]}>
            {source.model_used} · {source.duration_seconds}s · {source.sample_rate / 1000}kHz
          </Text>
        </View>

        {isLoading ? (
          <ActivityIndicator color={C.primary} />
        ) : (
          <Pressable
            style={[styles.playButton, { backgroundColor: C.primaryDim }]}
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
          <Text style={[styles.timeText, { color: C.textMuted }]}>{formatMs(positionMs)}</Text>
          <Pressable
            style={[styles.scrubBg, { backgroundColor: C.border }]}
            onLayout={(e) => { barWidth.current = e.nativeEvent.layout.width; }}
            onPress={(e) => {
              const pct = barWidth.current > 0 ? e.nativeEvent.locationX / barWidth.current : 0;
              seek(pct * durationMs);
            }}
          >
            <View style={[styles.scrubFill, { backgroundColor: C.fuchsia, flex: progress }]} />
            <View style={{ flex: 1 - progress }} />
          </Pressable>
          <Text style={[styles.timeText, { color: C.textMuted }]}>{formatMs(durationMs)}</Text>
        </View>
      )}

      {error && <Text style={[styles.error, { color: C.error }]}>{error}</Text>}

      <Pressable
        style={[styles.feedbackButton, { backgroundColor: C.primaryDim }]}
        onPress={() =>
          router.push({
            pathname: '/extraction/feedback',
            params: { extractionId, label: source.label },
          })
        }
      >
        <Text style={[styles.feedbackText, { color: C.primary }]}>Give Feedback</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    gap: 10,
  },
  header: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  info: { flex: 1, gap: 3 },
  label: { fontSize: 16, fontWeight: '600' },
  meta: { fontSize: 12 },
  playButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  playIcon: { fontSize: 18 },
  scrubRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  scrubBg: {
    flex: 1,
    height: 4,
    borderRadius: 2,
    flexDirection: 'row',
    overflow: 'hidden',
  },
  scrubFill: { borderRadius: 2 },
  timeText: { fontSize: 11, width: 36, textAlign: 'center' },
  error: { fontSize: 12 },
  feedbackButton: {
    alignSelf: 'flex-start',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
  },
  feedbackText: { fontWeight: '600', fontSize: 13 },
});
