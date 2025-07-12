import React from 'react';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { AuthProvider, useAuth } from './AuthContext'; // Certifique-se que o caminho está correto

const mockApi = new MockAdapter(axios);

// Componente de teste para consumir o contexto
const TestConsumerComponent: React.FC = () => {
  const auth = useAuth();
  if (auth.isLoading) return <div>Auth Loading...</div>;
  return (
    <div>
      <div data-testid="isAuthenticated">{auth.isAuthenticated.toString()}</div>
      <div data-testid="user">{auth.user ? auth.user.email : 'null'}</div>
      <div data-testid="token">{auth.token || 'null'}</div>
      <button onClick={auth.login}>Login</button>
      <button onClick={auth.logout}>Logout</button>
      <button onClick={() => auth.handleOAuthCallback('test-token-from-callback')}>Handle Callback</button>
    </div>
  );
};

describe('AuthContext', () => {
  const originalLocation = window.location;

  beforeEach(() => {
    // Limpa mocks e localStorage antes de cada teste (já feito no setupTests.ts, mas bom garantir)
    localStorage.clear();
    mockApi.reset();
     // Restaurar window.location para um mock limpo antes de cada teste
    delete (window as any).location;
    window.location = { ...originalLocation, assign: jest.fn(), replace: jest.fn(), href: '' };
  });

   afterAll(() => {
    // Restaurar a implementação original de window.location após todos os testes
    window.location = originalLocation;
  });

  it('should have initial state as not authenticated', () => {
    render(
      <AuthProvider>
        <TestConsumerComponent />
      </AuthProvider>
    );
    expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('false');
    expect(screen.getByTestId('user')).toHaveTextContent('null');
    expect(screen.getByTestId('token')).toHaveTextContent('null');
  });

  it('login function should redirect to Google login URL', () => {
    render(
      <AuthProvider>
        <TestConsumerComponent />
      </AuthProvider>
    );
    act(() => {
      userEvent.click(screen.getByText('Login'));
    });
    // window.location.href é atribuído diretamente no AuthContext
    expect(window.location.href).toBe('/api/v1/auth/google/login');
  });

  it('logout function should clear auth state and redirect to /', async () => {
    // Simula um estado logado inicial
    localStorage.setItem('authToken', 'fake-token');
    mockApi.onGet('/api/v1/users/me').reply(200, { user_id: '1', email: 'test@example.com' });

    render(
      <AuthProvider>
        <TestConsumerComponent />
      </AuthProvider>
    );

    // Espera o carregamento do usuário
    await screen.findByText('test@example.com');
    expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');

    act(() => {
      userEvent.click(screen.getByText('Logout'));
    });

    expect(localStorage.getItem('authToken')).toBeNull();
    expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('false');
    expect(screen.getByTestId('user')).toHaveTextContent('null');
    expect(window.location.href).toBe('/');
  });

  it('handleOAuthCallback should set token, fetch user, and update state', async () => {
    const mockUser = { user_id: '123', email: 'user@example.com' };
    mockApi.onGet('/api/v1/users/me').reply(200, mockUser);

    render(
      <AuthProvider>
        <TestConsumerComponent />
      </AuthProvider>
    );

    // Garante que o estado inicial não autenticado seja renderizado primeiro
    expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('false');

    await act(async () => {
      // Não precisamos clicar no botão aqui, pois ele é apenas para o TestConsumerComponent.
      // Chamamos diretamente a função que seria exposta pelo hook `useAuth` se estivéssemos testando `App.tsx`
      // Aqui, estamos efetivamente testando a lógica interna do AuthProvider quando handleOAuthCallback é invocado.
      // Para simular o clique no botão do TestConsumerComponent:
      userEvent.click(screen.getByText('Handle Callback'));
    });

    // Espera que o mock da API seja chamado e o estado atualizado
    await screen.findByText(mockUser.email); // Espera que o email do usuário apareça

    expect(localStorage.getItem('authToken')).toBe('test-token-from-callback');
    expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
    expect(screen.getByTestId('user')).toHaveTextContent(mockUser.email);
    expect(screen.getByTestId('token')).toHaveTextContent('test-token-from-callback');
    expect(mockApi.history.get.length).toBe(1); // Verifica se a API /users/me foi chamada
    expect(mockApi.history.get[0].headers?.Authorization).toBe('Bearer test-token-from-callback');
  });

  it('should load token from localStorage and fetch user on initial load', async () => {
    localStorage.setItem('authToken', 'stored-token');
    const mockUser = { user_id: '456', email: 'storeduser@example.com' };
    mockApi.onGet('/api/v1/users/me').reply(200, mockUser);

    render(
      <AuthProvider>
        <TestConsumerComponent />
      </AuthProvider>
    );

    await screen.findByText(mockUser.email); // Espera que o usuário seja carregado

    expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
    expect(screen.getByTestId('user')).toHaveTextContent(mockUser.email);
    expect(screen.getByTestId('token')).toHaveTextContent('stored-token');
  });

  it('should clear auth state if fetching user fails on initial load', async () => {
    localStorage.setItem('authToken', 'invalid-token');
    mockApi.onGet('/api/v1/users/me').reply(401); // Simula falha na autenticação

    render(
      <AuthProvider>
        <TestConsumerComponent />
      </AuthProvider>
    );

    // Espera o estado de "Auth Loading..." desaparecer
    // e depois verifica se o estado foi limpo
    await screen.findByText('null', { selector: '[data-testid="user"]'});


    expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('false');
    expect(screen.getByTestId('user')).toHaveTextContent('null');
    expect(screen.getByTestId('token')).toHaveTextContent('null');
    expect(localStorage.getItem('authToken')).toBeNull();
  });
});
