import { Tabs } from 'expo-router';
import React from 'react';
import { Text } from 'react-native';

function Icon({ emoji }: { emoji: string }) {
  return <Text style={{ fontSize: 22 }}>{emoji}</Text>;
}

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: '#6366F1',
        headerShown: true,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Upload',
          tabBarIcon: () => <Icon emoji="🎵" />,
        }}
      />
      <Tabs.Screen
        name="history"
        options={{
          title: 'History',
          tabBarIcon: () => <Icon emoji="📋" />,
        }}
      />
      <Tabs.Screen
        name="credits"
        options={{
          title: 'Credits',
          tabBarIcon: () => <Icon emoji="💳" />,
        }}
      />
    </Tabs>
  );
}
