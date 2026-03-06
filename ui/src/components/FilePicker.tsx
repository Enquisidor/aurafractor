/**
 * Platform-aware audio file picker.
 * Web: hidden <input type="file">  |  Native: expo-document-picker
 * Returns the same { uri, name, mimeType } shape on both platforms.
 */

import React, { useRef } from 'react';
import { Platform, Pressable, StyleSheet, Text } from 'react-native';

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
          style={[styles.button, disabled && styles.buttonDisabled]}
          onPress={() => inputRef.current?.click()}
          disabled={disabled}
        >
          <Text style={styles.buttonText}>Choose Audio File</Text>
        </Pressable>
      </>
    );
  }

  // Native
  const pickNative = async () => {
    const { getDocumentAsync } = await import('expo-document-picker');
    const result = await getDocumentAsync({
      type: AUDIO_TYPES,
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
      style={[styles.button, disabled && styles.buttonDisabled]}
      onPress={pickNative}
      disabled={disabled}
    >
      <Text style={styles.buttonText}>Choose Audio File</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    backgroundColor: '#6366F1',
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
    width: '100%',
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#FFF', fontSize: 16, fontWeight: '600' },
});
