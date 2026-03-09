/**
 * Root layout — always renders <Stack> so Expo Router's navigator is stable.
 * Auth loading/error is shown as an overlay, never replacing the navigator.
 */

import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import React, { useEffect } from 'react';
import { ActivityIndicator, Platform, StyleSheet, View } from 'react-native';
import { Provider } from 'react-redux';
import { ThemeProvider, useTheme } from '../src/contexts/ThemeContext';
import { useAuth } from '../src/hooks/useAuth';
import { store } from '../src/store/store';
import { hydrateUploadQueue, syncUploadQueue } from '../src/store/uploadQueueSlice';

function RootLayoutInner() {
  const { loading, error } = useAuth();
  const { C, isDark } = useTheme();

  // Hydrate the upload queue from storage once on mount
  useEffect(() => { store.dispatch(hydrateUploadQueue()); }, []);

  // Sync (retry queued uploads) whenever the backend becomes reachable
  useEffect(() => {
    if (!loading && !error) { store.dispatch(syncUploadQueue()); }
  }, [loading, error]);

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
      {/* Banner is shown in the tabs layout so it never overlaps Stack headers */}
    </>
  );
}

export default function RootLayout() {
  return (
    <Provider store={store}>
      <ThemeProvider>
        <RootLayoutInner />
      </ThemeProvider>
    </Provider>
  );
}

const styles = StyleSheet.create({
  overlay: { ...StyleSheet.absoluteFill, alignItems: 'center', justifyContent: 'center' },
});
