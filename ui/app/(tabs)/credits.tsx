/**
 * Credits screen — balance, tier, usage, recent transactions.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { user as userApi, CreditsResponse } from '../../src/api/client';
import { ErrorView } from '../../src/components/ErrorView';
import { useTheme } from '../../src/contexts/ThemeContext';
import { Theme } from '../../src/theme';

const TIER_LABEL: Record<string, string> = {
  free: 'Free',
  pro: 'Pro',
  studio: 'Studio (Unlimited)',
};

export default function CreditsScreen() {
  const { C, isDark, toggleTheme } = useTheme();
  const s = useMemo(() => makeStyles(C), [C]);
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

  useEffect(() => { load().finally(() => setLoading(false)); }, [load]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  if (loading) return <ActivityIndicator style={s.centered} size="large" color={C.primary} />;
  if (error) return <ErrorView message={error} />;
  if (!data) return null;

  const pct = data.monthly_allowance > 0
    ? Math.min(1, data.current_balance / data.monthly_allowance)
    : 1;

  return (
    <ScrollView
      style={s.screen}
      contentContainerStyle={s.scroll}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={C.primary} />}
    >
      {/* Balance card */}
      <View style={s.card}>
        <Text style={s.tier}>{TIER_LABEL[data.subscription_tier] ?? data.subscription_tier}</Text>
        <Text style={s.balance}>{data.current_balance}</Text>
        <Text style={s.balanceLabel}>credits remaining</Text>
        <View style={s.barBg}>
          <View style={[s.barFill, { flex: pct }]} />
          <View style={{ flex: 1 - pct }} />
        </View>
        <Text style={s.resetDate}>Resets {new Date(data.reset_date).toLocaleDateString()}</Text>
      </View>

      {/* Usage this month */}
      <View style={s.section}>
        <Text style={s.sectionTitle}>This Month</Text>
        <Row label="Extractions" value={String(data.usage_this_month.extractions)} s={s} />
        <Row label="Credits spent" value={String(data.usage_this_month.credits_spent)} s={s} />
      </View>

      {/* Recent transactions */}
      {data.recent_transactions.length > 0 && (
        <View style={s.section}>
          <Text style={s.sectionTitle}>Recent Transactions</Text>
          {data.recent_transactions.map((tx, i) => (
            <View key={i} style={s.tx}>
              <View>
                <Text style={s.txReason}>{tx.reason}</Text>
                <Text style={s.txDate}>{new Date(tx.created_at).toLocaleDateString()}</Text>
              </View>
              <Text style={[s.txAmount, tx.amount < 0 ? s.debit : s.credit]}>
                {tx.amount > 0 ? '+' : ''}{tx.amount}
              </Text>
            </View>
          ))}
        </View>
      )}

      {/* Theme toggle */}
      <Pressable style={s.themeToggle} onPress={toggleTheme}>
        <Text style={s.themeToggleText}>{isDark ? '☀️  Light mode' : '🌙  Dark mode'}</Text>
      </Pressable>
    </ScrollView>
  );
}

function Row({ label, value, s }: { label: string; value: string; s: ReturnType<typeof makeStyles> }) {
  return (
    <View style={s.row}>
      <Text style={s.rowLabel}>{label}</Text>
      <Text style={s.rowValue}>{value}</Text>
    </View>
  );
}

function makeStyles(C: Theme) {
  return StyleSheet.create({
    centered: { flex: 1 },
    screen:   { flex: 1, backgroundColor: C.bg },
    scroll:   { padding: 20, gap: 16, maxWidth: 600, width: '100%', alignSelf: 'center' },
    card: {
      backgroundColor: C.primary,
      borderRadius: 20,
      padding: 28,
      alignItems: 'center',
      gap: 4,
    },
    tier:         { color: C.primaryLight, fontSize: 12, fontWeight: '700', letterSpacing: 1.2, textTransform: 'uppercase' },
    balance:      { color: '#FFF', fontSize: 60, fontWeight: '800', lineHeight: 68 },
    balanceLabel: { color: C.primaryLight, fontSize: 14 },
    barBg: {
      flexDirection: 'row',
      height: 8,
      borderRadius: 4,
      backgroundColor: 'rgba(0,0,0,0.2)',
      width: '100%',
      marginTop: 14,
      overflow: 'hidden',
    },
    barFill:  { backgroundColor: C.fuchsia, borderRadius: 4 },
    resetDate: { color: C.primaryLight, fontSize: 12, marginTop: 6 },
    section: {
      backgroundColor: C.surface,
      borderRadius: 14,
      padding: 16,
      borderWidth: 1,
      borderColor: C.border,
      gap: 10,
    },
    sectionTitle: { fontSize: 13, fontWeight: '700', color: C.textSecondary, textTransform: 'uppercase', letterSpacing: 0.8 },
    row:      { flexDirection: 'row', justifyContent: 'space-between' },
    rowLabel: { color: C.textMuted, fontSize: 14 },
    rowValue: { color: C.textPrimary, fontWeight: '600', fontSize: 14 },
    tx:       { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
    txReason: { fontSize: 14, color: C.textPrimary, textTransform: 'capitalize' },
    txDate:   { fontSize: 11, color: C.textMuted },
    txAmount: { fontSize: 15, fontWeight: '700' },
    debit:    { color: C.error },
    credit:   { color: C.success },
    themeToggle: {
      alignSelf: 'center',
      paddingVertical: 10,
      paddingHorizontal: 20,
      borderRadius: 20,
      borderWidth: 1,
      borderColor: C.border,
      backgroundColor: C.surface,
      marginTop: 4,
    },
    themeToggleText: { color: C.textSecondary, fontSize: 14, fontWeight: '600' },
  });
}
