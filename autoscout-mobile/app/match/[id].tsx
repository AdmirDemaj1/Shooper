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
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { MaterialIcons } from '@expo/vector-icons';
import { Match, matchesApi } from '../../lib/api';

function scoreColor(score?: number): string {
  if (score === undefined) return '#999';
  if (score >= 75) return '#2E7D32';
  if (score >= 50) return '#F57C00';
  return '#C62828';
}

function DetailRow({ label, value }: { label: string; value?: string | number | null }) {
  if (!value) return null;
  return (
    <View style={styles.detailRow}>
      <Text style={styles.detailLabel}>{label}</Text>
      <Text style={styles.detailValue}>{value}</Text>
    </View>
  );
}

export default function MatchDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [match, setMatch] = useState<Match | null>(null);
  const [loading, setLoading] = useState(true);
  const [reasoningExpanded, setReasoningExpanded] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    if (!id) return;
    matchesApi
      .get(id)
      .then(setMatch)
      .catch(() => Alert.alert('Error', 'Could not load match details.'))
      .finally(() => setLoading(false));
  }, [id]);

  const handleAction = useCallback(
    async (action: 'saved' | 'dismissed') => {
      if (!match || actionLoading) return;
      setActionLoading(true);
      try {
        await matchesApi.recordAction(match.id, action);
        setMatch((prev) => prev ? { ...prev, user_action: action } : prev);
      } catch {
        Alert.alert('Error', 'Could not record action. Try again.');
      } finally {
        setActionLoading(false);
      }
    },
    [match, actionLoading]
  );

  const openListing = useCallback(() => {
    const url = match?.listing?.source_url;
    if (!url) return;
    if (url.includes('mock')) {
      Alert.alert('Demo listing', 'This is a demo listing — no real URL available yet.');
      return;
    }
    Linking.openURL(url).catch(() =>
      Alert.alert('Error', 'Could not open the listing URL.')
    );
  }, [match]);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#2E7D32" />
      </View>
    );
  }

  if (!match) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>Match not found.</Text>
      </View>
    );
  }

  const listing = match.listing;
  const title = listing?.title || match.summary || 'Car listing';
  const hasAction = !!match.user_action;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* ── Car icon placeholder (photo carousel in future) ── */}
      <View style={styles.photoBanner}>
        <MaterialIcons name="directions-car" size={64} color="#bbb" />
      </View>

      {/* ── Title + score ── */}
      <View style={styles.titleRow}>
        <Text style={styles.title} numberOfLines={3}>{title}</Text>
        {match.relevance_score !== undefined && (
          <View style={[styles.scoreBadge, { backgroundColor: scoreColor(match.relevance_score) }]}>
            <Text style={styles.scoreBadgeText}>{match.relevance_score}</Text>
          </View>
        )}
      </View>

      {/* ── Key specs ── */}
      <View style={styles.specsCard}>
        <DetailRow label="Price" value={listing?.price ? `€${listing.price}` : undefined} />
        <DetailRow label="Year" value={listing?.year} />
        <DetailRow
          label="Mileage"
          value={listing?.mileage ? `${listing.mileage.toLocaleString()} km` : undefined}
        />
        <DetailRow label="Location" value={listing?.location_text} />
        <DetailRow label="Make" value={listing?.make} />
        <DetailRow label="Model" value={listing?.model} />
      </View>

      {/* ── Description ── */}
      {listing?.description ? (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Description</Text>
          <Text style={styles.description}>{listing.description}</Text>
        </View>
      ) : null}

      {/* ── LLM Reasoning (collapsible) ── */}
      {match.llm_reasoning ? (
        <View style={styles.section}>
          <TouchableOpacity
            style={styles.reasoningHeader}
            onPress={() => setReasoningExpanded((v) => !v)}
            activeOpacity={0.7}
          >
            <Text style={styles.sectionTitle}>Why this match?</Text>
            <MaterialIcons
              name={reasoningExpanded ? 'expand-less' : 'expand-more'}
              size={20}
              color="#555"
            />
          </TouchableOpacity>
          {reasoningExpanded && (
            <Text style={styles.reasoning}>{match.llm_reasoning}</Text>
          )}
        </View>
      ) : null}

      {/* ── Open listing button ── */}
      {listing?.source_url ? (
        <TouchableOpacity style={styles.openButton} onPress={openListing} activeOpacity={0.8}>
          <MaterialIcons name="open-in-new" size={18} color="#fff" style={{ marginRight: 6 }} />
          <Text style={styles.openButtonText}>Open original listing</Text>
        </TouchableOpacity>
      ) : null}

      {/* ── Save / Dismiss actions ── */}
      <View style={styles.actionRow}>
        <TouchableOpacity
          style={[
            styles.actionButton,
            styles.dismissButton,
            match.user_action === 'dismissed' && styles.actionButtonActive,
          ]}
          onPress={() => handleAction('dismissed')}
          disabled={hasAction || actionLoading}
          activeOpacity={0.7}
        >
          <MaterialIcons
            name="thumb-down"
            size={18}
            color={match.user_action === 'dismissed' ? '#fff' : '#C62828'}
            style={{ marginRight: 4 }}
          />
          <Text
            style={[
              styles.actionButtonText,
              { color: match.user_action === 'dismissed' ? '#fff' : '#C62828' },
            ]}
          >
            Dismiss
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[
            styles.actionButton,
            styles.saveButton,
            match.user_action === 'saved' && styles.actionButtonActive,
          ]}
          onPress={() => handleAction('saved')}
          disabled={hasAction || actionLoading}
          activeOpacity={0.7}
        >
          <MaterialIcons
            name="bookmark"
            size={18}
            color={match.user_action === 'saved' ? '#fff' : '#2E7D32'}
            style={{ marginRight: 4 }}
          />
          <Text
            style={[
              styles.actionButtonText,
              { color: match.user_action === 'saved' ? '#fff' : '#2E7D32' },
            ]}
          >
            Save
          </Text>
        </TouchableOpacity>
      </View>

      {hasAction && (
        <Text style={styles.actionConfirm}>
          {match.user_action === 'saved' ? '✓ Saved' : '✓ Dismissed'}
        </Text>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
  },
  errorText: {
    color: '#888',
    fontSize: 16,
  },
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  content: {
    paddingBottom: 40,
  },
  photoBanner: {
    height: 200,
    backgroundColor: '#f5f5f5',
    justifyContent: 'center',
    alignItems: 'center',
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 8,
    gap: 12,
  },
  title: {
    flex: 1,
    fontSize: 19,
    fontWeight: '700',
    color: '#111',
  },
  scoreBadge: {
    borderRadius: 16,
    paddingHorizontal: 10,
    paddingVertical: 5,
    minWidth: 44,
    alignItems: 'center',
    flexShrink: 0,
  },
  scoreBadgeText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '800',
  },
  specsCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    backgroundColor: '#f9f9f9',
    borderRadius: 10,
    padding: 14,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#ddd',
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 5,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#eee',
  },
  detailLabel: {
    fontSize: 14,
    color: '#666',
  },
  detailValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#111',
  },
  section: {
    marginHorizontal: 16,
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#333',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 6,
  },
  description: {
    fontSize: 14,
    color: '#444',
    lineHeight: 21,
  },
  reasoningHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  reasoning: {
    marginTop: 6,
    fontSize: 13,
    color: '#555',
    fontStyle: 'italic',
    lineHeight: 19,
  },
  openButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#1565C0',
    marginHorizontal: 16,
    marginBottom: 16,
    padding: 13,
    borderRadius: 10,
  },
  openButtonText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '600',
  },
  actionRow: {
    flexDirection: 'row',
    marginHorizontal: 16,
    gap: 12,
    marginBottom: 8,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    borderRadius: 10,
    borderWidth: 1.5,
  },
  dismissButton: {
    borderColor: '#C62828',
    backgroundColor: '#fff',
  },
  saveButton: {
    borderColor: '#2E7D32',
    backgroundColor: '#fff',
  },
  actionButtonActive: {
    backgroundColor: '#2E7D32',
    borderColor: '#2E7D32',
  },
  actionButtonText: {
    fontSize: 15,
    fontWeight: '600',
  },
  actionConfirm: {
    textAlign: 'center',
    fontSize: 13,
    color: '#2E7D32',
    fontWeight: '600',
    marginTop: 4,
  },
});
