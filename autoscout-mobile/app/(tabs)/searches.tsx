import React, { useEffect, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  Switch,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { useRouter } from 'expo-router';
import { MaterialIcons } from '@expo/vector-icons';
import { useProfileStore } from '../../store/profileStore';
import { SearchProfile } from '../../lib/api';

function profileSummary(p: SearchProfile): string {
  const parts: string[] = [];
  if (p.make || p.model) parts.push([p.make, p.model].filter(Boolean).join(' '));
  if (p.year_min || p.year_max) {
    parts.push(p.year_min && p.year_max ? `${p.year_min}–${p.year_max}` : `from ${p.year_min ?? p.year_max}`);
  }
  if (p.price_max) parts.push(`max ${p.currency === 'ALL' ? 'L' : '€'}${p.price_max.toLocaleString()}`);
  if (p.mileage_max) parts.push(`<${(p.mileage_max / 1000).toFixed(0)}k km`);
  return parts.join(' · ') || 'No filters set';
}

function ProfileCard({ profile }: { profile: SearchProfile }) {
  const { toggle, remove } = useProfileStore();
  const router = useRouter();

  function confirmDelete() {
    Alert.alert('Delete search?', `"${profile.name}" will be permanently removed.`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: () => remove(profile.id) },
    ]);
  }

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Text style={styles.cardName} numberOfLines={1}>{profile.name}</Text>
        <Switch
          value={profile.is_active}
          onValueChange={() => toggle(profile.id)}
          trackColor={{ true: '#2E7D32' }}
          thumbColor="#fff"
        />
      </View>
      <Text style={styles.cardSummary}>{profileSummary(profile)}</Text>
      <View style={styles.cardActions}>
        <TouchableOpacity
          style={styles.actionBtn}
          onPress={() => router.push({ pathname: '/profile-form', params: { id: profile.id } })}
        >
          <MaterialIcons name="edit" size={16} color="#2E7D32" />
          <Text style={styles.actionBtnText}>Edit</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.actionBtn, styles.deleteBtn]} onPress={confirmDelete}>
          <MaterialIcons name="delete-outline" size={16} color="#c62828" />
          <Text style={[styles.actionBtnText, styles.deleteBtnText]}>Delete</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

export default function Searches() {
  const router = useRouter();
  const { profiles, loading, fetch } = useProfileStore();

  useEffect(() => { fetch(); }, []);

  const onRefresh = useCallback(() => fetch(), [fetch]);

  if (loading && profiles.length === 0) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#2E7D32" />
      </View>
    );
  }

  if (profiles.length === 0) {
    return (
      <View style={styles.centered}>
        <MaterialIcons name="search" size={48} color="#ccc" />
        <Text style={styles.emptyTitle}>No searches yet</Text>
        <Text style={styles.emptySubtitle}>
          Tell us what car you're looking for and we'll find matches daily
        </Text>
        <View style={styles.emptyButtons}>
          <TouchableOpacity
            style={styles.primaryBtn}
            onPress={() => router.push('/profile-form')}
          >
            <MaterialIcons name="add" size={18} color="#fff" />
            <Text style={styles.primaryBtnText}>New Search</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.secondaryBtn}
            onPress={() => router.push({ pathname: '/profile-form', params: { mode: 'nl' } })}
          >
            <MaterialIcons name="chat-bubble-outline" size={18} color="#2E7D32" />
            <Text style={styles.secondaryBtnText}>Describe in words</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={profiles}
        keyExtractor={(p) => p.id}
        renderItem={({ item }) => <ProfileCard profile={item} />}
        contentContainerStyle={styles.list}
        onRefresh={onRefresh}
        refreshing={loading}
      />
      <View style={styles.fab}>
        <TouchableOpacity
          style={styles.primaryBtn}
          onPress={() => router.push('/profile-form')}
        >
          <MaterialIcons name="add" size={18} color="#fff" />
          <Text style={styles.primaryBtnText}>New Search</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.secondaryBtn}
          onPress={() => router.push({ pathname: '/profile-form', params: { mode: 'nl' } })}
        >
          <MaterialIcons name="chat-bubble-outline" size={18} color="#2E7D32" />
          <Text style={styles.secondaryBtnText}>Describe in words</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 32, backgroundColor: '#fff' },
  list: { padding: 16, paddingBottom: 120 },

  // Empty state
  emptyTitle: { fontSize: 18, fontWeight: '600', color: '#000', marginTop: 16, marginBottom: 8, textAlign: 'center' },
  emptySubtitle: { fontSize: 14, color: '#666', textAlign: 'center', marginBottom: 32, lineHeight: 20 },
  emptyButtons: { gap: 12, width: '100%' },

  // Buttons
  primaryBtn: { backgroundColor: '#2E7D32', paddingVertical: 13, paddingHorizontal: 20, borderRadius: 8, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 },
  primaryBtnText: { color: '#fff', fontSize: 15, fontWeight: '600' },
  secondaryBtn: { borderWidth: 1.5, borderColor: '#2E7D32', paddingVertical: 13, paddingHorizontal: 20, borderRadius: 8, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 },
  secondaryBtnText: { color: '#2E7D32', fontSize: 15, fontWeight: '600' },

  // FAB area at bottom
  fab: { position: 'absolute', bottom: 24, left: 16, right: 16, gap: 10 },

  // Card
  card: { backgroundColor: '#fff', borderRadius: 10, padding: 16, marginBottom: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.06, shadowRadius: 4, elevation: 2 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  cardName: { fontSize: 16, fontWeight: '600', color: '#111', flex: 1, marginRight: 8 },
  cardSummary: { fontSize: 13, color: '#666', marginBottom: 12 },
  cardActions: { flexDirection: 'row', gap: 8 },
  actionBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingVertical: 6, paddingHorizontal: 10, borderRadius: 6, borderWidth: 1, borderColor: '#2E7D32' },
  actionBtnText: { fontSize: 13, color: '#2E7D32', fontWeight: '500' },
  deleteBtn: { borderColor: '#c62828' },
  deleteBtnText: { color: '#c62828' },
});
