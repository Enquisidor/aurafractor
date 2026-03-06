/**
 * Home / Upload screen.
 *
 * Flow:
 *  1. Pick audio file → upload → get track_id + suggestions
 *  2. User selects labels from chips (AI-suggested + custom text input)
 *  3. Press Extract → navigate to extraction/[id]
 *
 * On upload error the picked file is preserved so the user can retry
 * without re-picking.
 */

import { router } from 'expo-router';
import React, { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { extraction as extractionApi, upload as uploadApi, LabelSuggestion } from '../../src/api/client';
import { FilePicker, PickedFile } from '../../src/components/FilePicker';
import { LabelChip } from '../../src/components/LabelChip';

type Phase = 'idle' | 'uploading' | 'selecting';

interface TrackInfo {
  trackId: string;
  genre: string;
  tempo: number;
  suggestions: LabelSuggestion[];
}

export default function UploadScreen() {
  const [phase, setPhase] = useState<Phase>('idle');
  const [isExtracting, setIsExtracting] = useState(false);
  const [pickedFile, setPickedFile] = useState<PickedFile | null>(null);
  const [trackInfo, setTrackInfo] = useState<TrackInfo | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [customLabel, setCustomLabel] = useState('');
  const [error, setError] = useState<string | null>(null);

  const toggleLabel = (label: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(label) ? next.delete(label) : next.add(label);
      return next;
    });

  const doUpload = async (file: PickedFile) => {
    setError(null);
    setPhase('uploading');
    try {
      const uploadRes = await uploadApi.audio(file.uri, file.name, file.mimeType);
      const suggestRes = await extractionApi.suggestLabels(uploadRes.track_id);
      setTrackInfo({
        trackId: uploadRes.track_id,
        genre: suggestRes.genre,
        tempo: suggestRes.tempo,
        suggestions: suggestRes.suggested_labels,
      });
      setPhase('selecting');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed');
      setPhase('idle');
    }
  };

  const handleFilePicked = (file: PickedFile) => {
    setPickedFile(file);
    doUpload(file);
  };

  const retry = () => {
    if (pickedFile) doUpload(pickedFile);
  };

  const startExtraction = async () => {
    if (!trackInfo) return;
    const labels = [
      ...selected,
      ...(customLabel.trim() ? [customLabel.trim()] : []),
    ];
    if (labels.length === 0) {
      Alert.alert('Select at least one label');
      return;
    }
    setIsExtracting(true);
    setError(null);
    try {
      const res = await extractionApi.extract(
        trackInfo.trackId,
        labels.map((l) => ({ label: l, model: 'demucs' as const })),
      );
      router.push(`/extraction/${res.extraction_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Extraction failed');
    } finally {
      setIsExtracting(false);
    }
  };

  if (phase === 'idle' || phase === 'uploading') {
    return (
      <View style={styles.container}>
        <View style={styles.inner}>
          {phase === 'uploading' ? (
            <>
              <ActivityIndicator size="large" color="#6366F1" />
              <Text style={styles.hint}>Uploading {pickedFile?.name}…</Text>
            </>
          ) : (
            <>
              <Text style={styles.title}>Aurafractor</Text>
              <Text style={styles.subtitle}>
                Upload a track and extract any instrument in plain language.
              </Text>
              <FilePicker onFilePicked={handleFilePicked} />

              {error && (
                <>
                  <Text style={styles.error}>{error}</Text>
                  {pickedFile && (
                    <Pressable style={styles.secondaryButton} onPress={retry}>
                      <Text style={styles.secondaryText}>Retry "{pickedFile.name}"</Text>
                    </Pressable>
                  )}
                </>
              )}
            </>
          )}
        </View>
      </View>
    );
  }

  if (phase === 'selecting' && trackInfo) {
    return (
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.inner}>
          <Text style={styles.sectionTitle}>AI Suggestions</Text>
          <Text style={styles.meta}>
            {trackInfo.genre.replace(/_/g, ' ')} · {trackInfo.tempo} BPM
          </Text>
          <View style={styles.chips}>
            {trackInfo.suggestions.map((s) => (
              <LabelChip
                key={s.label}
                suggestion={s}
                selected={selected.has(s.label)}
                onPress={() => toggleLabel(s.label)}
              />
            ))}
          </View>

          <Text style={styles.sectionTitle}>Custom Label</Text>
          <TextInput
            style={styles.input}
            placeholder='e.g. "dry lead vocals"'
            value={customLabel}
            onChangeText={setCustomLabel}
            returnKeyType="done"
          />

          {error && <Text style={styles.error}>{error}</Text>}

          <Pressable
            style={[styles.button, isExtracting && styles.buttonDisabled]}
            onPress={startExtraction}
            disabled={isExtracting}
          >
            {isExtracting ? (
              <ActivityIndicator color="#FFF" />
            ) : (
              <Text style={styles.buttonText}>Extract</Text>
            )}
          </Pressable>

          <FilePicker onFilePicked={handleFilePicked} />
          <Pressable style={styles.secondaryButton} onPress={() => setPhase('idle')}>
            <Text style={styles.secondaryText}>← Upload different file</Text>
          </Pressable>
        </View>
      </ScrollView>
    );
  }

  return null;
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  inner: { width: '100%', maxWidth: 600, gap: 16 },
  scroll: { padding: 20, alignItems: 'center' },
  title: { fontSize: 32, fontWeight: '700', color: '#1E293B' },
  subtitle: { fontSize: 16, color: '#64748B', textAlign: 'center', lineHeight: 22 },
  sectionTitle: { fontSize: 14, fontWeight: '600', color: '#475569', marginTop: 8 },
  meta: { fontSize: 13, color: '#94A3B8', marginBottom: 4 },
  chips: { flexDirection: 'row', flexWrap: 'wrap' },
  input: {
    borderWidth: 1,
    borderColor: '#CBD5E1',
    borderRadius: 10,
    padding: 12,
    fontSize: 15,
    backgroundColor: '#F8FAFC',
  },
  button: {
    backgroundColor: '#6366F1',
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 12,
    width: '100%',
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#FFF', fontSize: 16, fontWeight: '600' },
  secondaryButton: { alignItems: 'center', paddingVertical: 8 },
  secondaryText: { color: '#6366F1', fontSize: 14 },
  hint: { color: '#64748B', marginTop: 12, fontSize: 14 },
  error: { color: '#EF4444', fontSize: 13, textAlign: 'center' },
});
