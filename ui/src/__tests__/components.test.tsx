/**
 * TDD tests for shared UI components.
 */

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react-native';
import React from 'react';
import { LabelChip } from '../components/LabelChip';
import { StatusBadge } from '../components/StatusBadge';
import { ErrorView } from '../components/ErrorView';
import { FirstLaunchModal } from '../components/FirstLaunchModal';
import { storage } from '../storage/platform';

// platform-storage mock exposes __clear for test isolation
const mockStorage = storage as any;

const SUGGESTION = {
  label: 'lead vocals',
  confidence: 0.94,
  frequency_range: [85, 8000] as [number, number],
  recommended: true,
};

// ---------------------------------------------------------------------------
// LabelChip
// ---------------------------------------------------------------------------

describe('LabelChip', () => {
  it('renders the label and rounded confidence', () => {
    render(<LabelChip suggestion={SUGGESTION} selected={false} onPress={() => {}} />);
    expect(screen.getByText('lead vocals')).toBeTruthy();
    expect(screen.getByText('94%')).toBeTruthy();
  });

  it('calls onPress when tapped', () => {
    const onPress = jest.fn();
    render(<LabelChip suggestion={SUGGESTION} selected={false} onPress={onPress} />);
    fireEvent.press(screen.getByRole('checkbox'));
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  it('reflects selected state in accessibilityState', () => {
    const { rerender } = render(
      <LabelChip suggestion={SUGGESTION} selected={false} onPress={() => {}} />,
    );
    expect(screen.getByRole('checkbox').props.accessibilityState.checked).toBe(false);

    rerender(<LabelChip suggestion={SUGGESTION} selected={true} onPress={() => {}} />);
    expect(screen.getByRole('checkbox').props.accessibilityState.checked).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// StatusBadge
// ---------------------------------------------------------------------------

describe('StatusBadge', () => {
  it.each([
    ['queued', 'Queued'],
    ['processing', 'Processing…'],
    ['completed', 'Completed'],
    ['failed', 'Failed'],
    ['awaiting_confirmation', 'Confirm Labels'],
  ] as const)('renders correct label for status "%s"', (status, label) => {
    render(<StatusBadge status={status} />);
    expect(screen.getByText(label)).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// ErrorView
// ---------------------------------------------------------------------------

describe('ErrorView', () => {
  it('renders the provided message', () => {
    render(<ErrorView message="Something went wrong" />);
    expect(screen.getByText('Something went wrong')).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// FirstLaunchModal
// ---------------------------------------------------------------------------

describe('FirstLaunchModal', () => {
  beforeEach(() => {
    mockStorage.__clear();
  });

  it('renders the welcome modal on first launch', async () => {
    render(<FirstLaunchModal />);
    await waitFor(() => {
      expect(screen.getByText('Welcome to Aurafractor')).toBeTruthy();
    });
  });

  it('shows the Get started button', async () => {
    render(<FirstLaunchModal />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /get started/i })).toBeTruthy();
    });
  });

  it('dismisses and persists seen flag when Get started is pressed', async () => {
    render(<FirstLaunchModal />);
    await waitFor(() => expect(screen.getByText('Welcome to Aurafractor')).toBeTruthy());

    await act(async () => {
      fireEvent.press(screen.getByRole('button', { name: /get started/i }));
    });

    expect(screen.queryByText('Welcome to Aurafractor')).toBeNull();
    const seen = await storage.getItem('first_launch_seen');
    expect(seen).toBe('1');
  });

  it('does not render when the seen flag is already set', async () => {
    await storage.setItem('first_launch_seen', '1');
    render(<FirstLaunchModal />);
    // Allow storage.getItem to resolve
    await act(async () => { await Promise.resolve(); });
    expect(screen.queryByText('Welcome to Aurafractor')).toBeNull();
  });
});
