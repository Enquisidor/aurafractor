/**
 * Platform-aware audio file picker.
 * Web: hidden <input type="file">  |  Native: expo-document-picker
 * Returns the same { uri, name, mimeType } shape on both platforms.
 */

import React, { useRef } from 'react';
import { Platform, Pressable, StyleSheet, Text } from 'react-native';
import { useTheme } from '../contexts/ThemeContext';

export interface PickedFile {
  uri: string;
  name: string;
  mimeType: string;
}

interface Props {
  onFilePicked: (file: PickedFile) => void;
  disabled?: boolean;
}

const AUDIO_TYPES = ['audio/mpeg', 'audio/wav', 'audio/flac', 'audio/ogg', 'audio/*'];

export function FilePicker({ onFilePicked, disabled }: Props) {
  const { C } = useTheme();
  const inputRef = useRef<HTMLInputElement | null>(null);

  if (Platform.OS === 'web') {
    return (
      <>
        {/* Hidden native file input */}
        <input
          ref={inputRef}
          type="file"
          accept={AUDIO_TYPES.join(',')}
          style={{ display: 'none' }}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            const uri = URL.createObjectURL(file);
            onFilePicked({ uri, name: file.name, mimeType: file.type || 'audio/mpeg' });
            // Reset so the same file can be picked again
            e.target.value = '';
          }}
        />
        <Pressable
          style={[styles.button, { backgroundColor: C.fuchsia }, disabled && styles.buttonDisabled]}
          onPress={() => inputRef.current?.click()}
          disabled={disabled}
        >
          <Text style={styles.buttonText}>Choose Audio File</Text>
        </Pressable>
      </>
    );
  }

  // Native — use a single wildcard so the Android picker shows all audio files
  // (passing an array of MIME types can result in an empty "Recent" view)
  const pickNative = async () => {
    const { getDocumentAsync } = await import('expo-document-picker');
    const result = await getDocumentAsync({
      type: 'audio/*',
      copyToCacheDirectory: true,
    });
    if (result.canceled) return;
    const asset = result.assets[0];
    onFilePicked({
      uri: asset.uri,
      name: asset.name,
      mimeType: asset.mimeType ?? 'audio/mpeg',
    });
  };

  return (
    <Pressable
      style={[styles.button, { backgroundColor: C.fuchsia }, disabled && styles.buttonDisabled]}
      onPress={pickNative}
      disabled={disabled}
    >
      <Text style={styles.buttonText}>Choose Audio File</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
    width: '100%',
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#FFF', fontSize: 16, fontWeight: '600' },
});
