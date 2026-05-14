# AutoScout Mobile

React Native app for AutoScout AI. iOS and Android via Expo.

## Tech Stack

- **Framework:** React Native 0.74+ with Expo SDK 51+
- **State Management:** Zustand
- **Server Cache:** React Query 5+
- **Auth:** Firebase Auth (phone OTP)
- **Maps:** React Native Maps + Mapbox
- **UI:** React Native Paper + custom design tokens
- **Build:** Expo CLI + EAS Build

## Local Development

### Prerequisites

- Node.js 20+
- Expo CLI (`npm install -g expo-cli`)
- Xcode (macOS) or Android Studio
- iPhone or Android simulator

### Setup

```bash
# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your API URLs and Firebase config

# Start dev server
expo start

# Open in iOS simulator
# Press 'i' in the terminal

# Open in Android emulator
# Press 'a' in the terminal
```

## Project Structure

```
autoscout-mobile/
├── app/
│   ├── _layout.tsx          # Root navigation
│   ├── (auth)/
│   │   ├── signup.tsx
│   │   ├── otp.tsx
│   │   └── _layout.tsx
│   ├── (tabs)/
│   │   ├── searches.tsx
│   │   ├── history.tsx
│   │   ├── settings.tsx
│   │   └── _layout.tsx
│   ├── match-detail/[id].tsx
│   └── modals/
│       ├── create-profile.tsx
│       └── location-picker.tsx
├── src/
│   ├── api/
│   │   ├── client.ts        # HTTP client with auth headers
│   │   ├── auth.ts
│   │   ├── profiles.ts
│   │   └── matches.ts
│   ├── store/
│   │   ├── auth.ts          # Zustand auth store
│   │   ├── profiles.ts
│   │   └── matches.ts
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useProfiles.ts
│   │   └── useMatches.ts
│   ├── components/
│   │   ├── ListingCard.tsx
│   │   ├── ProfileForm.tsx
│   │   ├── LocationPicker.tsx
│   │   └── EmptyState.tsx
│   ├── utils/
│   │   ├── formatting.ts
│   │   ├── validation.ts
│   │   └── geo.ts
│   └── design/
│       ├── tokens.ts        # Design system tokens
│       └── theme.ts
├── app.json                 # Expo config
├── eas.json                 # EAS Build config
├── package.json
└── README.md
```

## Environment Variables

```env
# API
EXPO_PUBLIC_API_URL=http://localhost:8000
EXPO_PUBLIC_API_ENV=dev

# Firebase
EXPO_PUBLIC_FIREBASE_API_KEY=...
EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN=...
EXPO_PUBLIC_FIREBASE_PROJECT_ID=...
EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET=...
EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=...
EXPO_PUBLIC_FIREBASE_APP_ID=...

# Maps
EXPO_PUBLIC_MAPBOX_TOKEN=...
```

Note: `EXPO_PUBLIC_*` vars are bundled into the app; never put secrets there.

## Building & Deployment

### TestFlight (iOS)

```bash
eas build --platform ios --profile preview
# Follow prompts; upload to TestFlight
```

### Google Play Internal Testing (Android)

```bash
eas build --platform android --profile preview
# Follow prompts; upload to Play Console
```

## Testing

```bash
npm run test
```

## Code Quality

```bash
# Lint
npm run lint

# Format
npm run format

# Type check
npm run type-check
```

## Contributing

1. Branch from `main`
2. Follow TypeScript strict mode
3. Test on both iOS and Android simulators
4. PR with no console warnings or errors
