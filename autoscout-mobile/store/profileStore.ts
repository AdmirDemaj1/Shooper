import { create } from 'zustand';
import { profilesApi, SearchProfile, SearchProfileCreate } from '../lib/api';

interface ProfileStore {
  profiles: SearchProfile[];
  loading: boolean;
  fetch: () => Promise<void>;
  create: (data: Partial<SearchProfileCreate>) => Promise<SearchProfile>;
  update: (id: string, data: Partial<SearchProfileCreate>) => Promise<void>;
  remove: (id: string) => Promise<void>;
  toggle: (id: string) => Promise<void>;
}

export const useProfileStore = create<ProfileStore>((set, get) => ({
  profiles: [],
  loading: false,

  fetch: async () => {
    set({ loading: true });
    try {
      const profiles = await profilesApi.list();
      set({ profiles });
    } catch (e) {
      console.error('Failed to fetch profiles', e);
    } finally {
      set({ loading: false });
    }
  },

  create: async (data) => {
    const profile = await profilesApi.create(data);
    await get().fetch();
    return profile;
  },

  update: async (id, data) => {
    await profilesApi.update(id, data);
    await get().fetch();
  },

  remove: async (id) => {
    await profilesApi.remove(id);
    set((s) => ({ profiles: s.profiles.filter((p) => p.id !== id) }));
  },

  toggle: async (id) => {
    const updated = await profilesApi.toggle(id);
    set((s) => ({ profiles: s.profiles.map((p) => (p.id === id ? updated : p)) }));
  },
}));
