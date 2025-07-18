import './App.css' // Estilos específicos do App
import { Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next'; // Importar hook
import React, { Suspense, lazy } from 'react';
import { Routes, Route, Link, Navigate, useLocation, useNavigate, NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AppShell, Burger, Group, UnstyledButton, Text, Box, Anchor, Button as MantineButton, Loader, Center, NavLink as MantineNavLink } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconGauge, IconChartInfographic, IconBulb, IconSettings, IconKey, IconBrandAws, IconBrandGoogle, IconCloud, IconBrandWindows, IconBuildingStore, IconBox } from '@tabler/icons-react';
import { useAuth } from './contexts/AuthContext';
import { useAccount } from './contexts/AccountContext';

// Lazy load das páginas principais
const LoginPage = lazy(() => import('./pages/LoginPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const ReportsPage = lazy(() => import('./pages/ReportsPage'));
const InsightsPage = lazy(() => import('./pages/InsightsPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const CredentialsPage = lazy(() => import('./pages/Admin/CredentialsPage')); // Adicionado
const AccessDeniedPage = lazy(() => import('./pages/AccessDeniedPage'));
const NotificationsPage = lazy(() => import('./pages/Admin/NotificationsPage'));
const LinkedAccountsPage = lazy(() => import('./pages/Admin/LinkedAccountsPage'));
const InventoryPage = lazy(() => import('./pages/InventoryPage'));
const AttackPathsPage = lazy(() => import('./pages/AttackPathsPage'));
const RemediationsPage = lazy(() => import('./pages/Admin/RemediationsPage'));

// Componentes de rota não precisam de lazy load
import ProtectedRoute from './components/Common/ProtectedRoute';

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
  const { accounts, selectedAccountId, setSelectedAccountId } = useAccount();
  const { t, i18n } = useTranslation();

  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
  };

  if (auth.isLoading) {
    return (
      <Center style={{ height: '100vh' }}>
        <Loader size="xl" />
      </Center>
    );
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

  const mainLinks = [
    { icon: <IconGauge size={22} />, label: t('header.navDashboard', 'Dashboard'), to: '/dashboard' },
    { icon: <IconChartInfographic size={22} />, label: t('header.navReports', 'Reports'), to: '/reports' },
    { icon: <IconBulb size={22} />, label: t('header.navInsights', 'Insights'), to: '/insights' },
    { icon: <IconSettings size={22} />, label: t('header.navSettings', 'Settings'), to: '/settings' },
    { icon: <IconKey size={22} />, label: t('header.navCredentials', 'Credentials'), to: '/settings/credentials' }, // Adicionado
  ];

  const providerLinks = [
      { icon: <IconBrandAws size={20} />, label: 'AWS', to: '/dashboard/aws' },
      { icon: <IconBrandGoogle size={20} />, label: 'GCP', to: '/dashboard/gcp' },
      { icon: <IconCloud size={20} />, label: 'Azure', to: '/dashboard/azure' },
      { icon: <IconBox size={20} />, label: 'Huawei Cloud', to: '/dashboard/huawei' },
      { icon: <IconBrandWindows size={20} />, label: 'Microsoft 365', to: '/dashboard/microsoft365' },
      { icon: <IconBuildingStore size={20} />, label: 'Google Workspace', to: '/dashboard/google-workspace' },
  ];

  const createNavLink = (link: {icon: JSX.Element, label: string, to: string}) => (
     <MantineNavLink
      key={link.label}
      component={NavLink}
      to={link.to}
      label={link.label}
      leftSection={link.icon}
      onClick={() => toggle()} // Fecha o navbar mobile ao clicar
      styles={(theme) => ({
        root: { borderRadius: theme.radius.sm },
        label: { fontSize: '1rem' },
        body: {
            '&[data-active]': {
                '&, &:hover': {
                    backgroundColor: theme.fn.variant({ variant: 'filled', color: theme.primaryColor }).background,
                    color: theme.white,
                },
            },
        }
      })}
    />
  );

  const mainNavLinks = mainLinks.map(createNavLink);
  const providerNavLinks = providerLinks.map(createNavLink);


  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{ width: 280, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            {auth.isAuthenticated && <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />}
            <Text size="xl" fw={700}>{t('header.title')}</Text>
          </Group>

          <Group>
             {auth.isAuthenticated && (
              <>
                <Select
                  placeholder="Selecione uma conta"
                  value={selectedAccountId ? String(selectedAccountId) : null}
                  onChange={(value) => setSelectedAccountId(value ? Number(value) : null)}
                  data={accounts.map(acc => ({ value: String(acc.id), label: acc.name }))}
                  disabled={accounts.length === 0}
                />
              <MantineButton variant="light" onClick={() => auth.logout()}>
                {t('header.btnLogout')}
              </MantineButton>
              </>
            )}
            <Group gap="xs" ml="lg">
              <MantineButton variant={i18n.language === 'en' ? "filled" : "default"} size="xs" onClick={() => changeLanguage('en')}>EN</MantineButton>
              <MantineButton variant={i18n.language === 'pt-BR' ? "filled" : "default"} size="xs" onClick={() => changeLanguage('pt-BR')}>PT-BR</MantineButton>
            </Group>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="md">
        <Box>
            <Text tt="uppercase" size="xs" c="dimmed" fw={500} mb="sm">{t('navbar.mainMenu', 'Main Menu')}</Text>
            {mainNavLinks}
        </Box>
        <Box mt="md">
            <Text tt="uppercase" size="xs" c="dimmed" fw={500} mb="sm">{t('navbar.providersMenu', 'Providers')}</Text>
            {providerNavLinks}
        </Box>
      </AppShell.Navbar>

      <AppShell.Main>
        <Suspense fallback={<Center style={{ height: '100%' }}><Loader /></Center>}>
            <Routes>
              <Route path="/" element={!auth.isAuthenticated ? <LoginPage /> : <Navigate to="/dashboard" replace />} />
              <Route path="/auth/callback" element={<OAuthCallbackPage />} />
              <Route path="/dashboard/*" element={auth.isAuthenticated ? <DashboardPage /> : <Navigate to="/" replace />} />
              <Route path="/reports" element={auth.isAuthenticated ? <ReportsPage /> : <Navigate to="/" replace />} />
              <Route path="/insights" element={auth.isAuthenticated ? <InsightsPage /> : <Navigate to="/" replace />} />
              <Route path="/settings" element={
                  <ProtectedRoute requiredRole="Administrator">
                    <SettingsPage />
                  </ProtectedRoute>
                } />
              <Route path="/settings/credentials" element={
                  <ProtectedRoute requiredRole="Administrator">
                    <CredentialsPage />
                  </ProtectedRoute>
                } />
               <Route path="/settings/notifications" element={
                  <ProtectedRoute requiredRole="Administrator">
                    <NotificationsPage />
                  </ProtectedRoute>
                } />
                <Route path="/settings/accounts" element={
                  <ProtectedRoute requiredRole="Administrator">
                    <LinkedAccountsPage />
                  </ProtectedRoute>
                } />
              <Route path="/remediations" element={
                  <ProtectedRoute requiredRole="Manager">
                    <RemediationsPage />
                  </ProtectedRoute>
                } />
              <Route path="/inventory" element={auth.isAuthenticated ? <InventoryPage /> : <Navigate to="/" replace />} />
              <Route path="/attack-paths" element={auth.isAuthenticated ? <AttackPathsPage /> : <Navigate to="/" replace />} />
              <Route path="/access-denied" element={<AccessDeniedPage />} />
              <Route path="*" element={<Navigate to={auth.isAuthenticated ? "/dashboard" : "/"} replace />} />
            </Routes>
        </Suspense>
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
