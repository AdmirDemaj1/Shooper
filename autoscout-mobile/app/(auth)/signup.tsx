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
import { useRouter } from 'expo-router';
import { useAuthStore } from '../../store/authStore';

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 20,
    backgroundColor: '#fff',
  },
  title: {
    fontSize: 28,
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
  note: {
    fontSize: 12,
    color: '#999',
    marginTop: 20,
    textAlign: 'center',
  },
});

export default function Signup() {
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const setConfirmationResult = useAuthStore((state) => state.setConfirmationResult);

  const handleSignup = async () => {
    if (!phone.trim()) {
      Alert.alert('Error', 'Please enter a phone number');
      return;
    }

    setLoading(true);
    try {
      const phoneWithCountry = phone.startsWith('+') ? phone : `+${phone}`;

      // For development/Expo Go: simulate OTP being sent
      // In production, replace with actual Firebase signInWithPhoneNumber
      const mockConfirmationResult = {
        verificationId: 'mock-' + Date.now(),
        confirm: async (code: string) => {
          // Mock: just validate code format for now
          if (code.length !== 6) throw new Error('Invalid code');
          return {
            user: {
              uid: 'mock-' + Date.now(),
              phoneNumber: phoneWithCountry,
              getIdToken: async () => `mock:${phoneWithCountry}`,
            },
          };
        },
      };

      setConfirmationResult(mockConfirmationResult as any);

      // Navigate to OTP screen
      router.push({
        pathname: '/(auth)/otp',
        params: { phone: phoneWithCountry },
      });

      Alert.alert('OTP Sent', `A test code will be: 123456\n(In production, you\'ll receive a real SMS)`);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to send OTP';
      Alert.alert('Error', message);
      console.error('Sign up error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>AutoScout AI</Text>
      <Text style={styles.subtitle}>Find your perfect car</Text>

      <TextInput
        placeholder="+355 69 123 4567"
        value={phone}
        onChangeText={setPhone}
        keyboardType="phone-pad"
        style={styles.input}
        editable={!loading}
        autoFocus
        placeholderTextColor="#ccc"
      />

      <TouchableOpacity
        style={[styles.button, loading && styles.buttonDisabled]}
        onPress={handleSignup}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.buttonText}>Send OTP</Text>
        )}
      </TouchableOpacity>

      <Text style={styles.note}>Dev Mode: Use code 123456 to test</Text>
    </View>
  );
}
