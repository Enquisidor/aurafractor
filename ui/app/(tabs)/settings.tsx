/**
 * Settings screen — theme toggle, device ID, auth status.
 */

import React, { useMemo } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useTheme } from '../../src/contexts/ThemeContext';
import { useAuth } from '../../src/hooks/useAuth';
import { Theme } from '../../src/theme';

export default function SettingsScreen() {
  const { C, isDark, toggleTheme } = useTheme();
  const { auth, error } = useAuth();
  const s = useMemo(() => makeStyles(C), [C]);

  return (
    <ScrollView style={s.screen} contentContainerStyle={s.scroll}>

      {/* Appearance */}
      <Text style={s.sectionTitle}>Appearance</Text>
      <View style={s.card}>
        <View style={s.row}>
          <Text style={s.rowLabel}>Theme</Text>
          <Pressable style={s.toggle} onPress={toggleTheme}>
            <Text style={s.toggleText}>{isDark ? '☀️  Light' : '🌙  Dark'}</Text>
          </Pressable>
        </View>
      </View>

      {/* Account */}
      <Text style={s.sectionTitle}>Account</Text>
      <View style={s.card}>
        <View style={s.row}>
          <Text style={s.rowLabel}>Plan</Text>
          <Text style={s.rowValue}>
            {auth ? auth.subscriptionTier.charAt(0).toUpperCase() + auth.subscriptionTier.slice(1) : '—'}
          </Text>
        </View>
        <View style={s.row}>
          <Text style={s.rowLabel}>Backend</Text>
          <Text style={[s.rowValue, error ? { color: C.error } : { color: C.success }]}>
            {error ? 'Unreachable' : 'Connected'}
          </Text>
        </View>
        {auth && (
          <View style={s.row}>
            <Text style={s.rowLabel}>User ID</Text>
            <Text style={s.rowValueMono} numberOfLines={1}>{auth.userId}</Text>
          </View>
        )}
      </View>

    </ScrollView>
  );
}

function makeStyles(C: Theme) {
  return StyleSheet.create({
    screen:       { flex: 1, backgroundColor: C.bg },
    scroll:       { padding: 20, gap: 8, maxWidth: 600, width: '100%', alignSelf: 'center' },
    sectionTitle: {
      fontSize: 12,
      fontWeight: '700',
      color: C.textSecondary,
      textTransform: 'uppercase',
      letterSpacing: 1,
      marginTop: 12,
      marginBottom: 4,
      paddingHorizontal: 4,
    },
    card: {
      backgroundColor: C.surface,
      borderRadius: 14,
      borderWidth: 1,
      borderColor: C.border,
      overflow: 'hidden',
    },
    row: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      paddingVertical: 14,
      paddingHorizontal: 16,
      borderBottomWidth: StyleSheet.hairlineWidth,
      borderBottomColor: C.border,
    },
    rowLabel:     { fontSize: 15, color: C.textPrimary },
    rowValue:     { fontSize: 15, color: C.textMuted, fontWeight: '500' },
    rowValueMono: { fontSize: 12, color: C.textMuted, flex: 1, textAlign: 'right', marginLeft: 12 },
    toggle: {
      paddingVertical: 6,
      paddingHorizontal: 14,
      borderRadius: 20,
      backgroundColor: C.primaryDim,
      borderWidth: 1,
      borderColor: C.primary,
    },
    toggleText: { color: C.primary, fontSize: 13, fontWeight: '600' },
  });
}
