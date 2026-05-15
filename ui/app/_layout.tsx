/**
 * Root layout — always renders <Stack> so Expo Router's navigator is stable.
 * Auth loading/error is shown as an overlay, never replacing the navigator.
 */

import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import React, { useEffect } from 'react';
import { ActivityIndicator, Platform, StyleSheet, View } from 'react-native';
import { Provider } from 'react-redux';
import { FirstLaunchModal } from '../src/components/FirstLaunchModal';
import { ThemeProvider, useTheme } from '../src/contexts/ThemeContext';
import { useAuth } from '../src/hooks/useAuth';
import { store } from '../src/store/store';
import { hydrateExtractions } from '../src/store/extractionsSlice';
import { hydrateUploadQueue, syncUploadQueue } from '../src/store/uploadQueueSlice';

function RootLayoutInner() {
  const { loading, error, isNewUser } = useAuth();
  const { C, isDark } = useTheme();

  // Hydrate the upload queue and extractions cache from storage once on mount
  useEffect(() => {
    store.dispatch(hydrateUploadQueue());
    store.dispatch(hydrateExtractions());
  }, []);

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

      {/* First-launch onboarding modal — shown once, persisted via storage.
          isNewUser (from the auth API's is_new_user field) forces the modal
          visible immediately after a successful first-time registration,
          without waiting for the storage read. */}
      {!loading && <FirstLaunchModal isNewUser={isNewUser} />}

      {/* Full-screen overlay only while first loading */}
      {loading && (
        <View style={[styles.overlay, { backgroundColor: C.bg }]}>
          <ActivityIndicator size="large" color={C.primary} />
        </View>
      )}
      {/* Auth error banner is shown in the tabs layout so it never overlaps Stack headers */}
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
