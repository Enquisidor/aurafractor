/**
 * Hook: wraps expo-av Audio for a single stem URL.
 *
 * Loads the sound on mount, unloads on unmount.
 * Returns play/pause toggle + playback position.
 * Degrades gracefully if ExponentAV native module is unavailable.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

export interface AudioPlayerState {
  isPlaying: boolean;
  isLoading: boolean;
  positionMs: number;
  durationMs: number;
  error: string | null;
}

export interface AudioPlayerControls {
  toggle: () => Promise<void>;
  seek: (ms: number) => Promise<void>;
}

const INITIAL_STATE: AudioPlayerState = {
  isPlaying: false,
  isLoading: true,
  positionMs: 0,
  durationMs: 0,
  error: null,
};

export function useAudioPlayer(url: string): AudioPlayerState & AudioPlayerControls {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const soundRef = useRef<any>(null);
  const [state, setState] = useState<AudioPlayerState>(INITIAL_STATE);

  useEffect(() => {
    let mounted = true;

    (async () => {
      try {
        // Dynamic import so a missing native module doesn't crash the whole app
        const { Audio } = await import('expo-av');
        await Audio.setAudioModeAsync({ playsInSilentModeIOS: true });
        const { sound } = await Audio.Sound.createAsync(
          { uri: url },
          { shouldPlay: false },
          (status: { isLoaded: boolean; isPlaying?: boolean; positionMillis?: number; durationMillis?: number }) => {
            if (!mounted || !status.isLoaded) return;
            setState((prev) => ({
              ...prev,
              isPlaying: status.isPlaying ?? false,
              positionMs: status.positionMillis ?? 0,
              durationMs: status.durationMillis ?? prev.durationMs,
              isLoading: false,
            }));
          },
        );
        soundRef.current = sound;
        if (mounted) setState((prev) => ({ ...prev, isLoading: false }));
      } catch (e) {
        if (mounted) {
          setState((prev) => ({
            ...prev,
            isLoading: false,
            error: e instanceof Error ? e.message : 'Audio unavailable',
          }));
        }
      }
    })();

    return () => {
      mounted = false;
      soundRef.current?.unloadAsync();
    };
  }, [url]);

  const toggle = useCallback(async () => {
    const sound = soundRef.current;
    if (!sound) return;
    try {
      const status = await sound.getStatusAsync();
      if (!status.isLoaded) return;
      if (status.isPlaying) {
        await sound.pauseAsync();
      } else {
        if (status.positionMillis >= (status.durationMillis ?? 0) - 100) {
          await sound.setPositionAsync(0);
        }
        await sound.playAsync();
      }
    } catch { /* native module unavailable */ }
  }, []);

  const seek = useCallback(async (ms: number) => {
    try { await soundRef.current?.setPositionAsync(ms); } catch { /* unavailable */ }
  }, []);

  return { ...state, toggle, seek };
}
