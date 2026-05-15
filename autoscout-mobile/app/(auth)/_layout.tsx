import { Stack } from 'expo-router';

export default function AuthLayout() {
  return (
    <Stack
      screenOptions={{ headerShown: false }}
      initialRouteName="signup"
    >
      <Stack.Screen
        name="signup"
        options={{ animationEnabled: false }}
      />
      <Stack.Screen name="otp" />
    </Stack>
  );
}
