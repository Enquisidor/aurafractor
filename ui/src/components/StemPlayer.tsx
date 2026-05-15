/**
 * Audio player card for a single extracted stem.
 *
 * Shows label, model, play/pause button, waveform (with playback cursor and
 * optional segment selection), and a feedback button.
 *
 * Segment annotation:
 *   - "Select region" button enters selection mode.
 *   - User drags on the waveform to define start/end seconds.
 *   - Selected region is highlighted fuchsia on the waveform.
 *   - Time range is shown below the waveform; "Clear" removes it.
 *   - If a region is selected when "Give Feedback" is tapped, the segment
 *     times are passed as route params to the feedback screen.
 */

import { router } from 'expo-router';
import React, { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { ExtractionResult } from '../api/client';
import { useTheme } from '../contexts/ThemeContext';
import { useAudioPlayer } from '../hooks/useAudioPlayer';
import { WaveformAnnotator } from './WaveformAnnotator';

interface Props {
  source: ExtractionResult;
  extractionId: string;
}

function formatSec(s: number): string {
  const mins = Math.floor(s / 60);
  const secs = Math.floor(s % 60);
  return `${mins}:${String(secs).padStart(2, '0')}`;
}

export function StemPlayer({ source, extractionId }: Props) {
  const { C } = useTheme();
  const { isPlaying, isLoading, positionMs, durationMs, error, toggle, seek } =
    useAudioPlayer(source.audio_url);

  const [selectionMode, setSelectionMode] = useState(false);
  const [segmentStartS, setSegmentStartS] = useState<number | null>(null);
  const [segmentEndS, setSegmentEndS] = useState<number | null>(null);

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

      {/* Waveform with playback cursor + segment annotation */}
      {!isLoading && durationMs > 0 && (
        <>
          <WaveformAnnotator
            waveformUrl={source.waveform_url}
            durationMs={durationMs}
            positionMs={positionMs}
            onSeek={seek}
            selectionMode={selectionMode}
            segmentStartS={segmentStartS}
            segmentEndS={segmentEndS}
            onSegmentChange={(s, e) => {
              setSegmentStartS(s);
              setSegmentEndS(e);
            }}
          />

          {/* Selection controls row */}
          <View style={styles.selectionRow}>
            {segmentStartS != null && segmentEndS != null ? (
              <>
                <Text style={[styles.segmentLabel, { color: C.fuchsia }]}>
                  {formatSec(segmentStartS)} – {formatSec(segmentEndS)}
                </Text>
                <Pressable
                  onPress={() => {
                    setSegmentStartS(null);
                    setSegmentEndS(null);
                    setSelectionMode(false);
                  }}
                  hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                >
                  <Text style={[styles.selectionAction, { color: C.textMuted }]}>Clear</Text>
                </Pressable>
              </>
            ) : selectionMode ? (
              <>
                <Text style={[styles.selectionHint, { color: C.textMuted }]}>
                  Drag to select a region
                </Text>
                <Pressable
                  onPress={() => setSelectionMode(false)}
                  hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                >
                  <Text style={[styles.selectionAction, { color: C.textMuted }]}>Cancel</Text>
                </Pressable>
              </>
            ) : (
              <Pressable
                onPress={() => setSelectionMode(true)}
                hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
              >
                <Text style={[styles.selectionAction, { color: C.primary }]}>Select region</Text>
              </Pressable>
            )}
          </View>
        </>
      )}

      {error && <Text style={[styles.error, { color: C.error }]}>{error}</Text>}

      <Pressable
        style={[styles.feedbackButton, { backgroundColor: C.primaryDim }]}
        onPress={() =>
          router.push({
            pathname: '/extraction/feedback',
            params: {
              extractionId,
              label: source.label,
              ...(segmentStartS != null && segmentEndS != null
                ? {
                    segmentStart: String(segmentStartS),
                    segmentEnd: String(segmentEndS),
                  }
                : {}),
            },
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
  selectionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    minHeight: 20,
  },
  segmentLabel: { fontSize: 12, fontWeight: '600' },
  selectionHint: { fontSize: 12 },
  selectionAction: { fontSize: 12, fontWeight: '600' },
  error: { fontSize: 12 },
  feedbackButton: {
    alignSelf: 'flex-start',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
  },
  feedbackText: { fontWeight: '600', fontSize: 13 },
});
