import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import ErrorMessage from './ErrorMessage';
import { MantineProvider } from '@mantine/core';

// Mock do i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback: string) => fallback || key,
  }),
}));

const renderWithMantine = (component: React.ReactElement) => {
  return render(<MantineProvider>{component}</MantineProvider>);
};

describe('ErrorMessage', () => {
  it('should render the message when provided', () => {
    renderWithMantine(<ErrorMessage message="Test error message" />);
    expect(screen.getByText('Test error message')).toBeInTheDocument();
  });

  it('should render the custom title when provided', () => {
    renderWithMantine(<ErrorMessage message="Test error" title="Custom Title" />);
    expect(screen.getByText('Custom Title')).toBeInTheDocument();
  });

  it('should render the default title when no title is provided', () => {
    renderWithMantine(<ErrorMessage message="Test error" />);
    expect(screen.getByText('An Error Occurred')).toBeInTheDocument();
  });

  it('should not render anything if the message is null', () => {
    const { container } = renderWithMantine(<ErrorMessage message={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('should call onClose when the close button is clicked', () => {
    const handleClose = jest.fn();
    renderWithMantine(<ErrorMessage message="Test error" onClose={handleClose} />);

    const closeButton = screen.getByRole('button'); // Mantine's close button has a role of 'button'
    fireEvent.click(closeButton);

    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('should not show a close button if onClose is not provided', () => {
    renderWithMantine(<ErrorMessage message="Test error" />);
    const closeButton = screen.queryByRole('button');
    expect(closeButton).not.toBeInTheDocument();
  });
});
