/**
 * Home / Upload screen.
 *
 * Flow:
 *  1. Pick audio file → confirm selection → upload → get track_id + suggestions
 *  2. User selects labels from chips (AI-suggested + custom text input)
 *  3. Press Extract → navigate to extraction/[id]
 *
 * On upload error the picked file is preserved so the user can retry
 * without re-picking.
 */

import { router } from 'expo-router';
import React, { useMemo, useState } from 'react';
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
import { useDispatch } from 'react-redux';
import { extraction as extractionApi, upload as uploadApi, LabelSuggestion } from '../../src/api/client';
import { FilePicker, PickedFile } from '../../src/components/FilePicker';
import { LabelChip } from '../../src/components/LabelChip';
import { useTheme } from '../../src/contexts/ThemeContext';
import { AppDispatch } from '../../src/store/store';
import { addEntry, markFailed, markUploaded } from '../../src/store/uploadQueueSlice';
import { Theme } from '../../src/theme';

type Phase = 'idle' | 'confirming' | 'uploading' | 'selecting';

interface TrackInfo {
  trackId: string;
  genre: string;
  tempo: number;
  suggestions: LabelSuggestion[];
}

export default function UploadScreen() {
  const { C } = useTheme();
  const s = useMemo(() => makeStyles(C), [C]);
  const dispatch = useDispatch<AppDispatch>();
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
    // Generate localId before dispatch so we can reference it for updates
    const localId = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    dispatch(addEntry({ localId, filename: file.name, fileUri: file.uri, mimeType: file.mimeType }));
    try {
      const uploadRes = await uploadApi.audio(file.uri, file.name, file.mimeType);
      dispatch(markUploaded({ localId, trackId: uploadRes.track_id }));
      const suggestRes = await extractionApi.suggestLabels(uploadRes.track_id);
      setTrackInfo({
        trackId: uploadRes.track_id,
        genre: suggestRes.genre,
        tempo: suggestRes.tempo,
        suggestions: suggestRes.suggested_labels,
      });
      setPhase('selecting');
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Upload failed';
      dispatch(markFailed({ localId, errorMessage: msg }));
      setError(msg);
      setPhase('confirming');
    }
  };

  const handleFilePicked = (file: PickedFile) => {
    setPickedFile(file);
    setError(null);
    setPhase('confirming');
  };

  const confirmUpload = () => { if (pickedFile) doUpload(pickedFile); };
  const retry = () => { if (pickedFile) doUpload(pickedFile); };

  const startExtraction = async () => {
    if (!trackInfo) return;
    const labels = [
      ...selected,
      ...(customLabel.trim() ? [customLabel.trim()] : []),
    ];
    if (labels.length === 0) { Alert.alert('Select at least one label'); return; }
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

  if (phase === 'idle' || phase === 'confirming' || phase === 'uploading') {
    return (
      <View style={s.container}>
        <View style={s.inner}>
          {phase === 'uploading' ? (
            <>
              <ActivityIndicator size="large" color={C.primary} />
              <Text style={s.hint}>Uploading {pickedFile?.name}…</Text>
            </>
          ) : phase === 'confirming' && pickedFile ? (
            <>
              <Text style={s.title}>Ready to upload</Text>
              <View style={s.fileCard}>
                <Text style={s.fileName} numberOfLines={2}>{pickedFile.name}</Text>
              </View>
              <Pressable style={s.button} onPress={confirmUpload}>
                <Text style={s.buttonText}>Upload & Analyse</Text>
              </Pressable>
              <FilePicker onFilePicked={handleFilePicked} />
              <Pressable style={s.secondaryButton} onPress={() => setPhase('idle')}>
                <Text style={s.secondaryText}>← Choose different file</Text>
              </Pressable>
            </>
          ) : (
            <>
              <Text style={s.title}>Aurafractor</Text>
              <Text style={s.subtitle}>
                Upload a track and extract any instrument in plain language.
              </Text>
              <FilePicker onFilePicked={handleFilePicked} />
              {error && (
                <>
                  <Text style={s.error}>{error}</Text>
                  {pickedFile && (
                    <Pressable style={s.secondaryButton} onPress={retry}>
                      <Text style={s.secondaryText}>Retry "{pickedFile.name}"</Text>
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
      <ScrollView style={s.scrollView} contentContainerStyle={s.scroll}>
        <View style={s.inner}>
          <Text style={s.sectionTitle}>AI Suggestions</Text>
          <Text style={s.meta}>
            {trackInfo.genre.replace(/_/g, ' ')} · {trackInfo.tempo} BPM
          </Text>
          <View style={s.chips}>
            {trackInfo.suggestions.map((suggestion) => (
              <LabelChip
                key={suggestion.label}
                suggestion={suggestion}
                selected={selected.has(suggestion.label)}
                onPress={() => toggleLabel(suggestion.label)}
              />
            ))}
          </View>

          <Text style={s.sectionTitle}>Custom Label</Text>
          <TextInput
            style={s.input}
            placeholder='e.g. "dry lead vocals"'
            placeholderTextColor={C.textMuted}
            value={customLabel}
            onChangeText={setCustomLabel}
            returnKeyType="done"
          />

          {error && <Text style={s.error}>{error}</Text>}

          <Pressable
            style={[s.button, isExtracting && s.buttonDisabled]}
            onPress={startExtraction}
            disabled={isExtracting}
          >
            {isExtracting
              ? <ActivityIndicator color="#FFF" />
              : <Text style={s.buttonText}>Extract</Text>}
          </Pressable>

          <FilePicker onFilePicked={handleFilePicked} />
          <Pressable style={s.secondaryButton} onPress={() => setPhase('idle')}>
            <Text style={s.secondaryText}>← Upload different file</Text>
          </Pressable>
        </View>
      </ScrollView>
    );
  }

  return null;
}

function makeStyles(C: Theme) {
  return StyleSheet.create({
    container:      { flex: 1, backgroundColor: C.bg, alignItems: 'center', justifyContent: 'center', padding: 32 },
    scrollView:     { flex: 1, backgroundColor: C.bg },
    inner:          { width: '100%', maxWidth: 600, gap: 16 },
    scroll:         { padding: 20, alignItems: 'center' },
    title:          { fontSize: 34, fontWeight: '800', color: C.textPrimary, letterSpacing: -0.5 },
    subtitle:       { fontSize: 16, color: C.textMuted, textAlign: 'center', lineHeight: 24 },
    sectionTitle:   { fontSize: 13, fontWeight: '700', color: C.textSecondary, textTransform: 'uppercase', letterSpacing: 0.8, marginTop: 8 },
    meta:           { fontSize: 13, color: C.periwinkle, marginBottom: 4 },
    chips:          { flexDirection: 'row', flexWrap: 'wrap' },
    input: {
      borderWidth: 1.5,
      borderColor: C.border,
      borderRadius: 12,
      padding: 12,
      fontSize: 15,
      color: C.textPrimary,
      backgroundColor: C.surface,
    },
    button: {
      backgroundColor: C.fuchsia,
      paddingVertical: 15,
      borderRadius: 14,
      alignItems: 'center',
      marginTop: 12,
      width: '100%',
    },
    buttonDisabled:   { opacity: 0.5 },
    buttonText:       { color: '#FFF', fontSize: 16, fontWeight: '700', letterSpacing: 0.3 },
    secondaryButton:  { alignItems: 'center', paddingVertical: 8 },
    secondaryText:    { color: C.primary, fontSize: 14, fontWeight: '500' },
    fileCard: {
      backgroundColor: C.surface,
      borderRadius: 14,
      borderWidth: 1.5,
      borderColor: C.border,
      padding: 16,
      width: '100%',
      alignItems: 'center',
    },
    fileName:         { color: C.textPrimary, fontSize: 15, fontWeight: '600', textAlign: 'center' },
    hint:             { color: C.textMuted, marginTop: 12, fontSize: 14, textAlign: 'center' },
    error:            { color: C.error, fontSize: 13, textAlign: 'center' },
  });
}
