/**
 * FirstLaunchModal — shown once on first app launch.
 *
 * Aurafractor uses anonymous device-ID registration (no email/password).
 * This modal explains the value proposition and lets the user confirm
 * they are ready to start. It is dismissed permanently on confirmation;
 * the seen flag is persisted via platform storage.
 *
 * Three display states, determined by the `isNewUser` prop and the
 * presence of a stored session token:
 *
 * 1. isNewUser === true
 *    The auth API confirmed a brand-new first-time registration.
 *    Heading: "Account created"
 *    CTA: "Start using Aurafractor"
 *
 * 2. isNewUser === false AND a session token exists in storage
 *    A returning device: the device was already registered in a prior
 *    session and the token is still present. The user cleared
 *    `first_launch_seen` (e.g. reinstalled the app) but their account
 *    was auto-restored. Heading: "Welcome back"
 *    CTA: "Continue"
 *
 * 3. isNewUser === false AND no session token in storage
 *    Genuine first launch with registration still pending (or in progress).
 *    Original neutral welcome copy. CTA: "Get started"
 *
 * Design gap (logged as DEC-006): no visual design reference was provided
 * for this screen. The layout uses the project's existing design tokens
 * and follows the neon-pastel theme. A designer pass is required to replace
 * this with a finalized design.
 *
 * Decision (logged as DEC-012): storage-check approach for distinguishing
 * returning-device from genuine first-launch within the isNewUser === false
 * branch — see decision log for full rationale.
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
const SESSION_TOKEN_KEY = 'session_token';

type ModalVariant = 'new-user' | 'returning-device' | 'first-launch';

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
  const [variant, setVariant] = useState<ModalVariant>('first-launch');

  useEffect(() => {
    if (isNewUser) {
      // Backend confirmed this is a new registration — show immediately
      // without waiting for the storage check (the storage write on dismiss
      // will prevent it showing again on subsequent launches).
      setVariant('new-user');
      setVisible(true);
      return;
    }
    // For isNewUser === false, check both the seen flag and whether a session
    // token already exists. A session token present means the device was
    // registered in a prior session and the account has been auto-restored —
    // the user is a returning device, not a genuine first-time visitor.
    Promise.all([
      storage.getItem(SEEN_KEY),
      storage.getItem(SESSION_TOKEN_KEY),
    ]).then(([seen, sessionToken]) => {
      if (seen) return; // Already shown — do not re-show.
      const resolvedVariant: ModalVariant = sessionToken
        ? 'returning-device'
        : 'first-launch';
      setVariant(resolvedVariant);
      setVisible(true);
    });
  }, [isNewUser]);

  const handleStart = async () => {
    await storage.setItem(SEEN_KEY, '1');
    setVisible(false);
    let announcement: string;
    if (variant === 'new-user') {
      announcement = 'Account created. Welcome to Aurafractor.';
    } else if (variant === 'returning-device') {
      announcement = 'Welcome back. Your account has been restored.';
    } else {
      announcement = "Welcome to Aurafractor. Let's get started.";
    }
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
          {variant === 'new-user' ? (
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
          ) : variant === 'returning-device' ? (
            <>
              <Text style={[styles.title, { color: C.textPrimary }]}>
                Welcome back
              </Text>
              <Text style={[styles.body, { color: C.textSecondary }]}>
                We recognised your device and restored your account
                automatically. No password needed — your account is always
                tied to this device.
              </Text>
              <Pressable
                onPress={handleStart}
                style={({ pressed }) => [
                  styles.cta,
                  { backgroundColor: pressed ? C.primaryLight : C.primary },
                ]}
                accessibilityRole="button"
                accessibilityLabel="Continue to Aurafractor"
              >
                <Text style={styles.ctaLabel}>Continue</Text>
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
