/**
 * TDD tests for shared UI components.
 */

import { render, screen, fireEvent } from '@testing-library/react-native';
import React from 'react';
import { LabelChip } from '../components/LabelChip';
import { StatusBadge } from '../components/StatusBadge';
import { ErrorView } from '../components/ErrorView';

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
