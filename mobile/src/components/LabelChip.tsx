/**
 * Selectable label chip for instrument selection.
 */

import React from 'react';
import { Pressable, StyleSheet, Text } from 'react-native';
import { LabelSuggestion } from '../api/client';

interface Props {
  suggestion: LabelSuggestion;
  selected: boolean;
  onPress: () => void;
}

export function LabelChip({ suggestion, selected, onPress }: Props) {
  return (
    <Pressable
      style={[styles.chip, selected && styles.selected]}
      onPress={onPress}
      accessibilityRole="checkbox"
      accessibilityState={{ checked: selected }}
      accessibilityLabel={`${suggestion.label}, confidence ${Math.round(suggestion.confidence * 100)}%`}
    >
      <Text style={[styles.label, selected && styles.labelSelected]}>
        {suggestion.label}
      </Text>
      <Text style={styles.confidence}>
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
    borderColor: '#CBD5E1',
    backgroundColor: '#F8FAFC',
    margin: 4,
  },
  selected: {
    borderColor: '#6366F1',
    backgroundColor: '#EEF2FF',
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    color: '#334155',
  },
  labelSelected: {
    color: '#4338CA',
  },
  confidence: {
    fontSize: 11,
    color: '#94A3B8',
  },
});
