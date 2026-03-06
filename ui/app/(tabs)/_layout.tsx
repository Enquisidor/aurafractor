import { Tabs } from 'expo-router';
import React from 'react';
import { Text } from 'react-native';
import { useTheme } from '../../src/contexts/ThemeContext';

function Icon({ emoji }: { emoji: string }) {
  return <Text style={{ fontSize: 22 }}>{emoji}</Text>;
}

export default function TabLayout() {
  const { C } = useTheme();

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: C.primary,
        tabBarInactiveTintColor: C.textMuted,
        tabBarStyle: {
          backgroundColor: C.surface,
          borderTopColor: C.border,
          borderTopWidth: 1,
        },
        headerStyle: { backgroundColor: C.surface },
        headerTintColor: C.textPrimary,
        headerShadowVisible: false,
        headerShown: true,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{ title: 'Upload', tabBarIcon: () => <Icon emoji="🎵" /> }}
      />
      <Tabs.Screen
        name="history"
        options={{ title: 'History', tabBarIcon: () => <Icon emoji="📋" /> }}
      />
      <Tabs.Screen
        name="credits"
        options={{ title: 'Credits', tabBarIcon: () => <Icon emoji="💳" /> }}
      />
    </Tabs>
  );
}
