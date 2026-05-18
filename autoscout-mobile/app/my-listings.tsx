import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Image,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { MaterialIcons } from '@expo/vector-icons';
import { PlatformListing, platformListingsApi } from '../lib/api';

const STATUS_COLORS: Record<string, string> = {
  active: '#2E7D32',
  sold: '#888',
  removed: '#c62828',
  expired: '#F57C00',
};

function ListingRow({ item }: { item: PlatformListing }) {
  const router = useRouter();
  const thumb = item.photo_urls?.[0];
  const price = item.price
    ? `${item.currency === 'ALL' ? 'L' : '€'}${Number(item.price).toLocaleString()}`
    : '—';

  return (
    <TouchableOpacity
      style={styles.row}
      onPress={() => router.push(`/listing/${item.id}`)}
      activeOpacity={0.8}
    >
      <View style={styles.thumb}>
        {thumb ? (
          <Image source={{ uri: thumb }} style={styles.thumbImg} resizeMode="cover" />
        ) : (
          <MaterialIcons name="directions-car" size={28} color="#bbb" />
        )}
      </View>
      <View style={styles.rowBody}>
        <Text style={styles.rowTitle} numberOfLines={2}>{item.title}</Text>
        <Text style={styles.rowPrice}>{price}</Text>
        <View style={styles.statusRow}>
          <View style={[styles.statusDot, { backgroundColor: STATUS_COLORS[item.status] || '#888' }]} />
          <Text style={[styles.statusText, { color: STATUS_COLORS[item.status] || '#888' }]}>
            {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
          </Text>
          <Text style={styles.viewsText}> · {item.views_count} views</Text>
        </View>
      </View>
      <MaterialIcons name="chevron-right" size={20} color="#ccc" />
    </TouchableOpacity>
  );
}

export default function MyListings() {
  const router = useRouter();
  const [listings, setListings] = useState<PlatformListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await platformListingsApi.myListings();
      setListings(data);
    } catch {
      // keep existing
    }
  }, []);

  useEffect(() => {
    load().finally(() => setLoading(false));
  }, []);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#2E7D32" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {listings.length === 0 ? (
        <View style={styles.centered}>
          <MaterialIcons name="post-add" size={48} color="#ccc" />
          <Text style={styles.emptyTitle}>No listings yet</Text>
          <Text style={styles.emptySub}>Cars you post for sale will appear here</Text>
          <TouchableOpacity style={styles.postBtn} onPress={() => router.push('/post-listing')}>
            <MaterialIcons name="add" size={18} color="#fff" />
            <Text style={styles.postBtnText}>Post a listing</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={listings}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <ListingRow item={item} />}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#2E7D32" />}
          contentContainerStyle={styles.list}
        />
      )}
      {listings.length > 0 && (
        <TouchableOpacity style={styles.fab} onPress={() => router.push('/post-listing')}>
          <MaterialIcons name="add" size={24} color="#fff" />
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 32, backgroundColor: '#fff' },
  list: { paddingBottom: 80 },
  row: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', marginHorizontal: 12, marginTop: 10, borderRadius: 10, padding: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 3, elevation: 1 },
  thumb: { width: 64, height: 64, borderRadius: 8, backgroundColor: '#f0f0f0', justifyContent: 'center', alignItems: 'center', marginRight: 12, overflow: 'hidden', flexShrink: 0 },
  thumbImg: { width: 64, height: 64 },
  rowBody: { flex: 1 },
  rowTitle: { fontSize: 14, fontWeight: '600', color: '#111', marginBottom: 2 },
  rowPrice: { fontSize: 15, fontWeight: '700', color: '#2E7D32', marginBottom: 4 },
  statusRow: { flexDirection: 'row', alignItems: 'center' },
  statusDot: { width: 7, height: 7, borderRadius: 4, marginRight: 5 },
  statusText: { fontSize: 12, fontWeight: '600' },
  viewsText: { fontSize: 12, color: '#888' },
  emptyTitle: { fontSize: 18, fontWeight: '600', color: '#333', marginTop: 12 },
  emptySub: { fontSize: 14, color: '#888', marginTop: 6, marginBottom: 24, textAlign: 'center' },
  postBtn: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#2E7D32', paddingVertical: 12, paddingHorizontal: 20, borderRadius: 8, gap: 6 },
  postBtnText: { color: '#fff', fontSize: 15, fontWeight: '600' },
  fab: { position: 'absolute', bottom: 24, right: 20, width: 52, height: 52, borderRadius: 26, backgroundColor: '#2E7D32', justifyContent: 'center', alignItems: 'center', shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.2, shadowRadius: 4, elevation: 4 },
});
