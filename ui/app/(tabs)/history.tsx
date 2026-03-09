/**
 * History screen — paginated list of uploaded tracks with extraction summaries.
 */

import { router } from 'expo-router';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useSelector } from 'react-redux';
import { user as userApi, TrackSummary } from '../../src/api/client';
import { StatusBadge } from '../../src/components/StatusBadge';
import { useTheme } from '../../src/contexts/ThemeContext';
import { RootState } from '../../src/store/store';
import { UploadEntry } from '../../src/store/uploadQueueSlice';
import { Theme } from '../../src/theme'; // used by makeStyles + TrackRow

const PAGE_SIZE = 20;

// Unified row shape for both server and local-only entries
type HistoryRow =
  | { kind: 'server'; track: TrackSummary }
  | { kind: 'local';  entry: UploadEntry };

export default function HistoryScreen() {
  const { C } = useTheme();
  const s = useMemo(() => makeStyles(C), [C]);
  const queueEntries = useSelector((state: RootState) => state.uploadQueue.entries);
  const [tracks, setTracks] = useState<TrackSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (offset: number, replace: boolean) => {
    try {
      const res = await userApi.history(PAGE_SIZE, offset);
      setTotal(res.total_tracks);
      setTracks((prev) => (replace ? res.tracks : [...prev, ...res.tracks]));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load history');
    }
  }, []);

  useEffect(() => { load(0, true).finally(() => setLoading(false)); }, [load]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load(0, true);
    setRefreshing(false);
  }, [load]);

  const onEndReached = useCallback(async () => {
    if (loadingMore || tracks.length >= total) return;
    setLoadingMore(true);
    await load(tracks.length, false);
    setLoadingMore(false);
  }, [load, loadingMore, tracks.length, total]);

  if (loading) return <ActivityIndicator style={s.centered} size="large" color={C.primary} />;

  // Build unified list: server rows first, then local entries whose trackId
  // doesn't appear in the server list (failed/uploading attempts).
  const serverTrackIds = new Set(tracks.map((t) => t.track_id));
  const localOnly = queueEntries.filter(
    (e: UploadEntry) => !e.trackId || !serverTrackIds.has(e.trackId),
  );
  const rows: HistoryRow[] = [
    ...localOnly.map((entry): HistoryRow => ({ kind: 'local', entry })),
    ...tracks.map((track): HistoryRow => ({ kind: 'server', track })),
  ];

  return (
    <FlatList
      style={s.list}
      data={rows}
      keyExtractor={(r) => r.kind === 'server' ? r.track.track_id : `local-${r.entry.localId}`}
      contentContainerStyle={s.listContent}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={C.primary} />}
      onEndReached={onEndReached}
      onEndReachedThreshold={0.2}
      ListHeaderComponent={error ? (
        <View style={s.errorBanner}>
          <Text style={s.errorText}>Couldn't reach server — showing local history</Text>
        </View>
      ) : null}
      ListEmptyComponent={<Text style={s.empty}>No tracks yet. Upload one!</Text>}
      ListFooterComponent={loadingMore ? <ActivityIndicator color={C.primary} /> : null}
      renderItem={({ item }) =>
        item.kind === 'server'
          ? <TrackRow track={item.track} s={s} />
          : <LocalRow entry={item.entry} s={s} />
      }
    />
  );
}

const STATUS_LABEL: Record<string, string> = { uploading: 'Uploading…', uploaded: 'Uploaded', failed: 'Failed' };

function LocalRow({ entry, s }: { entry: UploadEntry; s: ReturnType<typeof makeStyles> }) {
  const isFailed = entry.status === 'failed';
  return (
    <View style={[s.row, isFailed && s.rowFailed]}>
      <View style={s.rowMain}>
        <Text style={s.filename} numberOfLines={1}>{entry.filename}</Text>
        <Text style={s.meta}>
          {new Date(entry.attemptedAt).toLocaleDateString()} · {entry.errorMessage ?? STATUS_LABEL[entry.status]}
        </Text>
      </View>
      <StatusBadge status={isFailed ? 'failed' : 'processing'} />
    </View>
  );
}

function TrackRow({ track, s }: { track: TrackSummary; s: ReturnType<typeof makeStyles> }) {
  const latest = track.latest_extraction;
  return (
    <Pressable
      style={s.row}
      onPress={() => latest && router.push(`/extraction/${latest.extraction_id}`)}
      disabled={!latest}
    >
      <View style={s.rowMain}>
        <Text style={s.filename} numberOfLines={1}>{track.filename}</Text>
        <Text style={s.meta}>
          {new Date(track.uploaded_at).toLocaleDateString()} · {track.extractions_count} extraction{track.extractions_count !== 1 ? 's' : ''}
        </Text>
      </View>
      {latest && (
        <StatusBadge status={latest.status as Parameters<typeof StatusBadge>[0]['status']} />
      )}
    </Pressable>
  );
}

function makeStyles(C: Theme) {
  return StyleSheet.create({
    centered:    { flex: 1 },
    list:        { flex: 1, backgroundColor: C.bg },
    listContent: { padding: 16, gap: 10, maxWidth: 600, width: '100%', alignSelf: 'center' },
    empty:       { textAlign: 'center', color: C.textMuted, marginTop: 60, fontSize: 15 },
    row: {
      flexDirection: 'row',
      alignItems: 'center',
      backgroundColor: C.surface,
      borderRadius: 14,
      padding: 14,
      borderWidth: 1,
      borderColor: C.border,
      gap: 12,
    },
    rowMain: { flex: 1, gap: 4 },
    filename:    { fontSize: 15, fontWeight: '600', color: C.textPrimary },
    meta:        { fontSize: 12, color: C.textMuted },
    rowFailed:   { borderColor: C.error, backgroundColor: C.errorDim },
    errorBanner: { backgroundColor: C.errorDim, borderRadius: 10, padding: 12, marginBottom: 8 },
    errorText:   { color: C.error, fontSize: 13, textAlign: 'center' },
  });
}
