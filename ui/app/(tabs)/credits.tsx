/**
 * Credits screen — balance, tier, usage, recent transactions.
 */

import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { user as userApi, CreditsResponse } from '../../src/api/client';
import { ErrorView } from '../../src/components/ErrorView';

const TIER_LABEL: Record<string, string> = {
  free: 'Free',
  pro: 'Pro',
  studio: 'Studio (Unlimited)',
};

export default function CreditsScreen() {
  const [data, setData] = useState<CreditsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await userApi.credits());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load credits');
    }
  }, []);

  useEffect(() => {
    load().finally(() => setLoading(false));
  }, [load]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  if (loading) return <ActivityIndicator style={styles.centered} size="large" color="#6366F1" />;
  if (error) return <ErrorView message={error} />;
  if (!data) return null;

  const pct = data.monthly_allowance > 0
    ? Math.min(1, data.current_balance / data.monthly_allowance)
    : 1;

  return (
    <ScrollView
      contentContainerStyle={styles.scroll}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#6366F1" />}
    >
      {/* Balance card */}
      <View style={styles.card}>
        <Text style={styles.tier}>{TIER_LABEL[data.subscription_tier] ?? data.subscription_tier}</Text>
        <Text style={styles.balance}>{data.current_balance}</Text>
        <Text style={styles.balanceLabel}>credits remaining</Text>

        {/* Progress bar */}
        <View style={styles.barBg}>
          <View style={[styles.barFill, { flex: pct }]} />
          <View style={{ flex: 1 - pct }} />
        </View>

        <Text style={styles.resetDate}>
          Resets {new Date(data.reset_date).toLocaleDateString()}
        </Text>
      </View>

      {/* Usage this month */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>This Month</Text>
        <Row label="Extractions" value={String(data.usage_this_month.extractions)} />
        <Row label="Credits spent" value={String(data.usage_this_month.credits_spent)} />
      </View>

      {/* Recent transactions */}
      {data.recent_transactions.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Recent Transactions</Text>
          {data.recent_transactions.map((tx, i) => (
            <View key={i} style={styles.tx}>
              <View>
                <Text style={styles.txReason}>{tx.reason}</Text>
                <Text style={styles.txDate}>{new Date(tx.created_at).toLocaleDateString()}</Text>
              </View>
              <Text style={[styles.txAmount, tx.amount < 0 ? styles.debit : styles.credit]}>
                {tx.amount > 0 ? '+' : ''}{tx.amount}
              </Text>
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  centered: { flex: 1 },
  scroll: { padding: 20, gap: 16, maxWidth: 600, width: '100%', alignSelf: 'center' },
  card: {
    backgroundColor: '#6366F1',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    gap: 4,
  },
  tier: { color: '#C7D2FE', fontSize: 13, fontWeight: '600', letterSpacing: 1, textTransform: 'uppercase' },
  balance: { color: '#FFF', fontSize: 56, fontWeight: '800', lineHeight: 64 },
  balanceLabel: { color: '#C7D2FE', fontSize: 14 },
  barBg: {
    flexDirection: 'row',
    height: 6,
    borderRadius: 3,
    backgroundColor: '#4F46E5',
    width: '100%',
    marginTop: 12,
    overflow: 'hidden',
  },
  barFill: { backgroundColor: '#A5B4FC', borderRadius: 3 },
  resetDate: { color: '#C7D2FE', fontSize: 12, marginTop: 4 },
  section: {
    backgroundColor: '#F8FAFC',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    gap: 10,
  },
  sectionTitle: { fontSize: 13, fontWeight: '600', color: '#475569' },
  row: { flexDirection: 'row', justifyContent: 'space-between' },
  rowLabel: { color: '#64748B', fontSize: 14 },
  rowValue: { color: '#1E293B', fontWeight: '600', fontSize: 14 },
  tx: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  txReason: { fontSize: 14, color: '#334155', textTransform: 'capitalize' },
  txDate: { fontSize: 11, color: '#94A3B8' },
  txAmount: { fontSize: 15, fontWeight: '700' },
  debit: { color: '#EF4444' },
  credit: { color: '#10B981' },
});
