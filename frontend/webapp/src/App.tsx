import './App.css' // Estilos específicos do App
import { Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next'; // Importar hook
import React from 'react';
import { Routes, Route, Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ReportsPage from './pages/ReportsPage'; // Importar a nova página de Relatórios
import { useAuth } from './contexts/AuthContext';

const OAuthCallbackPage = () => {
  const location = useLocation();
  const { t } = useTranslation();
  const auth = useAuth(); // Usar o contexto de autenticação
  const navigate = useNavigate(); // Para redirecionamento programático

  React.useEffect(() => {
    const params = new URLSearchParams(location.search);
    const token = params.get('token');
    const error = params.get('error');

    if (token) {
      auth.handleOAuthCallback(token)
        .then(() => {
          navigate('/dashboard', { replace: true });
        })
        .catch(err => {
          console.error("Error during OAuth callback handling:", err);
          navigate('/?error=' + encodeURIComponent(t('oauthCallback.errorProcessing')), { replace: true });
        });
    } else if (error) {
      console.error("OAuth Error:", error);
      navigate('/?error=' + encodeURIComponent(t('oauthCallback.error', { error })), { replace: true });
    } else {
      console.warn("OAuth callback sem token ou erro.");
      navigate('/?error=' + encodeURIComponent(t('oauthCallback.invalidCallback')), { replace: true });
    }
  }, [location, auth, t, navigate]);

  return <div>{t('oauthCallback.processing')}</div>;
};


function App() {
  const auth = useAuth(); // Usar o hook useAuth
  const { t, i18n } = useTranslation();

  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
  };

  if (auth.isLoading) {
    // Você pode retornar um spinner/loader de tela inteira aqui
    return <div className="loading-fullscreen">{t('loading')}</div>;
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>{t('header.title')}</h1>
        <nav>
          {!auth.isAuthenticated && <Link to="/">{t('header.navLogin')}</Link>}
          {auth.isAuthenticated && (
            <>
              <Link to="/dashboard" style={{ marginRight: '15px' }}>{t('header.navDashboard')}</Link>
              <Link to="/reports" style={{ marginRight: '15px' }}>{t('header.navReports')}</Link>
            </>
          )}
          {auth.isAuthenticated && <button onClick={() => auth.logout()}>{t('header.btnLogout')}</button>}
        </nav>
        <div className="language-selector" style={{ color: "white", marginLeft: "20px" }}>
          <button onClick={() => changeLanguage('en')} disabled={i18n.language === 'en'}>EN</button>
          <button onClick={() => changeLanguage('pt-BR')} disabled={i18n.language === 'pt-BR'}>PT-BR</button>
        </div>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={!auth.isAuthenticated ? <LoginPage /> : <Navigate to="/dashboard" replace />} />
          <Route path="/auth/callback" element={<OAuthCallbackPage />} />

          <Route
            path="/dashboard"
            element={auth.isAuthenticated ? <DashboardPage /> : <Navigate to="/" replace />}
          />
          <Route
            path="/reports"
            element={auth.isAuthenticated ? <ReportsPage /> : <Navigate to="/" replace />}
          />
          {/* Adicionar aqui outras rotas protegidas que dependem de auth.isAuthenticated */}

          {/* Rota catch-all para redirecionar usuários não autenticados para login, e autenticados para dashboard */}
          <Route path="*" element={<Navigate to={auth.isAuthenticated ? "/dashboard" : "/"} replace />} />
        </Routes>
      </main>
      <footer className="app-footer">
        <p>{t('footer.copyright', { year: new Date().getFullYear() })}</p>
      </footer>
    </div>
  )
}

export default App
