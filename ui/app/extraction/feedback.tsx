/**
 * Feedback screen.
 *
 * Reached from ExtractionScreen with params: { extractionId, label }.
 * Submitting good/bad feedback optionally triggers a re-extraction
 * with a refined label.
 */

import { router, useLocalSearchParams } from 'expo-router';
import React, { useMemo, useState } from 'react';
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
import { useTheme } from '../../src/contexts/ThemeContext';
import { Theme } from '../../src/theme';

type FeedbackType = 'good' | 'too_much' | 'too_little' | 'artifacts';

const FEEDBACK_OPTIONS: Array<{ type: FeedbackType; label: string; emoji: string }> = [
  { type: 'good', label: 'Sounds good', emoji: '✅' },
  { type: 'too_much', label: 'Too much bleed', emoji: '🔊' },
  { type: 'too_little', label: 'Too little signal', emoji: '🔇' },
  { type: 'artifacts', label: 'Artifacts / glitches', emoji: '⚠️' },
];

export default function FeedbackScreen() {
  const { C } = useTheme();
  const s = useMemo(() => makeStyles(C), [C]);
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
    <ScrollView style={{ backgroundColor: C.bg }} contentContainerStyle={s.scroll}>
      <Text style={s.heading}>Feedback for "{label}"</Text>

      <Text style={s.sectionTitle}>How did it sound?</Text>
      <View style={s.options}>
        {FEEDBACK_OPTIONS.map((opt) => (
          <Pressable
            key={opt.type}
            style={[s.option, feedbackType === opt.type && s.optionSelected]}
            onPress={() => setFeedbackType(opt.type)}
            accessibilityRole="radio"
            accessibilityState={{ checked: feedbackType === opt.type }}
          >
            <Text style={s.optionEmoji}>{opt.emoji}</Text>
            <Text style={[s.optionLabel, feedbackType === opt.type && s.optionLabelSelected]}>
              {opt.label}
            </Text>
          </Pressable>
        ))}
      </View>

      {feedbackType && feedbackType !== 'good' && (
        <>
          <Text style={s.sectionTitle}>Refine label (triggers re-extraction)</Text>
          <TextInput
            style={s.input}
            placeholder={`e.g. "dry ${label}"`}
            placeholderTextColor={C.textMuted}
            value={refinedLabel}
            onChangeText={setRefinedLabel}
          />
          <Text style={s.sectionTitle}>Comment (optional)</Text>
          <TextInput
            style={[s.input, s.multiline]}
            placeholder="Describe the issue…"
            placeholderTextColor={C.textMuted}
            value={comment}
            onChangeText={setComment}
            multiline
            numberOfLines={3}
          />
        </>
      )}

      {error && <Text style={s.error}>{error}</Text>}

      <Pressable
        style={[s.button, (!feedbackType || submitting) && s.buttonDisabled]}
        onPress={submit}
        disabled={!feedbackType || submitting}
      >
        {submitting ? (
          <ActivityIndicator color="#FFF" />
        ) : (
          <Text style={s.buttonText}>Submit Feedback</Text>
        )}
      </Pressable>

      <Pressable style={s.cancelButton} onPress={() => router.back()}>
        <Text style={s.cancelText}>Cancel</Text>
      </Pressable>
    </ScrollView>
  );
}

function makeStyles(C: Theme) {
  return StyleSheet.create({
    scroll:              { padding: 20, gap: 12 },
    heading:             { fontSize: 20, fontWeight: '700', color: C.textPrimary },
    sectionTitle:        { fontSize: 13, fontWeight: '600', color: C.textSecondary, marginTop: 8 },
    options:             { gap: 8 },
    option: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 10,
      padding: 14,
      borderRadius: 12,
      borderWidth: 1.5,
      borderColor: C.border,
      backgroundColor: C.surface,
    },
    optionSelected:      { borderColor: C.primary, backgroundColor: C.primaryDim },
    optionEmoji:         { fontSize: 20 },
    optionLabel:         { fontSize: 15, color: C.textPrimary },
    optionLabelSelected: { color: C.primary, fontWeight: '600' },
    input: {
      borderWidth: 1,
      borderColor: C.border,
      borderRadius: 10,
      padding: 12,
      fontSize: 15,
      color: C.textPrimary,
      backgroundColor: C.surface,
    },
    multiline:     { minHeight: 80, textAlignVertical: 'top' },
    error:         { color: C.error, fontSize: 13 },
    button: {
      backgroundColor: C.fuchsia,
      paddingVertical: 14,
      borderRadius: 12,
      alignItems: 'center',
      marginTop: 8,
    },
    buttonDisabled: { opacity: 0.5 },
    buttonText:     { color: '#FFF', fontSize: 16, fontWeight: '600' },
    cancelButton:   { alignItems: 'center', paddingVertical: 12 },
    cancelText:     { color: C.textMuted, fontSize: 14 },
  });
}
