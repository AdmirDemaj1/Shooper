import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Linking,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  Image,
  Dimensions,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { MaterialIcons } from '@expo/vector-icons';
import { PlatformListing, platformListingsApi } from '../../lib/api';
import { useAuthStore } from '../../store/authStore';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

function SpecRow({ label, value }: { label: string; value?: string | number | null }) {
  if (!value) return null;
  return (
    <View style={styles.specRow}>
      <Text style={styles.specLabel}>{label}</Text>
      <Text style={styles.specValue}>{value}</Text>
    </View>
  );
}

export default function ListingDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuthStore();
  const [listing, setListing] = useState<PlatformListing | null>(null);
  const [loading, setLoading] = useState(true);
  const [photoIndex, setPhotoIndex] = useState(0);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    if (!id) return;
    platformListingsApi
      .get(id)
      .then(setListing)
      .catch(() => Alert.alert('Error', 'Could not load listing.'))
      .finally(() => setLoading(false));
  }, [id]);

  const isOwner = listing && user && listing.seller_user_id === (user as any)?.uid;

  const openWhatsApp = useCallback(() => {
    if (!listing?.contact_phone) return;
    const phone = listing.contact_phone.replace(/\D/g, '');
    const text = encodeURIComponent(`Hi, I saw your listing on AutoScout: ${listing.title}`);
    Linking.openURL(`whatsapp://send?phone=${phone}&text=${text}`).catch(() =>
      Alert.alert('WhatsApp not found', 'Make sure WhatsApp is installed.')
    );
  }, [listing]);

  const markSold = useCallback(async () => {
    if (!listing) return;
    Alert.alert('Mark as sold?', 'This will hide the listing from Browse.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Mark sold',
        onPress: async () => {
          setActionLoading(true);
          try {
            const updated = await platformListingsApi.update(listing.id, { status: 'sold' });
            setListing(updated);
          } catch {
            Alert.alert('Error', 'Could not update listing.');
          } finally {
            setActionLoading(false);
          }
        },
      },
    ]);
  }, [listing]);

  const deleteListing = useCallback(async () => {
    if (!listing) return;
    Alert.alert('Delete listing?', 'This cannot be undone.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          setActionLoading(true);
          try {
            await platformListingsApi.remove(listing.id);
            router.back();
          } catch {
            Alert.alert('Error', 'Could not delete listing.');
            setActionLoading(false);
          }
        },
      },
    ]);
  }, [listing, router]);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#2E7D32" />
      </View>
    );
  }

  if (!listing) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>Listing not found.</Text>
      </View>
    );
  }

  const photos = listing.photo_urls || [];
  const price = listing.price
    ? `${listing.currency === 'ALL' ? 'L' : '€'}${Number(listing.price).toLocaleString()}`
    : null;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Photo carousel */}
      {photos.length > 0 ? (
        <View>
          <ScrollView
            horizontal
            pagingEnabled
            showsHorizontalScrollIndicator={false}
            onMomentumScrollEnd={(e) => {
              setPhotoIndex(Math.round(e.nativeEvent.contentOffset.x / SCREEN_WIDTH));
            }}
          >
            {photos.map((uri, i) => (
              <Image key={i} source={{ uri }} style={styles.photo} resizeMode="cover" />
            ))}
          </ScrollView>
          {photos.length > 1 && (
            <View style={styles.photoDots}>
              {photos.map((_, i) => (
                <View key={i} style={[styles.dot, i === photoIndex && styles.dotActive]} />
              ))}
            </View>
          )}
        </View>
      ) : (
        <View style={styles.photoPlaceholder}>
          <MaterialIcons name="directions-car" size={64} color="#bbb" />
        </View>
      )}

      {/* Status badge for sold listings */}
      {listing.status === 'sold' && (
        <View style={styles.soldBanner}>
          <Text style={styles.soldBannerText}>SOLD</Text>
        </View>
      )}

      {/* Title + price */}
      <View style={styles.titleRow}>
        <Text style={styles.title}>{listing.title}</Text>
        {price && <Text style={styles.price}>{price}</Text>}
      </View>

      {/* Specs */}
      <View style={styles.specsCard}>
        <SpecRow label="Year" value={listing.year} />
        <SpecRow label="Mileage" value={listing.mileage ? `${listing.mileage.toLocaleString()} km` : null} />
        <SpecRow label="Location" value={listing.location_text} />
        <SpecRow label="Transmission" value={listing.transmission} />
        <SpecRow label="Fuel" value={listing.fuel_type} />
        <SpecRow label="Body" value={listing.body_type} />
        <SpecRow label="Views" value={listing.views_count} />
      </View>

      {/* Description */}
      {listing.description ? (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Description</Text>
          <Text style={styles.description}>{listing.description}</Text>
        </View>
      ) : null}

      {/* Actions */}
      {!isOwner && listing.contact_phone && listing.status === 'active' && (
        <TouchableOpacity style={styles.whatsappBtn} onPress={openWhatsApp}>
          <MaterialIcons name="chat" size={20} color="#fff" />
          <Text style={styles.whatsappBtnText}>Contact seller on WhatsApp</Text>
        </TouchableOpacity>
      )}

      {isOwner && (
        <View style={styles.ownerActions}>
          <TouchableOpacity
            style={styles.editBtn}
            onPress={() => router.push({ pathname: '/post-listing', params: { edit: listing.id } })}
            disabled={actionLoading}
          >
            <MaterialIcons name="edit" size={16} color="#2E7D32" />
            <Text style={styles.editBtnText}>Edit</Text>
          </TouchableOpacity>
          {listing.status === 'active' && (
            <TouchableOpacity style={styles.soldBtn} onPress={markSold} disabled={actionLoading}>
              <MaterialIcons name="check-circle" size={16} color="#F57C00" />
              <Text style={styles.soldBtnText}>Mark sold</Text>
            </TouchableOpacity>
          )}
          <TouchableOpacity style={styles.deleteBtn} onPress={deleteListing} disabled={actionLoading}>
            <MaterialIcons name="delete-outline" size={16} color="#c62828" />
            <Text style={styles.deleteBtnText}>Delete</Text>
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#fff' },
  errorText: { color: '#888', fontSize: 16 },
  container: { flex: 1, backgroundColor: '#fff' },
  content: { paddingBottom: 40 },
  photo: { width: SCREEN_WIDTH, height: 240 },
  photoPlaceholder: { height: 200, backgroundColor: '#f5f5f5', justifyContent: 'center', alignItems: 'center' },
  photoDots: { flexDirection: 'row', justifyContent: 'center', paddingVertical: 8, gap: 5 },
  dot: { width: 7, height: 7, borderRadius: 4, backgroundColor: '#ccc' },
  dotActive: { backgroundColor: '#2E7D32', width: 18 },
  soldBanner: { backgroundColor: '#c62828', paddingVertical: 8, alignItems: 'center' },
  soldBannerText: { color: '#fff', fontWeight: '800', fontSize: 15, letterSpacing: 2 },
  titleRow: { paddingHorizontal: 16, paddingTop: 16, paddingBottom: 4 },
  title: { fontSize: 20, fontWeight: '700', color: '#111', marginBottom: 4 },
  price: { fontSize: 22, fontWeight: '800', color: '#2E7D32' },
  specsCard: { marginHorizontal: 16, marginVertical: 12, backgroundColor: '#f9f9f9', borderRadius: 10, padding: 14, borderWidth: StyleSheet.hairlineWidth, borderColor: '#ddd' },
  specRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 5, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: '#eee' },
  specLabel: { fontSize: 14, color: '#666' },
  specValue: { fontSize: 14, fontWeight: '600', color: '#111', textTransform: 'capitalize' },
  section: { marginHorizontal: 16, marginBottom: 16 },
  sectionTitle: { fontSize: 13, fontWeight: '700', color: '#555', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 },
  description: { fontSize: 14, color: '#444', lineHeight: 21 },
  whatsappBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#25D366', marginHorizontal: 16, marginBottom: 16, padding: 14, borderRadius: 10, gap: 8 },
  whatsappBtnText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  ownerActions: { flexDirection: 'row', marginHorizontal: 16, gap: 8, marginBottom: 16, flexWrap: 'wrap' },
  editBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingVertical: 9, paddingHorizontal: 14, borderRadius: 8, borderWidth: 1, borderColor: '#2E7D32' },
  editBtnText: { fontSize: 14, color: '#2E7D32', fontWeight: '500' },
  soldBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingVertical: 9, paddingHorizontal: 14, borderRadius: 8, borderWidth: 1, borderColor: '#F57C00' },
  soldBtnText: { fontSize: 14, color: '#F57C00', fontWeight: '500' },
  deleteBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingVertical: 9, paddingHorizontal: 14, borderRadius: 8, borderWidth: 1, borderColor: '#c62828' },
  deleteBtnText: { fontSize: 14, color: '#c62828', fontWeight: '500' },
});
