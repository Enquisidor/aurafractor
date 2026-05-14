/**
 * FirstLaunchModal — shown once on first app launch.
 *
 * Aurafractor uses anonymous device-ID registration (no email/password).
 * This modal explains the value proposition and lets the user confirm
 * they are ready to start. It is dismissed permanently on confirmation;
 * the seen flag is persisted via platform storage.
 *
 * When `isNewUser` is true (set from the auth API's `is_new_user` response
 * field), the modal presents the moment as an active account-creation
 * confirmation: the heading is "Account created", and copy explains that
 * the account is tied to this device. The CTA reads "Start using Aurafractor".
 *
 * When `isNewUser` is false but `first_launch_seen` has not been set (e.g.
 * a returning user who cleared storage), the modal shows a neutral welcome
 * tone with the original copy and "Get started" CTA.
 *
 * Design gap (logged as DEC-006): no visual design reference was provided
 * for this screen. The layout uses the project's existing design tokens
 * and follows the neon-pastel theme. A designer pass is required to replace
 * this with a finalized design.
 */

import React, { useEffect, useState } from 'react';
import {
  AccessibilityInfo,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useTheme } from '../contexts/ThemeContext';
import { storage } from '../storage/platform';

const SEEN_KEY = 'first_launch_seen';

interface FirstLaunchModalProps {
  /**
   * When true (sourced from the auth API's `is_new_user` field), the modal
   * is shown regardless of the storage flag and presents an active
   * account-creation confirmation rather than a passive welcome.
   * Defaults to false.
   */
  isNewUser?: boolean;
}

export function FirstLaunchModal({ isNewUser = false }: FirstLaunchModalProps) {
  const { C } = useTheme();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (isNewUser) {
      // Backend confirmed this is a new registration — show immediately
      // without waiting for the storage check (the storage write on dismiss
      // will prevent it showing again on subsequent launches).
      setVisible(true);
      return;
    }
    storage.getItem(SEEN_KEY).then((seen) => {
      if (!seen) setVisible(true);
    });
  }, [isNewUser]);

  const handleStart = async () => {
    await storage.setItem(SEEN_KEY, '1');
    setVisible(false);
    const announcement = isNewUser
      ? 'Account created. Welcome to Aurafractor.'
      : 'Welcome to Aurafractor. Let\'s get started.';
    AccessibilityInfo.announceForAccessibility(announcement);
  };

  if (!visible) return null;

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      statusBarTranslucent
      accessibilityViewIsModal
      onRequestClose={handleStart}
    >
      <View style={styles.backdrop}>
        <View style={[styles.card, { backgroundColor: C.surface, borderColor: C.border }]}>
          {isNewUser ? (
            <>
              <Text style={[styles.title, { color: C.textPrimary }]}>
                Account created
              </Text>
              <Text style={[styles.body, { color: C.textSecondary }]}>
                Your Aurafractor account is tied to this device. The app
                recognises you automatically — no password required.
              </Text>
              <Text style={[styles.body, { color: C.textSecondary }]}>
                Describe any sound you want extracted — vocals, kick drum,
                synth lead — and AI will isolate it from any track.
              </Text>
              <Pressable
                onPress={handleStart}
                style={({ pressed }) => [
                  styles.cta,
                  { backgroundColor: pressed ? C.primaryLight : C.primary },
                ]}
                accessibilityRole="button"
                accessibilityLabel="Start using Aurafractor"
              >
                <Text style={styles.ctaLabel}>Start using Aurafractor</Text>
              </Pressable>
            </>
          ) : (
            <>
              <Text style={[styles.title, { color: C.textPrimary }]}>
                Welcome to Aurafractor
              </Text>
              <Text style={[styles.body, { color: C.textSecondary }]}>
                Describe the sound you want — vocals, kick, synth lead — and we'll
                isolate it from any track using AI.
              </Text>
              <Text style={[styles.body, { color: C.textSecondary }]}>
                No account needed. Your device is registered automatically so you can
                start right away.
              </Text>
              <Pressable
                onPress={handleStart}
                style={({ pressed }) => [
                  styles.cta,
                  { backgroundColor: pressed ? C.primaryLight : C.primary },
                ]}
                accessibilityRole="button"
                accessibilityLabel="Get started with Aurafractor"
              >
                <Text style={styles.ctaLabel}>Get started</Text>
              </Pressable>
            </>
          )}
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.55)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  card: {
    width: '100%',
    maxWidth: 440,
    borderRadius: 16,
    borderWidth: 1,
    padding: 28,
    gap: 16,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    textAlign: 'center',
  },
  body: {
    fontSize: 15,
    lineHeight: 22,
    textAlign: 'center',
  },
  cta: {
    marginTop: 8,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  ctaLabel: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
});
