import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { useColorScheme } from 'react-native';
import { storage } from '../storage/platform';
import { darkTheme, lightTheme, Theme } from '../theme';

const STORAGE_KEY = 'theme_preference';

interface ThemeContextValue {
  C: Theme;
  isDark: boolean;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  C: lightTheme,
  isDark: false,
  toggleTheme: () => {},
});

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const systemScheme = useColorScheme();
  // null = follow system, 'light' | 'dark' = user override
  const [override, setOverride] = useState<'light' | 'dark' | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    storage.getItem(STORAGE_KEY).then((val) => {
      if (val === 'light' || val === 'dark') setOverride(val);
      setLoaded(true);
    });
  }, []);

  const isDark = override != null ? override === 'dark' : systemScheme === 'dark';
  const C = isDark ? darkTheme : lightTheme;

  const toggleTheme = useCallback(() => {
    const next = isDark ? 'light' : 'dark';
    setOverride(next);
    storage.setItem(STORAGE_KEY, next);
  }, [isDark]);

  // Render nothing until preference is loaded to avoid flash
  if (!loaded) return null;

  return (
    <ThemeContext.Provider value={{ C, isDark, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}
