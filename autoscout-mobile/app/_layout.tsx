import { Stack, useRouter, useRootNavigationState } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect } from 'react';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '../lib/firebase';
import { useAuthStore } from '../store/authStore';

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const router = useRouter();
  const rootNavigationState = useRootNavigationState();
  const { isLoading, restoreSession, user } = useAuthStore();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        try {
          const token = await firebaseUser.getIdToken();
          useAuthStore.setState({ user: firebaseUser, token });
        } catch (error) {
          console.error('Error getting token:', error);
        }
      } else {
        useAuthStore.setState({ user: null, token: null });
      }
    });

    return () => unsubscribe();
  }, []);

  // Wait for root navigation to be ready before routing
  useEffect(() => {
    if (!rootNavigationState?.key) return;

    if (user) {
      router.replace('/(tabs)/searches');
    } else {
      router.replace('/(auth)/signup');
    }

    SplashScreen.hideAsync();
  }, [rootNavigationState?.key, user, router]);

  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="(auth)" />
      <Stack.Screen name="(tabs)" />
      <Stack.Screen name="profile-form" options={{ headerShown: true, presentation: 'card' }} />
      <Stack.Screen name="match/[id]" options={{ headerShown: true, title: 'Match Detail', presentation: 'card' }} />
    </Stack>
  );
}
