/**
 * Status badge for extraction job state.
 */

import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useTheme } from '../contexts/ThemeContext';
import { Theme } from '../theme';

type Status = 'queued' | 'processing' | 'completed' | 'failed' | 'awaiting_confirmation';

function getConfig(C: Theme): Record<Status, { label: string; bg: string; fg: string }> {
  return {
    queued:                { label: 'Queued',         bg: C.warningDim, fg: C.warning },
    processing:            { label: 'Processing…',    bg: C.primaryDim, fg: C.primary },
    completed:             { label: 'Completed',       bg: C.successDim, fg: C.success },
    failed:                { label: 'Failed',          bg: C.errorDim,   fg: C.error   },
    awaiting_confirmation: { label: 'Confirm Labels', bg: C.warningDim, fg: C.warning },
  };
}

export function StatusBadge({ status }: { status: Status }) {
  const { C } = useTheme();
  const config = getConfig(C);
  const { label, bg, fg } = config[status] ?? config.queued;
  return (
    <View style={[styles.badge, { backgroundColor: bg }]}>
      <Text style={[styles.text, { color: fg }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  text: {
    fontSize: 12,
    fontWeight: '600',
  },
});
