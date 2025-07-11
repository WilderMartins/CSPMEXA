import React from 'react';
import { useLocation } from 'react-router-dom'; // useNavigate não é usado aqui
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import { Paper, Title, Text, Button as MantineButton, Center, Stack } from '@mantine/core'; // Importar componentes Mantine

const LoginPage: React.FC = () => {
  const { t } = useTranslation();
  const location = useLocation();
  const auth = useAuth();

  const queryParams = new URLSearchParams(location.search);
  const error = queryParams.get('error');

  const handleLogin = () => {
    auth.login();
  };

  return (
    <Center style={{ height: 'calc(100vh - 120px)' }}> {/* 120px para header e footer do AppShell */}
      <Paper withBorder shadow="md" p={30} radius="md" style={{minWidth: '350px', maxWidth: '450px'}}>
        <Stack gap="lg">
          <Title order={2} ta="center">
            {t('loginPage.title')}
          </Title>

          {error && (
            <Text c="red" ta="center" size="sm">
              {t('loginPage.errorMessage', { error: decodeURIComponent(error) })}
            </Text>
          )}

          <Text ta="center" size="sm" c="dimmed">
            {t('loginPage.greeting')}
          </Text>

          <MantineButton onClick={handleLogin} fullWidth variant="filled" size="lg">
            {t('loginPage.button')}
          </MantineButton>

          <Text ta="center" size="xs" c="dimmed">
            {t('loginPage.redirectMessage')}
          </Text>
        </Stack>
      </Paper>
    </Center>
  );
};

export default LoginPage;
