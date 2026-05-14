import { Tabs } from 'expo-router';
import React, { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '../../src/contexts/ThemeContext';
import { useAuth } from '../../src/hooks/useAuth';

function Icon({ emoji }: { emoji: string }) {
  return <Text style={{ fontSize: 22 }}>{emoji}</Text>;
}

export default function TabLayout() {
  const { C } = useTheme();
  const { error, loading, retry } = useAuth();
  const insets = useSafeAreaInsets();
  const [dismissed, setDismissed] = useState(false);

  // Tab bar is ~49pt; sit the banner just above it
  const TAB_BAR_HEIGHT = 49;

  // Reset dismissed state when a new error surfaces after a retry
  const handleRetry = () => {
    setDismissed(false);
    retry();
  };

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

      {error && !dismissed && !loading && (
        <View
          accessibilityRole="alert"
          accessibilityLiveRegion="polite"
          style={[
            styles.banner,
            { backgroundColor: C.errorDim, borderTopColor: C.error, bottom: insets.bottom + TAB_BAR_HEIGHT },
          ]}
        >
          <Text style={[styles.bannerText, { color: C.error }]}>
            Could not connect — some features unavailable
          </Text>
          <Pressable
            onPress={handleRetry}
            hitSlop={12}
            accessibilityRole="button"
            accessibilityLabel="Retry connection"
            style={[styles.retryButton, { borderColor: C.error }]}
          >
            <Text style={[styles.retryLabel, { color: C.error }]}>Retry</Text>
          </Pressable>
          <Pressable
            onPress={() => setDismissed(true)}
            hitSlop={12}
            accessibilityRole="button"
            accessibilityLabel="Dismiss error banner"
          >
            <Text style={[styles.dismiss, { color: C.error }]}>✕</Text>
          </Pressable>
        </View>
      )}

      {/* Inline spinner shown while a retry is in progress */}
      {loading && !error && (
        <View
          style={[
            styles.banner,
            { backgroundColor: C.primaryDim, borderTopColor: C.primary, bottom: insets.bottom + TAB_BAR_HEIGHT },
          ]}
          accessibilityLiveRegion="polite"
        >
          <ActivityIndicator size="small" color={C.primary} />
          <Text style={[styles.bannerText, { color: C.primary }]}>
            Connecting…
          </Text>
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
  retryButton: {
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 4,
    borderWidth: 1,
  },
  retryLabel: { fontSize: 12, fontWeight: '600' },
  dismiss:    { fontSize: 14, fontWeight: '700' },
});
