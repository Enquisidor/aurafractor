/**
 * Status badge for extraction job state.
 */

import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

type Status = 'queued' | 'processing' | 'completed' | 'failed' | 'awaiting_confirmation';

const CONFIG: Record<Status, { label: string; bg: string; fg: string }> = {
  queued: { label: 'Queued', bg: '#FEF3C7', fg: '#92400E' },
  processing: { label: 'Processing…', bg: '#DBEAFE', fg: '#1E40AF' },
  completed: { label: 'Completed', bg: '#D1FAE5', fg: '#065F46' },
  failed: { label: 'Failed', bg: '#FEE2E2', fg: '#991B1B' },
  awaiting_confirmation: { label: 'Confirm Labels', bg: '#FEF9C3', fg: '#713F12' },
};

export function StatusBadge({ status }: { status: Status }) {
  const { label, bg, fg } = CONFIG[status] ?? CONFIG.queued;
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
