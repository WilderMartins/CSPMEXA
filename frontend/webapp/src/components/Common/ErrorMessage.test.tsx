// import React from 'react';
// import { render, screen, fireEvent } from '@testing-library/react';
// import ErrorMessage from './ErrorMessage';

// describe('ErrorMessage', () => {
//   it('should not render when message is null', () => {
//     const { container } = render(<ErrorMessage message={null} onClose={() => {}} />);
//     expect(container.firstChild).toBeNull();
//   });

//   it('should render when message is provided', () => {
//     render(<ErrorMessage message="Test error" onClose={() => {}} />);
//     expect(screen.getByText(/Test error/i)).toBeInTheDocument();
//   });

//   it('should call onClose when the close button is clicked', () => {
//     const onClose = jest.fn();
//     render(<ErrorMessage message="Test error" onClose={onClose} />);
//     fireEvent.click(screen.getByRole('button'));
//     expect(onClose).toHaveBeenCalledTimes(1);
//   });
// });
it.todo('should be tested');
