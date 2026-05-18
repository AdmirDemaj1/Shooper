import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Image,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { MaterialIcons } from '@expo/vector-icons';
import { PlatformListing, platformListingsApi } from '../../lib/api';

function priceLabel(listing: PlatformListing): string {
  const sym = listing.currency === 'ALL' ? 'L' : '€';
  return listing.price ? `${sym}${Number(listing.price).toLocaleString()}` : '';
}

function ListingCard({ item }: { item: PlatformListing }) {
  const router = useRouter();
  const thumb = item.photo_urls?.[0];
  const km = item.mileage ? `${(item.mileage / 1000).toFixed(0)}k km` : '';
  const subtitle = [priceLabel(item), km, item.location_text].filter(Boolean).join(' · ');

  return (
    <TouchableOpacity
      style={styles.card}
      onPress={() => router.push(`/listing/${item.id}`)}
      activeOpacity={0.8}
    >
      <View style={styles.thumb}>
        {thumb ? (
          <Image source={{ uri: thumb }} style={styles.thumbImg} resizeMode="cover" />
        ) : (
          <MaterialIcons name="directions-car" size={32} color="#bbb" />
        )}
      </View>
      <View style={styles.cardBody}>
        <Text style={styles.cardTitle} numberOfLines={2}>{item.title || `${item.make} ${item.model}`}</Text>
        {subtitle ? <Text style={styles.cardSub} numberOfLines={1}>{subtitle}</Text> : null}
        {item.year ? <Text style={styles.cardYear}>{item.year}</Text> : null}
      </View>
      <MaterialIcons name="chevron-right" size={20} color="#ccc" />
    </TouchableOpacity>
  );
}

export default function Browse() {
  const router = useRouter();
  const [listings, setListings] = useState<PlatformListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [cursor, setCursor] = useState<string | undefined>();
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [makeFilter, setMakeFilter] = useState('');
  const [appliedMake, setAppliedMake] = useState('');

  const load = useCallback(async (reset = false) => {
    try {
      const params: Record<string, any> = { limit: 20 };
      if (appliedMake) params.make = appliedMake;
      if (!reset && cursor) params.cursor = cursor;

      const res = await platformListingsApi.browse(params);
      setListings((prev) => (reset ? res.listings : [...prev, ...res.listings]));
      setHasMore(res.has_more);
      setCursor(res.next_cursor);
    } catch {
      // keep existing listings on error
    }
  }, [appliedMake, cursor]);

  useEffect(() => {
    setLoading(true);
    setCursor(undefined);
    platformListingsApi.browse({ limit: 20, ...(appliedMake ? { make: appliedMake } : {}) })
      .then((res) => {
        setListings(res.listings);
        setHasMore(res.has_more);
        setCursor(res.next_cursor);
      })
      .finally(() => setLoading(false));
  }, [appliedMake]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    setCursor(undefined);
    try {
      const res = await platformListingsApi.browse({ limit: 20, ...(appliedMake ? { make: appliedMake } : {}) });
      setListings(res.listings);
      setHasMore(res.has_more);
      setCursor(res.next_cursor);
    } finally {
      setRefreshing(false);
    }
  }, [appliedMake]);

  const loadMore = useCallback(async () => {
    if (!hasMore || loadingMore || !cursor) return;
    setLoadingMore(true);
    try {
      const res = await platformListingsApi.browse({ limit: 20, cursor, ...(appliedMake ? { make: appliedMake } : {}) });
      setListings((prev) => [...prev, ...res.listings]);
      setHasMore(res.has_more);
      setCursor(res.next_cursor);
    } finally {
      setLoadingMore(false);
    }
  }, [hasMore, loadingMore, cursor, appliedMake]);

  return (
    <View style={styles.container}>
      {/* Filter bar */}
      <View style={styles.filterBar}>
        <View style={styles.searchBox}>
          <MaterialIcons name="search" size={18} color="#888" />
          <TextInput
            style={styles.searchInput}
            placeholder="Make (e.g. BMW)"
            value={makeFilter}
            onChangeText={setMakeFilter}
            onSubmitEditing={() => setAppliedMake(makeFilter.trim())}
            returnKeyType="search"
            autoCapitalize="words"
          />
          {makeFilter ? (
            <TouchableOpacity onPress={() => { setMakeFilter(''); setAppliedMake(''); }}>
              <MaterialIcons name="close" size={16} color="#888" />
            </TouchableOpacity>
          ) : null}
        </View>
      </View>

      {loading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color="#2E7D32" />
        </View>
      ) : listings.length === 0 ? (
        <View style={styles.centered}>
          <MaterialIcons name="storefront" size={48} color="#ccc" />
          <Text style={styles.emptyTitle}>No listings yet</Text>
          <Text style={styles.emptySub}>Be the first to post a car for sale</Text>
          <TouchableOpacity style={styles.postBtn} onPress={() => router.push('/post-listing')}>
            <MaterialIcons name="add" size={18} color="#fff" />
            <Text style={styles.postBtnText}>Post a listing</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={listings}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <ListingCard item={item} />}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#2E7D32" />}
          onEndReached={loadMore}
          onEndReachedThreshold={0.3}
          ListFooterComponent={loadingMore ? <ActivityIndicator color="#2E7D32" style={{ margin: 16 }} /> : null}
          contentContainerStyle={styles.list}
        />
      )}

      {/* FAB */}
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
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 32 },
  filterBar: { backgroundColor: '#fff', paddingHorizontal: 16, paddingVertical: 10, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: '#eee' },
  searchBox: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#f0f0f0', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 7, gap: 6 },
  searchInput: { flex: 1, fontSize: 14, color: '#111' },
  list: { paddingBottom: 80 },
  card: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', marginHorizontal: 12, marginTop: 10, borderRadius: 10, padding: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 3, elevation: 1 },
  thumb: { width: 64, height: 64, borderRadius: 8, backgroundColor: '#f0f0f0', justifyContent: 'center', alignItems: 'center', marginRight: 12, overflow: 'hidden', flexShrink: 0 },
  thumbImg: { width: 64, height: 64 },
  cardBody: { flex: 1 },
  cardTitle: { fontSize: 15, fontWeight: '600', color: '#111', marginBottom: 2 },
  cardSub: { fontSize: 13, color: '#555' },
  cardYear: { fontSize: 12, color: '#888', marginTop: 2 },
  emptyTitle: { fontSize: 18, fontWeight: '600', color: '#333', marginTop: 12 },
  emptySub: { fontSize: 14, color: '#888', marginTop: 6, marginBottom: 24, textAlign: 'center' },
  postBtn: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#2E7D32', paddingVertical: 12, paddingHorizontal: 20, borderRadius: 8, gap: 6 },
  postBtnText: { color: '#fff', fontSize: 15, fontWeight: '600' },
  fab: { position: 'absolute', bottom: 24, right: 20, width: 52, height: 52, borderRadius: 26, backgroundColor: '#2E7D32', justifyContent: 'center', alignItems: 'center', shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.2, shadowRadius: 4, elevation: 4 },
});
