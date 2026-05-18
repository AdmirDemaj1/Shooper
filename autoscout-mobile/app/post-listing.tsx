import React, { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { MaterialIcons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import * as ImageManipulator from 'expo-image-manipulator';
import { platformListingsApi } from '../lib/api';

const CURRENCIES = ['EUR', 'ALL'] as const;
const TRANSMISSIONS = ['', 'manual', 'automatic'] as const;
const FUELS = ['', 'petrol', 'diesel', 'electric', 'hybrid'] as const;
const BODY_TYPES = ['', 'sedan', 'hatchback', 'suv', 'estate', 'coupe', 'convertible'] as const;

function PickerRow({
  label, options, value, onChange,
}: { label: string; options: readonly string[]; value: string; onChange: (v: string) => void }) {
  return (
    <View style={styles.pickerRow}>
      <Text style={styles.pickerLabel}>{label}</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
        {options.map((opt) => (
          <TouchableOpacity
            key={opt}
            style={[styles.chip, value === opt && styles.chipActive]}
            onPress={() => onChange(opt)}
          >
            <Text style={[styles.chipText, value === opt && styles.chipTextActive]}>
              {opt || 'Any'}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );
}

export default function PostListing() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);

  // Form fields
  const [title, setTitle] = useState('');
  const [make, setMake] = useState('');
  const [model, setModel] = useState('');
  const [year, setYear] = useState('');
  const [price, setPrice] = useState('');
  const [currency, setCurrency] = useState<'EUR' | 'ALL'>('EUR');
  const [mileage, setMileage] = useState('');
  const [location, setLocation] = useState('');
  const [transmission, setTransmission] = useState('');
  const [fuelType, setFuelType] = useState('');
  const [bodyType, setBodyType] = useState('');
  const [description, setDescription] = useState('');
  const [contactPhone, setContactPhone] = useState('');

  // Photos
  const [photos, setPhotos] = useState<{ uri: string }[]>([]);
  const [uploadingPhotos, setUploadingPhotos] = useState(false);

  async function pickPhotos() {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission needed', 'Please allow access to your photo library.');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsMultipleSelection: true,
      quality: 0.8,
      selectionLimit: 10 - photos.length,
    });
    if (!result.canceled) {
      setPhotos((prev) => [...prev, ...result.assets.map((a) => ({ uri: a.uri }))].slice(0, 10));
    }
  }

  function removePhoto(index: number) {
    setPhotos((prev) => prev.filter((_, i) => i !== index));
  }

  async function uploadPhotos(listingId: string): Promise<void> {
    for (const photo of photos) {
      try {
        const compressed = await ImageManipulator.manipulateAsync(
          photo.uri,
          [{ resize: { width: 1600 } }],
          { compress: 0.8, format: ImageManipulator.SaveFormat.JPEG }
        );
        await platformListingsApi.uploadPhotoDirect(listingId, compressed.uri);
      } catch (err) {
        console.warn('Photo upload failed', err);
      }
    }
  }

  async function handleSubmit() {
    if (!title.trim()) {
      Alert.alert('Required', 'Please enter a title for your listing.');
      return;
    }
    if (description.trim().length < 30) {
      Alert.alert('Required', 'Description must be at least 30 characters.');
      return;
    }

    setSubmitting(true);
    try {
      const listing = await platformListingsApi.create({
        title: title.trim(),
        make: make.trim() || undefined,
        model: model.trim() || undefined,
        year: year ? parseInt(year, 10) : undefined,
        price: price.trim() || undefined,
        currency,
        mileage: mileage ? parseInt(mileage, 10) : undefined,
        location_text: location.trim() || undefined,
        transmission: transmission || undefined,
        fuel_type: fuelType || undefined,
        body_type: bodyType || undefined,
        description: description.trim(),
        contact_phone: contactPhone.trim() || undefined,
      });

      if (photos.length > 0) {
        setUploadingPhotos(true);
        await uploadPhotos(listing.id);
        setUploadingPhotos(false);
      }

      Alert.alert('Listed!', 'Your car is now live. Buyers will be notified if it matches their search.', [
        { text: 'View listing', onPress: () => router.replace(`/listing/${listing.id}`) },
      ]);
    } catch (err: any) {
      Alert.alert('Error', err?.response?.data?.detail || 'Could not post listing. Try again.');
    } finally {
      setSubmitting(false);
      setUploadingPhotos(false);
    }
  }

  const busy = submitting || uploadingPhotos;

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView style={styles.container} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Text style={styles.sectionTitle}>Photos</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.photoRow}>
          {photos.map((p, i) => (
            <View key={i} style={styles.photoThumb}>
              <Image source={{ uri: p.uri }} style={styles.photoImg} />
              <TouchableOpacity style={styles.photoRemove} onPress={() => removePhoto(i)}>
                <MaterialIcons name="close" size={14} color="#fff" />
              </TouchableOpacity>
            </View>
          ))}
          {photos.length < 10 && (
            <TouchableOpacity style={styles.photoAdd} onPress={pickPhotos}>
              <MaterialIcons name="add-photo-alternate" size={28} color="#2E7D32" />
              <Text style={styles.photoAddText}>Add</Text>
            </TouchableOpacity>
          )}
        </ScrollView>

        <Text style={styles.sectionTitle}>Details</Text>

        <Text style={styles.label}>Title *</Text>
        <TextInput style={styles.input} value={title} onChangeText={setTitle} placeholder="e.g. VW Golf 7 2019 Manual" />

        <View style={styles.row}>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Make</Text>
            <TextInput style={styles.input} value={make} onChangeText={setMake} placeholder="BMW" />
          </View>
          <View style={{ width: 12 }} />
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Model</Text>
            <TextInput style={styles.input} value={model} onChangeText={setModel} placeholder="3 Series" />
          </View>
        </View>

        <View style={styles.row}>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Year</Text>
            <TextInput style={styles.input} value={year} onChangeText={setYear} placeholder="2019" keyboardType="numeric" />
          </View>
          <View style={{ width: 12 }} />
          <View style={{ flex: 2 }}>
            <Text style={styles.label}>Price</Text>
            <View style={styles.priceRow}>
              <TextInput style={[styles.input, { flex: 1 }]} value={price} onChangeText={setPrice} placeholder="9800" keyboardType="numeric" />
              <TouchableOpacity
                style={styles.currencyToggle}
                onPress={() => setCurrency((c) => c === 'EUR' ? 'ALL' : 'EUR')}
              >
                <Text style={styles.currencyText}>{currency}</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>

        <View style={styles.row}>
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Mileage (km)</Text>
            <TextInput style={styles.input} value={mileage} onChangeText={setMileage} placeholder="72000" keyboardType="numeric" />
          </View>
          <View style={{ width: 12 }} />
          <View style={{ flex: 1 }}>
            <Text style={styles.label}>Location</Text>
            <TextInput style={styles.input} value={location} onChangeText={setLocation} placeholder="Tiranë" />
          </View>
        </View>

        <PickerRow label="Transmission" options={TRANSMISSIONS} value={transmission} onChange={setTransmission} />
        <PickerRow label="Fuel" options={FUELS} value={fuelType} onChange={setFuelType} />
        <PickerRow label="Body type" options={BODY_TYPES} value={bodyType} onChange={setBodyType} />

        <Text style={styles.label}>Description * (min 30 chars)</Text>
        <TextInput
          style={[styles.input, styles.textArea]}
          value={description}
          onChangeText={setDescription}
          placeholder="Describe the car's condition, history, extras..."
          multiline
          numberOfLines={5}
          textAlignVertical="top"
        />

        <Text style={styles.label}>Contact phone</Text>
        <TextInput
          style={styles.input}
          value={contactPhone}
          onChangeText={setContactPhone}
          placeholder="+355 69 123 4567"
          keyboardType="phone-pad"
        />

        <TouchableOpacity
          style={[styles.submitBtn, busy && styles.submitBtnDisabled]}
          onPress={handleSubmit}
          disabled={busy}
        >
          {busy ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <MaterialIcons name="publish" size={18} color="#fff" />
          )}
          <Text style={styles.submitBtnText}>
            {uploadingPhotos ? 'Uploading photos…' : submitting ? 'Posting…' : 'Post listing'}
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  content: { padding: 16, paddingBottom: 40 },
  sectionTitle: { fontSize: 13, fontWeight: '700', color: '#555', textTransform: 'uppercase', letterSpacing: 0.5, marginTop: 20, marginBottom: 10 },
  label: { fontSize: 13, color: '#555', marginBottom: 4, marginTop: 12 },
  input: { borderWidth: 1, borderColor: '#ddd', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, fontSize: 15, color: '#111', backgroundColor: '#fafafa' },
  textArea: { height: 110, paddingTop: 10 },
  row: { flexDirection: 'row', alignItems: 'flex-end' },
  priceRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  currencyToggle: { borderWidth: 1, borderColor: '#2E7D32', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 10 },
  currencyText: { fontSize: 14, fontWeight: '700', color: '#2E7D32' },
  pickerRow: { marginTop: 12 },
  pickerLabel: { fontSize: 13, color: '#555', marginBottom: 6 },
  chips: { gap: 8, paddingRight: 16 },
  chip: { paddingHorizontal: 14, paddingVertical: 7, borderRadius: 20, borderWidth: 1, borderColor: '#ddd', backgroundColor: '#fafafa' },
  chipActive: { backgroundColor: '#2E7D32', borderColor: '#2E7D32' },
  chipText: { fontSize: 13, color: '#444' },
  chipTextActive: { color: '#fff', fontWeight: '600' },
  photoRow: { marginBottom: 4 },
  photoThumb: { width: 80, height: 80, borderRadius: 8, marginRight: 8, overflow: 'visible', position: 'relative' },
  photoImg: { width: 80, height: 80, borderRadius: 8 },
  photoRemove: { position: 'absolute', top: -6, right: -6, backgroundColor: '#c62828', borderRadius: 10, width: 20, height: 20, justifyContent: 'center', alignItems: 'center' },
  photoAdd: { width: 80, height: 80, borderRadius: 8, borderWidth: 1.5, borderColor: '#2E7D32', borderStyle: 'dashed', justifyContent: 'center', alignItems: 'center', gap: 2 },
  photoAddText: { fontSize: 11, color: '#2E7D32' },
  submitBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#2E7D32', paddingVertical: 14, borderRadius: 10, marginTop: 24, gap: 8 },
  submitBtnDisabled: { backgroundColor: '#81A784' },
  submitBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
});
