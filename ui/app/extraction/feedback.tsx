/**
 * Feedback screen.
 *
 * Reached from ExtractionScreen with params: { extractionId, label }.
 * Submitting good/bad feedback optionally triggers a re-extraction
 * with a refined label.
 */

import { router, useLocalSearchParams } from 'expo-router';
import React, { useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { extraction as extractionApi } from '../../src/api/client';

type FeedbackType = 'good' | 'too_much' | 'too_little' | 'artifacts';

const FEEDBACK_OPTIONS: Array<{ type: FeedbackType; label: string; emoji: string }> = [
  { type: 'good', label: 'Sounds good', emoji: '✅' },
  { type: 'too_much', label: 'Too much bleed', emoji: '🔊' },
  { type: 'too_little', label: 'Too little signal', emoji: '🔇' },
  { type: 'artifacts', label: 'Artifacts / glitches', emoji: '⚠️' },
];

export default function FeedbackScreen() {
  const { extractionId, label } = useLocalSearchParams<{
    extractionId: string;
    label: string;
  }>();

  const [feedbackType, setFeedbackType] = useState<FeedbackType | null>(null);
  const [refinedLabel, setRefinedLabel] = useState('');
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!feedbackType || !extractionId || !label) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await extractionApi.feedback(extractionId, {
        feedback_type: feedbackType,
        segment_label: label,
        refined_label: refinedLabel.trim() || undefined,
        comment: comment.trim() || undefined,
      });
      if (res.reextraction_queued && res.new_extraction_id) {
        router.replace(`/extraction/${res.new_extraction_id}`);
      } else {
        router.back();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.scroll}>
      <Text style={styles.heading}>Feedback for "{label}"</Text>

      <Text style={styles.sectionTitle}>How did it sound?</Text>
      <View style={styles.options}>
        {FEEDBACK_OPTIONS.map((opt) => (
          <Pressable
            key={opt.type}
            style={[styles.option, feedbackType === opt.type && styles.optionSelected]}
            onPress={() => setFeedbackType(opt.type)}
            accessibilityRole="radio"
            accessibilityState={{ checked: feedbackType === opt.type }}
          >
            <Text style={styles.optionEmoji}>{opt.emoji}</Text>
            <Text style={[styles.optionLabel, feedbackType === opt.type && styles.optionLabelSelected]}>
              {opt.label}
            </Text>
          </Pressable>
        ))}
      </View>

      {feedbackType && feedbackType !== 'good' && (
        <>
          <Text style={styles.sectionTitle}>Refine label (triggers re-extraction)</Text>
          <TextInput
            style={styles.input}
            placeholder={`e.g. "dry ${label}"`}
            value={refinedLabel}
            onChangeText={setRefinedLabel}
          />
          <Text style={styles.sectionTitle}>Comment (optional)</Text>
          <TextInput
            style={[styles.input, styles.multiline]}
            placeholder="Describe the issue…"
            value={comment}
            onChangeText={setComment}
            multiline
            numberOfLines={3}
          />
        </>
      )}

      {error && <Text style={styles.error}>{error}</Text>}

      <Pressable
        style={[styles.button, (!feedbackType || submitting) && styles.buttonDisabled]}
        onPress={submit}
        disabled={!feedbackType || submitting}
      >
        {submitting ? (
          <ActivityIndicator color="#FFF" />
        ) : (
          <Text style={styles.buttonText}>Submit Feedback</Text>
        )}
      </Pressable>

      <Pressable style={styles.cancelButton} onPress={() => router.back()}>
        <Text style={styles.cancelText}>Cancel</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 20, gap: 12 },
  heading: { fontSize: 20, fontWeight: '700', color: '#1E293B' },
  sectionTitle: { fontSize: 13, fontWeight: '600', color: '#475569', marginTop: 8 },
  options: { gap: 8 },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    padding: 14,
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: '#E2E8F0',
    backgroundColor: '#F8FAFC',
  },
  optionSelected: { borderColor: '#6366F1', backgroundColor: '#EEF2FF' },
  optionEmoji: { fontSize: 20 },
  optionLabel: { fontSize: 15, color: '#334155' },
  optionLabelSelected: { color: '#4338CA', fontWeight: '600' },
  input: {
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 10,
    padding: 12,
    fontSize: 15,
    backgroundColor: '#F8FAFC',
  },
  multiline: { minHeight: 80, textAlignVertical: 'top' },
  error: { color: '#EF4444', fontSize: 13 },
  button: {
    backgroundColor: '#6366F1',
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: '#FFF', fontSize: 16, fontWeight: '600' },
  cancelButton: { alignItems: 'center', paddingVertical: 12 },
  cancelText: { color: '#64748B', fontSize: 14 },
});
