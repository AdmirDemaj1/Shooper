import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { MaterialIcons } from '@expo/vector-icons';
import { Match, matchesApi } from '../../lib/api';
import { useProfileStore } from '../../store/profileStore';

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatDateHeader(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / 86_400_000);
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return 'Earlier this week';
  return date.toLocaleDateString(undefined, { month: 'long', day: 'numeric' });
}

function scoreColor(score?: number): string {
  if (score === undefined) return '#999';
  if (score >= 75) return '#2E7D32';
  if (score >= 50) return '#F57C00';
  return '#C62828';
}

// ── Score chip ────────────────────────────────────────────────────────────────

function ScoreChip({ score }: { score?: number }) {
  if (score === undefined) return null;
  return (
    <View style={[styles.scoreChip, { backgroundColor: scoreColor(score) }]}>
      <Text style={styles.scoreText}>{score}</Text>
    </View>
  );
}

// ── Match row ─────────────────────────────────────────────────────────────────

function MatchRow({ match, profileName }: { match: Match; profileName?: string }) {
  const router = useRouter();
  const listing = match.listing;
  const title = listing?.title || match.summary || 'Car listing';
  const price = listing?.price ? `€${listing.price}` : '';
  const km = listing?.mileage ? `${(listing.mileage / 1000).toFixed(0)}k km` : '';
  const location = listing?.location_text || '';
  const subtitle = [price, km, location].filter(Boolean).join(' · ');

  return (
    <TouchableOpacity
      style={styles.matchRow}
      onPress={() => router.push(`/match/${match.id}`)}
      activeOpacity={0.7}
    >
      {/* Icon placeholder */}
      <View style={styles.thumbPlaceholder}>
        <MaterialIcons name="directions-car" size={28} color="#999" />
      </View>

      <View style={styles.matchContent}>
        <Text style={styles.matchTitle} numberOfLines={2}>{title}</Text>
        {subtitle ? <Text style={styles.matchSubtitle} numberOfLines={1}>{subtitle}</Text> : null}
        {profileName ? (
          <Text style={styles.profileLabel} numberOfLines={1}>
            <MaterialIcons name="search" size={11} color="#888" /> {profileName}
          </Text>
        ) : null}
        {match.llm_reasoning ? (
          <Text style={styles.reasoning} numberOfLines={2}>{match.llm_reasoning}</Text>
        ) : null}
      </View>

      <View style={styles.matchRight}>
        <ScoreChip score={match.relevance_score} />
        <MaterialIcons name="chevron-right" size={18} color="#ccc" style={{ marginTop: 6 }} />
      </View>
    </TouchableOpacity>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────

type ListItem =
  | { type: 'header'; date: string }
  | { type: 'match'; match: Match; profileName?: string };

export default function History() {
  const { profiles, fetch: fetchProfiles } = useProfileStore();
  const [items, setItems] = useState<ListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const profileMap = Object.fromEntries((profiles ?? []).map((p) => [p.id, p.name]));

  const loadMatches = useCallback(async () => {
    setError(null);
    try {
      const allMatches: Match[] = [];

      // Fetch matches for each active profile (up to 5 per profile)
      const activeProfiles = (profiles ?? []).filter((p) => p.is_active);
      await Promise.all(
        activeProfiles.map(async (p) => {
          try {
            const res = await matchesApi.listForProfile(p.id);
            allMatches.push(...res.matches);
          } catch {
            // One failing profile shouldn't block the rest
          }
        })
      );

      // Sort newest first
      allMatches.sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );

      // Group by date header
      const grouped: ListItem[] = [];
      let lastHeader = '';
      for (const match of allMatches) {
        const header = formatDateHeader(match.created_at);
        if (header !== lastHeader) {
          grouped.push({ type: 'header', date: header });
          lastHeader = header;
        }
        grouped.push({ type: 'match', match, profileName: profileMap[match.search_profile_id] });
      }

      setItems(grouped);
    } catch (e: any) {
      setError('Could not load matches. Pull down to retry.');
    }
  }, [profiles]);

  useEffect(() => {
    // Ensure profiles are loaded before fetching matches
    if (profiles.length === 0) {
      fetchProfiles().then(() => loadMatches()).finally(() => setLoading(false));
    } else {
      loadMatches().finally(() => setLoading(false));
    }
  }, []);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadMatches();
    setRefreshing(false);
  }, [loadMatches]);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#2E7D32" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centered}>
        <MaterialIcons name="error-outline" size={40} color="#ccc" />
        <Text style={styles.emptyTitle}>{error}</Text>
      </View>
    );
  }

  if (items.length === 0) {
    return (
      <View style={styles.centered}>
        <MaterialIcons name="history" size={48} color="#ccc" />
        <Text style={styles.emptyTitle}>No matches yet</Text>
        <Text style={styles.emptySubtitle}>
          Matches will appear here once your searches run
        </Text>
      </View>
    );
  }

  return (
    <FlatList
      data={items}
      keyExtractor={(item, idx) =>
        item.type === 'header' ? `header-${idx}` : item.match.id
      }
      renderItem={({ item }) => {
        if (item.type === 'header') {
          return <Text style={styles.dateHeader}>{item.date}</Text>;
        }
        return <MatchRow match={item.match} profileName={item.profileName} />;
      }}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#2E7D32" />}
      contentContainerStyle={styles.list}
    />
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
    backgroundColor: '#fff',
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginTop: 12,
    textAlign: 'center',
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#888',
    marginTop: 6,
    textAlign: 'center',
  },
  list: {
    paddingBottom: 24,
    backgroundColor: '#fff',
  },
  dateHeader: {
    paddingHorizontal: 16,
    paddingTop: 20,
    paddingBottom: 6,
    fontSize: 13,
    fontWeight: '700',
    color: '#555',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    backgroundColor: '#f7f7f7',
  },
  matchRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#eee',
    backgroundColor: '#fff',
  },
  thumbPlaceholder: {
    width: 52,
    height: 52,
    borderRadius: 8,
    backgroundColor: '#f0f0f0',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
    flexShrink: 0,
  },
  matchContent: {
    flex: 1,
    marginRight: 8,
  },
  matchTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#111',
    marginBottom: 2,
  },
  matchSubtitle: {
    fontSize: 13,
    color: '#555',
    marginBottom: 2,
  },
  profileLabel: {
    fontSize: 11,
    color: '#888',
    marginBottom: 3,
  },
  reasoning: {
    fontSize: 12,
    color: '#777',
    fontStyle: 'italic',
    marginTop: 2,
  },
  matchRight: {
    alignItems: 'flex-end',
    flexShrink: 0,
  },
  scoreChip: {
    borderRadius: 12,
    paddingHorizontal: 8,
    paddingVertical: 3,
    minWidth: 36,
    alignItems: 'center',
  },
  scoreText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '700',
  },
});

