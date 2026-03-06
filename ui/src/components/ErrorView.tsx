import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

export function ErrorView({ message }: { message: string }) {
  return (
    <View style={styles.container}>
      <Text style={styles.emoji}>⚠️</Text>
      <Text style={styles.message}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  emoji: { fontSize: 40, marginBottom: 12 },
  message: { fontSize: 15, color: '#64748B', textAlign: 'center' },
});
