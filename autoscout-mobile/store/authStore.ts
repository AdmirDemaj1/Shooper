import { create } from 'zustand';
import { User } from 'firebase/auth';
import { ConfirmationResult } from 'firebase/auth';
import * as SecureStore from 'expo-secure-store';
import { auth } from '../lib/firebase';

interface AuthStore {
  user: User | null;
  token: string | null;
  confirmationResult: ConfirmationResult | null;
  isLoading: boolean;
  setConfirmationResult: (result: ConfirmationResult | null) => void;
  setUser: (user: User | null, token: string | null) => Promise<void>;
  logout: () => Promise<void>;
  restoreSession: () => Promise<void>;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: null,
  confirmationResult: null,
  isLoading: true,

  setConfirmationResult: (result) => set({ confirmationResult: result }),

  setUser: async (user, token) => {
    set({ user, token });
    if (token) {
      await SecureStore.setItemAsync('firebase_token', token);
    }
  },

  logout: async () => {
    await auth.signOut();
    await SecureStore.deleteItemAsync('firebase_token');
    set({ user: null, token: null, confirmationResult: null });
  },

  restoreSession: async () => {
    try {
      const token = await SecureStore.getItemAsync('firebase_token');
      if (token) {
        set({ token, user: auth.currentUser });
      }
    } catch (error) {
      console.error('Error restoring session:', error);
    } finally {
      set({ isLoading: false });
    }
  },
}));
