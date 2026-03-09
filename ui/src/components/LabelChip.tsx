/**
 * Selectable label chip for instrument selection.
 */

import React from 'react';
import { Pressable, StyleSheet, Text } from 'react-native';
import { LabelSuggestion } from '../api/client';
import { useTheme } from '../contexts/ThemeContext';

interface Props {
  suggestion: LabelSuggestion;
  selected: boolean;
  onPress: () => void;
}

export function LabelChip({ suggestion, selected, onPress }: Props) {
  const { C } = useTheme();
  return (
    <Pressable
      style={[
        styles.chip,
        { borderColor: selected ? C.primary : C.border, backgroundColor: selected ? C.primaryDim : C.surface },
      ]}
      onPress={onPress}
      accessibilityRole="checkbox"
      accessibilityState={{ checked: selected }}
      accessibilityLabel={`${suggestion.label}, confidence ${Math.round(suggestion.confidence * 100)}%`}
    >
      <Text style={[styles.label, { color: selected ? C.primary : C.textPrimary }]}>
        {suggestion.label}
      </Text>
      <Text style={[styles.confidence, { color: C.textMuted }]}>
        {Math.round(suggestion.confidence * 100)}%
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1.5,
    margin: 4,
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
  },
  confidence: {
    fontSize: 11,
  },
});
