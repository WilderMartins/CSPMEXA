import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import HttpBackend from 'i18next-http-backend';
import LanguageDetector from 'i18next-browser-languagedetector';

i18n
  // Carrega traduções usando http backend (ex: de public/locales)
  .use(HttpBackend)
  // Detecta o idioma do usuário
  .use(LanguageDetector)
  // Passa a instância i18n para react-i18next.
  .use(initReactI18next)
  // Inicializa i18next
  .init({
    fallbackLng: 'en', // Idioma padrão se o idioma do usuário não estiver disponível
    debug: process.env.NODE_ENV === 'development', // Logs no console em desenvolvimento
    interpolation: {
      escapeValue: false, // React já faz escaping por padrão
    },
    backend: {
      // Path para carregar os arquivos de tradução
      loadPath: '/locales/{{lng}}/{{ns}}.json',
    },
    // ns: ['translation'], // Namespaces, 'translation' é o padrão
    // defaultNS: 'translation',
  });

export default i18n;
