import React, { createContext, useState, useEffect, useContext, ReactNode } from 'react';
import axios from 'axios'; // Para buscar dados do usuário

/**
 * Interface para o objeto de usuário.
 * Contém informações básicas do usuário obtidas após o login.
 */
interface User {
  /** Identificador único do usuário. */
  user_id: string;
  /** Endereço de e-mail do usuário. */
  email: string;
  // Adicione outros campos do usuário conforme necessário (ex: name, picture, roles)
  // Estes viriam da resposta de /api/v1/users/me
}

/**
 * Define a forma do contexto de autenticação, incluindo o estado
 * e as funções para manipular a autenticação.
 */
interface AuthContextType {
  /** Verdadeiro se o usuário estiver autenticado, falso caso contrário. */
  isAuthenticated: boolean;
  /** Objeto contendo informações do usuário autenticado, ou null se não autenticado. */
  user: User | null;
  /** Token JWT do usuário autenticado, ou null. */
  token: string | null;
  /** Função para iniciar o processo de login (redireciona para o provedor OAuth). */
  login: () => void;
  /** Função para realizar o logout do usuário. */
  logout: () => void;
  /**
   * Manipula o callback do OAuth após o usuário ser redirecionado de volta do provedor.
   * @param tokenFromCallback O token JWT recebido do callback.
   * @returns Uma Promise que resolve quando o token é processado e o usuário é buscado.
   */
  handleOAuthCallback: (tokenFromCallback: string) => Promise<void>;
  /** Verdadeiro enquanto o estado inicial de autenticação ou os dados do usuário estão sendo carregados. */
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
});

/**
 * Provedor do Contexto de Autenticação.
 * Envolve a aplicação ou partes dela para fornecer acesso ao estado de autenticação
 * e funções relacionadas.
 *
 * @param props Props do componente, incluindo `children`.
 */
export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true); // Inicia como true

  useEffect(() => {
    const storedToken = localStorage.getItem('authToken');
    if (storedToken) {
      setToken(storedToken);
      apiClient.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
      fetchCurrentUser(storedToken);
    } else {
      setIsLoading(false); // Não há token, não está carregando usuário
    }
  }, []);

  const fetchCurrentUser = async (currentToken: string) => {
    setIsLoading(true);
    try {
      const response = await apiClient.get<User>('/users/me', {
        headers: {
          'Authorization': `Bearer ${currentToken}`
        }
      });
      setUser(response.data);
      setIsAuthenticated(true);
    } catch (error) {
      console.error('Failed to fetch user or token invalid:', error);
      // Token pode ser inválido/expirado, então limpa
      localStorage.removeItem('authToken');
      setToken(null);
      setUser(null);
      setIsAuthenticated(false);
      delete apiClient.defaults.headers.common['Authorization'];
    } finally {
      setIsLoading(false);
    }
  };

  const login = () => {
    // Redireciona para o endpoint de login do Google no backend/API Gateway
    // O backend cuidará do redirecionamento para o Google.
    window.location.href = `${import.meta.env.VITE_API_BASE_URL || '/api/v1'}/auth/google/login`;
  };

  const logout = () => {
    localStorage.removeItem('authToken');
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
    delete apiClient.defaults.headers.common['Authorization'];
    // Opcional: chamar um endpoint de logout no backend se existir
    // await apiClient.post('/auth/logout');
    window.location.href = '/'; // Redireciona para a página de login
  };

  const handleOAuthCallback = async (tokenFromCallback: string) => {
    localStorage.setItem('authToken', tokenFromCallback);
    setToken(tokenFromCallback);
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${tokenFromCallback}`;
    await fetchCurrentUser(tokenFromCallback);
    // O redirecionamento para /dashboard será tratado pela lógica de rotas no App.tsx
    // com base no estado isAuthenticated.
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, token, login, logout, handleOAuthCallback, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

/**
 * Hook customizado para acessar o AuthContext.
 * Fornece uma maneira fácil para os componentes consumirem o estado de autenticação
 * e as funções.
 *
 * @throws {Error} Se usado fora de um `AuthProvider`.
 * @returns O objeto do contexto de autenticação.
 */
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
