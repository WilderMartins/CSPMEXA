// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// Mock localStorage para os testes, pois o JSDOM não o implementa completamente
const localStorageMock = (() => {
  let store: { [key: string]: string } = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock window.location.href para que possamos espioná-lo ou verificar atribuições
// Isso é útil porque o AuthContext e App.tsx modificam window.location.href
// para redirecionamentos.
const originalLocation = window.location;
delete (window as any).location;
window.location = Object.defineProperties(
  {},
  {
    ...Object.getOwnPropertyDescriptors(originalLocation),
    assign: {
      configurable: true,
      value: jest.fn(),
    },
    replace: {
      configurable: true,
      value: jest.fn(),
    },
    href: {
      writable: true, // Permite que window.location.href seja atribuído
      value: originalLocation.href,
    },
  }
) as Location;

// Mock para i18next usado nos componentes
jest.mock('react-i18next', () => ({
  useTranslation: () => {
    return {
      t: (str: string, params?: Record<string, any>) => {
        if (params) {
          let result = str;
          for (const key in params) {
            result = result.replace(`{{${key}}}`, params[key]);
          }
          return result;
        }
        return str;
      },
      i18n: {
        changeLanguage: () => new Promise(() => {}),
        language: 'en', // ou o idioma padrão que você usa
      },
    };
  },
}));

// Mock para import.meta.env
// No Vite, as variáveis de ambiente são acessadas via import.meta.env.
// O Jest não entende isso nativamente.
// Se você tiver VITE_API_BASE_URL em seu .env, você pode mocká-lo assim:
// (global as any).importMetaEnv = { VITE_API_BASE_URL: '/api/v1' };
// Ou, se você estiver definindo no vite.config.ts como fiz (define: { 'import.meta.env.VITE_API_BASE_URL': ... }),
// o ts-jest pode já lidar com isso, mas um mock explícito pode ser necessário dependendo da configuração.
// Por agora, vamos assumir que o código usa '/api/v1' como fallback se VITE_API_BASE_URL não estiver definido.

// Limpar mocks após cada teste para evitar interferência entre testes
afterEach(() => {
  localStorageMock.clear();
  jest.clearAllMocks();
});
