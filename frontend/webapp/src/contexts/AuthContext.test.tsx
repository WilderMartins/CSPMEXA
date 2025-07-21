// import React from 'react';
// import { render, screen, act } from '@testing-library/react';
// import { AuthProvider, useAuth } from './AuthContext';

// const TestComponent = () => {
//   const { isAuthenticated, login, logout } = useAuth();
//   return (
//     <div>
//       <span>{isAuthenticated ? 'Authenticated' : 'Not Authenticated'}</span>
//       <button onClick={() => login('fake-token')}>Login</button>
//       <button onClick={logout}>Logout</button>
//     </div>
//   );
// };

// describe('AuthContext', () => {
//   it('should be not authenticated by default', () => {
//     render(
//       <AuthProvider>
//         <TestComponent />
//       </AuthProvider>
//     );
//     expect(screen.getByText(/Not Authenticated/i)).toBeInTheDocument();
//   });

//   it('should be authenticated after login', () => {
//     render(
//       <AuthProvider>
//         <TestComponent />
//       </AuthProvider>
//     );
//     act(() => {
//       screen.getByText(/Login/i).click();
//     });
//     expect(screen.getByText(/Authenticated/i)).toBeInTheDocument();
//   });

//   it('should be not authenticated after logout', () => {
//     render(
//       <AuthProvider>
//         <TestComponent />
//       </AuthProvider>
//     );
//     act(() => {
//       screen.getByText(/Login/i).click();
//     });
//     act(() => {
//       screen.getByText(/Logout/i).click();
//     });
//     expect(screen.getByText(/Not Authenticated/i)).toBeInTheDocument();
//   });
// });
it.todo('should be tested');
