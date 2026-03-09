import { Tabs } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '../../src/contexts/ThemeContext';
import { useAuth } from '../../src/hooks/useAuth';

function Icon({ emoji }: { emoji: string }) {
  return <Text style={{ fontSize: 22 }}>{emoji}</Text>;
}

export default function TabLayout() {
  const { C } = useTheme();
  const { error } = useAuth();
  const insets = useSafeAreaInsets();
  const [dismissed, setDismissed] = useState(false);

  // Tab bar is ~49pt; sit the banner just above it
  const TAB_BAR_HEIGHT = 49;

  return (
    <View style={{ flex: 1 }}>
      <Tabs
        screenOptions={{
          tabBarActiveTintColor: C.primary,
          tabBarInactiveTintColor: C.textMuted,
          tabBarStyle: {
            backgroundColor: C.surface,
            borderTopColor: C.border,
            borderTopWidth: 1,
          },
          headerStyle: { backgroundColor: C.surface },
          headerTintColor: C.textPrimary,
          headerShadowVisible: false,
          headerShown: true,
        }}
      >
        <Tabs.Screen
          name="index"
          options={{ title: 'Upload', tabBarIcon: () => <Icon emoji="🎵" /> }}
        />
        <Tabs.Screen
          name="history"
          options={{ title: 'History', tabBarIcon: () => <Icon emoji="📋" /> }}
        />
        <Tabs.Screen
          name="credits"
          options={{ title: 'Credits', tabBarIcon: () => <Icon emoji="💳" /> }}
        />
        <Tabs.Screen
          name="settings"
          options={{ title: 'Settings', tabBarIcon: () => <Icon emoji="⚙️" /> }}
        />
      </Tabs>

      {error && !dismissed && (
        <View style={[
          styles.banner,
          { backgroundColor: C.errorDim, borderTopColor: C.error, bottom: insets.bottom + TAB_BAR_HEIGHT },
        ]}>
          <Text style={[styles.bannerText, { color: C.error }]}>
            Backend unreachable — some features unavailable
          </Text>
          <Pressable onPress={() => setDismissed(true)} hitSlop={12}>
            <Text style={[styles.dismiss, { color: C.error }]}>✕</Text>
          </Pressable>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    position: 'absolute',
    left: 0,
    right: 0,
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderTopWidth: 1,
    gap: 8,
  },
  bannerText: { flex: 1, fontSize: 13, fontWeight: '500', textAlign: 'center' },
  dismiss:    { fontSize: 14, fontWeight: '700' },
});
