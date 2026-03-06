/**
 * Root layout — always renders <Stack> so Expo Router's navigator is stable.
 * Auth loading/error is shown as an overlay, never replacing the navigator.
 */

import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import React from 'react';
import { ActivityIndicator, Platform, StyleSheet, Text, View } from 'react-native';
import { useAuth } from '../src/hooks/useAuth';

export default function RootLayout() {
  const { loading, error } = useAuth();

  return (
    <>
      {Platform.OS !== 'web' && <StatusBar style="auto" />}
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen
          name="extraction/[id]"
          options={{ headerShown: true, title: 'Extraction' }}
        />
        <Stack.Screen
          name="extraction/feedback"
          options={{ headerShown: true, title: 'Feedback' }}
        />
      </Stack>

      {/* Auth overlay — sits above navigation without replacing the navigator */}
      {(loading || error) && (
        <View style={styles.overlay}>
          {loading && <ActivityIndicator size="large" color="#6366F1" />}
          {error && <Text style={styles.error}>{error}</Text>}
        </View>
      )}
    </>
  );
}

const styles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFill,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  error: { color: '#EF4444', fontSize: 15, textAlign: 'center', paddingHorizontal: 32 },
});
