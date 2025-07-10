import './App.css' // Estilos específicos do App
import { Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next'; // Importar hook
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
// OAuthCallbackPage está definido dentro deste arquivo por enquanto
// import { useAuth } from './contexts/AuthContext' // Será criado

// Componentes placeholder para as páginas - REMOVIDOS
// const LoginPagePlaceholder = () => <div>LoginPage Placeholder <br/> <a href="/api/v1/auth/google/login">Login com Google (Gateway)</a> </div>;
// const DashboardPagePlaceholder = () => <div>DashboardPage Placeholder</div>;

// Placeholder para o hook useAuth
const useAuthPlaceholder = () => {
  const token = localStorage.getItem('authToken');
  return { token, isAuthenticated: !!token };
};

const OAuthCallbackPage = () => {
  const location = useLocation();
  const { t } = useTranslation(); // Hook de tradução

  React.useEffect(() => {
    const params = new URLSearchParams(location.search);
    const token = params.get('token');
    const error = params.get('error');

    if (token) {
      localStorage.setItem('authToken', token);
      window.location.href = '/dashboard';
    } else if (error) {
      console.error("OAuth Error:", error);
      // Usar t() para a mensagem de erro, embora esta página seja breve
      window.location.href = '/?error=' + encodeURIComponent(t('oauthCallback.error', { error }));
    } else {
      console.warn("OAuth callback sem token ou erro.");
      window.location.href = '/?error=' + encodeURIComponent(t('oauthCallback.invalidCallback'));
    }
  }, [location, t]);

  return <div>{t('oauthCallback.processing')}</div>;
};


function App() {
  const { isAuthenticated } = useAuthPlaceholder();
  const { t, i18n } = useTranslation(); // Hook de tradução

  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>{t('header.title')}</h1>
        <nav>
          {!isAuthenticated && <Link to="/">{t('header.navLogin')}</Link>}
          {isAuthenticated && <Link to="/dashboard">{t('header.navDashboard')}</Link>}
          {isAuthenticated && <button onClick={() => {
            localStorage.removeItem('authToken');
            window.location.href = '/';
          }}>{t('header.btnLogout')}</button>}
        </nav>
        <div className="language-selector" style={{ color: "white", marginLeft: "20px" }}>
          <button onClick={() => changeLanguage('en')} disabled={i18n.language === 'en'}>EN</button>
          <button onClick={() => changeLanguage('pt-BR')} disabled={i18n.language === 'pt-BR'}>PT-BR</button>
        </div>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={!isAuthenticated ? <LoginPage /> : <Navigate to="/dashboard" replace />} />
          <Route path="/auth/callback" element={<OAuthCallbackPage />} />

          <Route
            path="/dashboard"
            element={isAuthenticated ? <DashboardPage /> : <Navigate to="/" replace />}
          />

          <Route path="*" element={<Navigate to={isAuthenticated ? "/dashboard" : "/"} replace />} />
        </Routes>
      </main>
      <footer className="app-footer">
        <p>{t('footer.copyright', { year: new Date().getFullYear() })}</p>
      </footer>
    </div>
  )
}

export default App
