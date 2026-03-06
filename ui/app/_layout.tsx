/**
 * Root layout — always renders <Stack> so Expo Router's navigator is stable.
 * Auth loading/error is shown as an overlay, never replacing the navigator.
 */

import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import React from 'react';
import { ActivityIndicator, Platform, StyleSheet, Text, View } from 'react-native';
import { ThemeProvider, useTheme } from '../src/contexts/ThemeContext';
import { useAuth } from '../src/hooks/useAuth';

function RootLayoutInner() {
  const { loading, error } = useAuth();
  const { C, isDark } = useTheme();

  return (
    <>
      {Platform.OS !== 'web' && <StatusBar style={isDark ? 'light' : 'dark'} />}
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen
          name="extraction/[id]"
          options={{
            headerShown: true,
            title: 'Extraction',
            headerStyle: { backgroundColor: C.surface },
            headerTintColor: C.textPrimary,
            headerShadowVisible: false,
          }}
        />
        <Stack.Screen
          name="extraction/feedback"
          options={{
            headerShown: true,
            title: 'Feedback',
            headerStyle: { backgroundColor: C.surface },
            headerTintColor: C.textPrimary,
            headerShadowVisible: false,
          }}
        />
      </Stack>

      {/* Full-screen overlay only while first loading */}
      {loading && (
        <View style={[styles.overlay, { backgroundColor: C.bg }]}>
          <ActivityIndicator size="large" color={C.primary} />
        </View>
      )}
      {/* Non-blocking banner on error — navigation still works */}
      {!loading && error && (
        <View style={[styles.banner, { backgroundColor: C.errorDim, borderBottomColor: C.error }]}>
          <Text style={[styles.bannerText, { color: C.error }]}>
            Backend unreachable — some features unavailable
          </Text>
        </View>
      )}
    </>
  );
}

export default function RootLayout() {
  return (
    <ThemeProvider>
      <RootLayoutInner />
    </ThemeProvider>
  );
}

const styles = StyleSheet.create({
  overlay: { ...StyleSheet.absoluteFill, alignItems: 'center', justifyContent: 'center' },
  banner: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    zIndex: 999,
  },
  bannerText: { fontSize: 13, textAlign: 'center', fontWeight: '500' },
});
