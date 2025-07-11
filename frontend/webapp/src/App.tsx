import './App.css' // Estilos específicos do App
import { Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next'; // Importar hook
import React from 'react';
import { Routes, Route, Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AppShell, Burger, Group, UnstyledButton, Text, Box, Anchor, Button as MantineButton } from '@mantine/core'; // Importar AppShell e outros
import { useDisclosure } from '@mantine/hooks';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ReportsPage from './pages/ReportsPage';
import InsightsPage from './pages/InsightsPage';
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
  const [opened, { toggle }] = useDisclosure(false); // Para o Navbar mobile
  const auth = useAuth();
  const { t, i18n } = useTranslation();

  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
  };

  if (auth.isLoading) {
    // TODO: Usar um Loader da Mantine aqui
    return <div className="loading-fullscreen" style={{display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh'}}>{t('loading')}</div>;
  }

  const navLinkStyle = (isActive?: boolean) => ({ // Estilo para links de navegação, pode ser melhorado com NavLink do react-router
    padding: '8px 12px',
    borderRadius: '4px',
    textDecoration: 'none',
    color: isActive ? 'var(--mantine-color-blue-filled)' : 'var(--mantine-color-text)',
    fontWeight: isActive ? 700 : 500,
    '&:hover': {
      backgroundColor: 'var(--mantine-color-gray-1)',
    },
  });


  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{ width: 250, breakpoint: 'sm', collapsed: { mobile: !opened, desktop: true } }} // Navbar será usado se quisermos links laterais no futuro
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          {/* Burger para Navbar mobile - pode ser removido se não houver Navbar lateral */}
          {/* <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" /> */}

          <Text size="xl" fw={700}>{t('header.title')}</Text>

          <Group>
            <nav>
              <Group gap="sm">
                {!auth.isAuthenticated && (
                  <Anchor component={Link} to="/" style={navLinkStyle()}>
                    {t('header.navLogin')}
                  </Anchor>
                )}
                {auth.isAuthenticated && (
                  <>
                    <Anchor component={Link} to="/dashboard" style={navLinkStyle()}>
                      {t('header.navDashboard')}
                    </Anchor>
                    <Anchor component={Link} to="/reports" style={navLinkStyle()}>
                      {t('header.navReports')}
                    </Anchor>
                    <Anchor component={Link} to="/insights" style={navLinkStyle()}>
                      {t('header.navInsights', 'Insights')}
                    </Anchor>
                  </>
                )}
              </Group>
            </nav>

            {auth.isAuthenticated && (
              <MantineButton variant="light" onClick={() => auth.logout()}>
                {t('header.btnLogout')}
              </MantineButton>
            )}

            <Group gap="xs" ml="lg">
              <MantineButton variant={i18n.language === 'en' ? "filled" : "default"} size="xs" onClick={() => changeLanguage('en')}>EN</MantineButton>
              <MantineButton variant={i18n.language === 'pt-BR' ? "filled" : "default"} size="xs" onClick={() => changeLanguage('pt-BR')}>PT-BR</MantineButton>
            </Group>
          </Group>
        </Group>
      </AppShell.Header>

      {/* AppShell.Navbar - pode ser adicionado aqui se necessário no futuro */}
      {/* <AppShell.Navbar p="md">Navbar</AppShell.Navbar> */}

      <AppShell.Main>
        <Routes>
          <Route path="/" element={!auth.isAuthenticated ? <LoginPage /> : <Navigate to="/dashboard" replace />} />
          <Route path="/auth/callback" element={<OAuthCallbackPage />} />
          <Route path="/dashboard" element={auth.isAuthenticated ? <DashboardPage /> : <Navigate to="/" replace />} />
          <Route path="/reports" element={auth.isAuthenticated ? <ReportsPage /> : <Navigate to="/" replace />} />
          <Route path="/insights" element={auth.isAuthenticated ? <InsightsPage /> : <Navigate to="/" replace />} />
          <Route path="*" element={<Navigate to={auth.isAuthenticated ? "/dashboard" : "/"} replace />} />
        </Routes>
      </AppShell.Main>

      <AppShell.Footer p="md" style={{textAlign: 'center'}}>
        <Text size="sm" c="dimmed">
          {t('footer.copyright', { year: new Date().getFullYear() })}
        </Text>
      </AppShell.Footer>
    </AppShell>
  );
}

export default App;
