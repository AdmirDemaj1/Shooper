import React, { useState } from 'react';
import {
  View,
  TextInput,
  TouchableOpacity,
  Text,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useAuthStore } from '../../store/authStore';
import { syncUser } from '../../lib/api';

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 20,
    backgroundColor: '#fff',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#000',
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    marginBottom: 30,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    paddingHorizontal: 15,
    paddingVertical: 12,
    marginBottom: 15,
    borderRadius: 8,
    fontSize: 16,
    textAlign: 'center',
    letterSpacing: 2,
    color: '#000',
  },
  button: {
    backgroundColor: '#2E7D32',
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 10,
  },
  buttonDisabled: {
    backgroundColor: '#ccc',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default function OTP() {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { phone } = useLocalSearchParams();
  const { confirmationResult, setUser } = useAuthStore();

  const handleVerify = async () => {
    if (code.length !== 6) {
      Alert.alert('Error', 'Please enter a 6-digit code');
      return;
    }

    if (!confirmationResult) {
      Alert.alert('Error', 'OTP not ready. Please try signing up again.');
      return;
    }

    setLoading(true);
    try {
      // Confirm OTP with Firebase (or mock)
      const userCredential = await confirmationResult.confirm(code);
      const firebaseToken = await userCredential.user.getIdToken();

      // Try to sync with backend, but allow dev mode with mock tokens
      try {
        await syncUser(firebaseToken);
      } catch (syncError: any) {
        // In dev mode with mock tokens, backend will reject
        // Allow proceeding anyway for testing
        if (firebaseToken.startsWith('mock:')) {
          console.warn('Dev mode: Backend rejected mock token, proceeding anyway');
        } else {
          throw syncError;
        }
      }

      // Save user and token to Zustand store
      await setUser(userCredential.user, firebaseToken);

      // Navigate to authenticated screens
      router.replace('/(tabs)/searches');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Verification failed';
      Alert.alert('Error', message);
      console.error('OTP verification error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Enter verification code</Text>
      <Text style={styles.subtitle}>We sent a code to {phone}</Text>

      <TextInput
        placeholder="000000"
        value={code}
        onChangeText={setCode}
        keyboardType="number-pad"
        maxLength={6}
        style={styles.input}
        editable={!loading}
        autoFocus
      />

      <TouchableOpacity
        style={[styles.button, loading && styles.buttonDisabled]}
        onPress={handleVerify}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.buttonText}>Verify</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}
