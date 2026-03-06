/**
 * Colour tokens for light and dark themes.
 *
 * Light  — neon-pastel: electric fuchsia + vibrant purple + periwinkle on
 *           a soft lavender-white canvas.
 * Dark   — same hues but glowing on deep purple-black.
 */

export interface Theme {
  // Canvas
  bg:         string;
  surface:    string;
  surfaceAlt: string;
  // Borders
  border:      string;
  borderLight: string;
  // Violet — backbone
  primary:      string;
  primaryLight: string;
  primaryDim:   string;
  // Fuchsia — accent (CTA, scrub bar, progress)
  fuchsia:     string;
  fuchsiaLight:string;
  fuchsiaDim:  string;
  // Periwinkle — meta / secondary info
  periwinkle:    string;
  periwinkleDim: string;
  // Text
  textPrimary:   string;
  textSecondary: string;
  textMuted:     string;
  // Semantic
  error:      string;
  errorDim:   string;
  success:    string;
  successDim: string;
  warning:    string;
  warningDim: string;
}

export const lightTheme: Theme = {
  bg:         '#FAFAFF',
  surface:    '#FFFFFF',
  surfaceAlt: '#F5F0FF',

  border:      '#E9D5FF',
  borderLight: '#F3E8FF',

  primary:      '#9333EA',
  primaryLight: '#C084FC',
  primaryDim:   '#F3E8FF',

  fuchsia:     '#D946EF',
  fuchsiaLight:'#F0ABFC',
  fuchsiaDim:  '#FDF4FF',

  periwinkle:    '#818CF8',
  periwinkleDim: '#EEF2FF',

  textPrimary:   '#2E1065',
  textSecondary: '#7E22CE',
  textMuted:     '#A78BFA',

  error:      '#F43F5E',
  errorDim:   '#FFF1F2',
  success:    '#10B981',
  successDim: '#ECFDF5',
  warning:    '#F59E0B',
  warningDim: '#FFFBEB',
};

export const darkTheme: Theme = {
  bg:         '#0D0B1A',
  surface:    '#161228',
  surfaceAlt: '#1E1840',

  border:      '#3D2B6E',
  borderLight: '#2A2050',

  primary:      '#A855F7',
  primaryLight: '#C084FC',
  primaryDim:   '#2D1058',

  fuchsia:     '#E879F9',
  fuchsiaLight:'#F0ABFC',
  fuchsiaDim:  '#3D0F4A',

  periwinkle:    '#818CF8',
  periwinkleDim: '#1E1B40',

  textPrimary:   '#F5F3FF',
  textSecondary: '#DDD6FE',
  textMuted:     '#7C6AA8',

  error:      '#F87171',
  errorDim:   '#2D0D0D',
  success:    '#34D399',
  successDim: '#0A2B1A',
  warning:    '#FBBF24',
  warningDim: '#2A1C04',
};
