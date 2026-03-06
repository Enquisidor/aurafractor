/**
 * Hook: wraps expo-av Audio for a single stem URL.
 *
 * Loads the sound on mount, unloads on unmount.
 * Returns play/pause toggle + playback position.
 */

import { Audio, AVPlaybackStatus } from 'expo-av';
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
  const soundRef = useRef<Audio.Sound | null>(null);
  const [state, setState] = useState<AudioPlayerState>(INITIAL_STATE);

  useEffect(() => {
    let mounted = true;

    (async () => {
      try {
        await Audio.setAudioModeAsync({ playsInSilentModeIOS: true });
        const { sound } = await Audio.Sound.createAsync(
          { uri: url },
          { shouldPlay: false },
          (status: AVPlaybackStatus) => {
            if (!mounted || !status.isLoaded) return;
            setState((prev) => ({
              ...prev,
              isPlaying: status.isPlaying,
              positionMs: status.positionMillis,
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
            error: e instanceof Error ? e.message : 'Audio load failed',
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
    const status = await sound.getStatusAsync();
    if (!status.isLoaded) return;
    if (status.isPlaying) {
      await sound.pauseAsync();
    } else {
      // Restart from beginning if finished
      if (status.positionMillis >= (status.durationMillis ?? 0) - 100) {
        await sound.setPositionAsync(0);
      }
      await sound.playAsync();
    }
  }, []);

  const seek = useCallback(async (ms: number) => {
    await soundRef.current?.setPositionAsync(ms);
  }, []);

  return { ...state, toggle, seek };
}
