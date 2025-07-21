// import React from 'react';
// import { render, screen, fireEvent, waitFor } from '@testing-library/react';
// import { MemoryRouter } from 'react-router-dom';
// import LoginPage from '../pages/LoginPage';
// import { AuthProvider } from '../contexts/AuthContext';
// import { api } from '../services/api';
// import MockAdapter from 'axios-mock-adapter';

// const mock = new MockAdapter(api);

// describe('LoginPage', () => {
//   it('should login successfully and redirect', async () => {
//     mock.onPost('/auth/login').reply(200, { access_token: 'fake-token' });

//     render(
//       <MemoryRouter>
//         <AuthProvider>
//           <LoginPage />
//         </AuthProvider>
//       </MemoryRouter>
//     );

//     fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'test@example.com' } });
//     fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'password' } });
//     fireEvent.click(screen.getByRole('button', { name: /login/i }));

//     await waitFor(() => {
//       expect(window.location.href).toBe('/dashboard');
//     });
//   });
// });
it.todo('should be tested');
