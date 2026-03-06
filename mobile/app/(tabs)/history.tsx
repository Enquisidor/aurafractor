/**
 * History screen — paginated list of uploaded tracks with extraction summaries.
 */

import { router } from 'expo-router';
import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { user as userApi, TrackSummary } from '../../src/api/client';
import { ErrorView } from '../../src/components/ErrorView';
import { StatusBadge } from '../../src/components/StatusBadge';

const PAGE_SIZE = 20;

export default function HistoryScreen() {
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
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load history');
    }
  }, []);

  useEffect(() => {
    load(0, true).finally(() => setLoading(false));
  }, [load]);

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

  if (loading) return <ActivityIndicator style={styles.centered} size="large" color="#6366F1" />;
  if (error) return <ErrorView message={error} />;

  return (
    <FlatList
      data={tracks}
      keyExtractor={(t) => t.track_id}
      contentContainerStyle={styles.list}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#6366F1" />}
      onEndReached={onEndReached}
      onEndReachedThreshold={0.2}
      ListEmptyComponent={<Text style={styles.empty}>No tracks yet. Upload one!</Text>}
      ListFooterComponent={loadingMore ? <ActivityIndicator color="#6366F1" /> : null}
      renderItem={({ item }) => <TrackRow track={item} />}
    />
  );
}

function TrackRow({ track }: { track: TrackSummary }) {
  const latest = track.latest_extraction;
  return (
    <Pressable
      style={styles.row}
      onPress={() => latest && router.push(`/extraction/${latest.extraction_id}`)}
      disabled={!latest}
    >
      <View style={styles.rowMain}>
        <Text style={styles.filename} numberOfLines={1}>{track.filename}</Text>
        <Text style={styles.meta}>
          {new Date(track.uploaded_at).toLocaleDateString()} · {track.extractions_count} extraction{track.extractions_count !== 1 ? 's' : ''}
        </Text>
      </View>
      {latest && (
        <StatusBadge status={latest.status as Parameters<typeof StatusBadge>[0]['status']} />
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  centered: { flex: 1 },
  list: { padding: 16, gap: 10 },
  empty: { textAlign: 'center', color: '#94A3B8', marginTop: 60, fontSize: 15 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F8FAFC',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    gap: 12,
  },
  rowMain: { flex: 1, gap: 4 },
  filename: { fontSize: 15, fontWeight: '600', color: '#1E293B' },
  meta: { fontSize: 12, color: '#94A3B8' },
});
