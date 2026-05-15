import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  Alert,
  ActivityIndicator,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import { useProfileStore } from '../store/profileStore';
import { profilesApi } from '../lib/api';

type Mode = 'form' | 'nl';

const TRANSMISSIONS = ['manual', 'automatic'];
const FUEL_TYPES = ['petrol', 'diesel', 'electric', 'hybrid', 'lpg'];

function ChipGroup({
  options,
  value,
  onChange,
}: {
  options: string[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <View style={styles.chipRow}>
      {options.map((opt) => {
        const selected = value === opt;
        return (
          <TouchableOpacity
            key={opt}
            style={[styles.chip, selected && styles.chipSelected]}
            onPress={() => onChange(selected ? '' : opt)}
          >
            <Text style={[styles.chipText, selected && styles.chipTextSelected]}>
              {opt.charAt(0).toUpperCase() + opt.slice(1)}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

export default function ProfileForm() {
  const router = useRouter();
  const { id, mode: initialMode } = useLocalSearchParams<{ id?: string; mode?: string }>();
  const { profiles, create, update } = useProfileStore();

  const existing = id ? profiles.find((p) => p.id === id) : undefined;
  const isEditing = !!existing;

  const [mode, setMode] = useState<Mode>(initialMode === 'nl' ? 'nl' : 'form');
  const [nlText, setNlText] = useState('');
  const [parsing, setParsing] = useState(false);
  const [lowConfidence, setLowConfidence] = useState<Set<string>>(new Set());

  // Form fields
  const [name, setName] = useState(existing?.name ?? '');
  const [make, setMake] = useState(existing?.make ?? '');
  const [model, setModel] = useState(existing?.model ?? '');
  const [yearMin, setYearMin] = useState(existing?.year_min?.toString() ?? '');
  const [yearMax, setYearMax] = useState(existing?.year_max?.toString() ?? '');
  const [priceMax, setPriceMax] = useState(existing?.price_max?.toString() ?? '');
  const [currency, setCurrency] = useState(existing?.currency ?? 'EUR');
  const [mileageMax, setMileageMax] = useState(existing?.mileage_max?.toString() ?? '');
  const [transmission, setTransmission] = useState(existing?.transmission ?? '');
  const [fuelType, setFuelType] = useState(existing?.fuel_type ?? '');
  const [notes, setNotes] = useState(existing?.free_text_criteria ?? '');
  const [saving, setSaving] = useState(false);

  async function handleParse() {
    if (!nlText.trim()) return;
    setParsing(true);
    try {
      const result = await profilesApi.parse(nlText.trim());
      const p = result.profile;
      if (p.name) setName(p.name);
      if (p.make) setMake(p.make);
      if (p.model) setModel(p.model);
      if (p.year_min) setYearMin(String(p.year_min));
      if (p.year_max) setYearMax(String(p.year_max));
      if (p.price_max) setPriceMax(String(p.price_max));
      if (p.currency) setCurrency(p.currency);
      if (p.mileage_max) setMileageMax(String(p.mileage_max));
      if (p.transmission) setTransmission(p.transmission);
      if (p.fuel_type) setFuelType(p.fuel_type);
      if (p.free_text_criteria) setNotes(p.free_text_criteria);
      setLowConfidence(new Set(result.low_confidence_fields));
      setMode('form');
    } catch {
      Alert.alert('Parse failed', 'Could not parse your description. Please try again.');
    } finally {
      setParsing(false);
    }
  }

  async function handleSave() {
    if (!name.trim()) {
      Alert.alert('Name required', 'Please give this search a name.');
      return;
    }
    setSaving(true);
    try {
      const data = {
        name: name.trim(),
        make: make.trim() || undefined,
        model: model.trim() || undefined,
        year_min: yearMin ? parseInt(yearMin, 10) : undefined,
        year_max: yearMax ? parseInt(yearMax, 10) : undefined,
        price_max: priceMax ? parseFloat(priceMax) : undefined,
        currency,
        mileage_max: mileageMax ? parseInt(mileageMax, 10) : undefined,
        transmission: transmission || undefined,
        fuel_type: fuelType || undefined,
        free_text_criteria: notes.trim() || undefined,
      };
      if (isEditing && id) {
        await update(id, data);
      } else {
        await create(data);
      }
      router.back();
    } catch (e: any) {
      const detail = e?.response?.data?.detail ?? e?.message ?? 'Unknown error';
      Alert.alert('Save failed', detail);
      console.error('Save error', e?.response?.data ?? e);
    } finally {
      setSaving(false);
    }
  }

  // Yellow border on low-confidence fields
  const fieldStyle = (field: string) =>
    lowConfidence.has(field) ? styles.inputLowConfidence : styles.input;

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <Stack.Screen options={{ title: isEditing ? 'Edit Search' : 'New Search', headerShown: true }} />
      <ScrollView style={styles.container} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">

        {/* Mode toggle */}
        <View style={styles.modeToggle}>
          <TouchableOpacity
            style={[styles.modeBtn, mode === 'form' && styles.modeBtnActive]}
            onPress={() => setMode('form')}
          >
            <Text style={[styles.modeBtnText, mode === 'form' && styles.modeBtnTextActive]}>Form</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.modeBtn, mode === 'nl' && styles.modeBtnActive]}
            onPress={() => setMode('nl')}
          >
            <Text style={[styles.modeBtnText, mode === 'nl' && styles.modeBtnTextActive]}>Describe in words</Text>
          </TouchableOpacity>
        </View>

        {/* NL mode */}
        {mode === 'nl' && (
          <View style={styles.nlContainer}>
            <Text style={styles.nlHint}>
              Example: "VW Golf 6, viti 2010-2015, çmim max 8000 euro, max 200 mijë km"
            </Text>
            <TextInput
              style={styles.nlInput}
              placeholder="Describe the car you're looking for..."
              placeholderTextColor="#aaa"
              value={nlText}
              onChangeText={setNlText}
              multiline
              numberOfLines={5}
              textAlignVertical="top"
            />
            <TouchableOpacity
              style={[styles.parseBtn, (!nlText.trim() || parsing) && styles.parseBtnDisabled]}
              onPress={handleParse}
              disabled={!nlText.trim() || parsing}
            >
              {parsing ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <Text style={styles.parseBtnText}>Parse & fill form</Text>
              )}
            </TouchableOpacity>
          </View>
        )}

        {/* Form mode */}
        {mode === 'form' && (
          <View style={styles.formContainer}>
            {lowConfidence.size > 0 && (
              <View style={styles.reviewBanner}>
                <Text style={styles.reviewBannerText}>
                  Fields outlined in yellow have low confidence — please review them.
                </Text>
              </View>
            )}

            <Text style={styles.label}>Name *</Text>
            <TextInput style={fieldStyle('name')} placeholder="e.g. VW Golf, budget €8k" placeholderTextColor="#aaa" value={name} onChangeText={setName} />

            <Text style={styles.label}>Make</Text>
            <TextInput style={fieldStyle('make')} placeholder="e.g. Volkswagen" placeholderTextColor="#aaa" value={make} onChangeText={setMake} />

            <Text style={styles.label}>Model</Text>
            <TextInput style={fieldStyle('model')} placeholder="e.g. Golf 6" placeholderTextColor="#aaa" value={model} onChangeText={setModel} />

            <Text style={styles.label}>Year</Text>
            <View style={styles.row}>
              <TextInput
                style={[fieldStyle('year_min'), styles.flex1]}
                placeholder="From"
                placeholderTextColor="#aaa"
                value={yearMin}
                onChangeText={setYearMin}
                keyboardType="number-pad"
              />
              <Text style={styles.rangeSep}>–</Text>
              <TextInput
                style={[fieldStyle('year_max'), styles.flex1]}
                placeholder="To"
                placeholderTextColor="#aaa"
                value={yearMax}
                onChangeText={setYearMax}
                keyboardType="number-pad"
              />
            </View>

            <Text style={styles.label}>Max price</Text>
            <View style={styles.row}>
              <TextInput
                style={[fieldStyle('price_max'), styles.flex1]}
                placeholder="0"
                placeholderTextColor="#aaa"
                value={priceMax}
                onChangeText={setPriceMax}
                keyboardType="decimal-pad"
              />
              <TouchableOpacity
                style={[styles.currencyToggle, currency === 'EUR' && styles.currencyActive]}
                onPress={() => setCurrency('EUR')}
              >
                <Text style={[styles.currencyText, currency === 'EUR' && styles.currencyTextActive]}>EUR</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.currencyToggle, currency === 'ALL' && styles.currencyActive]}
                onPress={() => setCurrency('ALL')}
              >
                <Text style={[styles.currencyText, currency === 'ALL' && styles.currencyTextActive]}>ALL</Text>
              </TouchableOpacity>
            </View>

            <Text style={styles.label}>Max mileage (km)</Text>
            <TextInput
              style={fieldStyle('mileage_max')}
              placeholder="e.g. 200000"
              placeholderTextColor="#aaa"
              value={mileageMax}
              onChangeText={setMileageMax}
              keyboardType="number-pad"
            />

            <Text style={styles.label}>Transmission</Text>
            <ChipGroup options={TRANSMISSIONS} value={transmission} onChange={setTransmission} />

            <Text style={styles.label}>Fuel type</Text>
            <ChipGroup options={FUEL_TYPES} value={fuelType} onChange={setFuelType} />

            <Text style={styles.label}>Extra notes</Text>
            <TextInput
              style={[fieldStyle('free_text_criteria'), styles.notesInput]}
              placeholder="Any other requirements..."
              placeholderTextColor="#aaa"
              value={notes}
              onChangeText={setNotes}
              multiline
              numberOfLines={3}
              textAlignVertical="top"
            />
          </View>
        )}

        {/* Save button always visible at bottom */}
        <TouchableOpacity
          style={[styles.saveBtn, (saving || (mode === 'nl' && !name)) && styles.saveBtnDisabled]}
          onPress={mode === 'nl' ? handleParse : handleSave}
          disabled={saving}
        >
          {saving ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Text style={styles.saveBtnText}>
              {mode === 'nl' ? 'Parse & fill form' : isEditing ? 'Save changes' : 'Create search'}
            </Text>
          )}
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  content: { padding: 20, paddingBottom: 40 },

  // Mode toggle
  modeToggle: { flexDirection: 'row', backgroundColor: '#f0f0f0', borderRadius: 8, padding: 3, marginBottom: 24 },
  modeBtn: { flex: 1, paddingVertical: 8, alignItems: 'center', borderRadius: 6 },
  modeBtnActive: { backgroundColor: '#fff', shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 2, elevation: 1 },
  modeBtnText: { fontSize: 14, color: '#888', fontWeight: '500' },
  modeBtnTextActive: { color: '#111', fontWeight: '600' },

  // NL mode
  nlContainer: { gap: 12 },
  nlHint: { fontSize: 13, color: '#666', fontStyle: 'italic', lineHeight: 18 },
  nlInput: { borderWidth: 1, borderColor: '#ddd', borderRadius: 8, padding: 12, fontSize: 15, color: '#111', minHeight: 120, backgroundColor: '#fafafa' },
  parseBtn: { backgroundColor: '#2E7D32', paddingVertical: 13, borderRadius: 8, alignItems: 'center' },
  parseBtnDisabled: { backgroundColor: '#aaa' },
  parseBtnText: { color: '#fff', fontSize: 15, fontWeight: '600' },

  // Form mode
  formContainer: { gap: 4 },
  reviewBanner: { backgroundColor: '#FFF8E1', borderWidth: 1, borderColor: '#FFD600', borderRadius: 8, padding: 10, marginBottom: 8 },
  reviewBannerText: { fontSize: 13, color: '#5D4037' },

  label: { fontSize: 13, fontWeight: '600', color: '#444', marginBottom: 4, marginTop: 12 },
  input: { borderWidth: 1, borderColor: '#ddd', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, fontSize: 15, color: '#111', backgroundColor: '#fafafa' },
  inputLowConfidence: { borderWidth: 2, borderColor: '#FFD600', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, fontSize: 15, color: '#111', backgroundColor: '#FFFDE7' },
  notesInput: { minHeight: 80, textAlignVertical: 'top' },

  row: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  flex1: { flex: 1 },
  rangeSep: { fontSize: 16, color: '#666' },

  // Currency toggle
  currencyToggle: { paddingVertical: 10, paddingHorizontal: 14, borderWidth: 1, borderColor: '#ddd', borderRadius: 8 },
  currencyActive: { borderColor: '#2E7D32', backgroundColor: '#E8F5E9' },
  currencyText: { fontSize: 14, color: '#666', fontWeight: '500' },
  currencyTextActive: { color: '#2E7D32', fontWeight: '700' },

  // Chips
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { paddingVertical: 7, paddingHorizontal: 14, borderRadius: 20, borderWidth: 1, borderColor: '#ddd' },
  chipSelected: { backgroundColor: '#2E7D32', borderColor: '#2E7D32' },
  chipText: { fontSize: 13, color: '#555' },
  chipTextSelected: { color: '#fff', fontWeight: '600' },

  // Save
  saveBtn: { backgroundColor: '#2E7D32', paddingVertical: 14, borderRadius: 8, alignItems: 'center', marginTop: 32 },
  saveBtnDisabled: { backgroundColor: '#aaa' },
  saveBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
});
