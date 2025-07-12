import React from 'react';
import { useTranslation } from 'react-i18next';
import { NavLink, Routes, Route, Navigate } from 'react-router-dom';
import { Title, Paper, Group, NavLink as MantineNavLink } from '@mantine/core';
import { IconBell, IconUserShield } from '@tabler/icons-react';
import NotificationSettingsPage from './Settings/NotificationSettingsPage';
// import UserManagementPage from './Settings/UserManagementPage';

/**
 * `SettingsPage` atua como um layout e roteador para as várias sub-páginas de configurações,
 * como Notificações e Gerenciamento de Usuários.
 *
 * @component
 */
const SettingsPage: React.FC = () => {
  const { t } = useTranslation();

  return (
    <div className="settings-page">
      <Title order={1} mb="xl">{t('settings.title', 'Settings')}</Title>
      <Group align="flex-start">
        <Paper withBorder p="md" radius="md" style={{ width: 220 }}>
            <MantineNavLink
                label={t('settings.menu.notifications', 'Notifications')}
                component={NavLink}
                to="/settings/notifications"
                leftSection={<IconBell size={20} />}
            />
             <MantineNavLink
                label={t('settings.menu.users', 'User Management')}
                component={NavLink}
                to="/settings/users"
                leftSection={<IconUserShield size={20} />}
            />
        </Paper>
        <div style={{ flex: 1 }}>
            <Routes>
                <Route path="notifications" element={<NotificationSettingsPage />} />
                {/*
                  As rotas abaixo serão descomentadas à medida que as páginas forem criadas.
                  <Route path="users" element={<UserManagementPage />} />
                */}
                 <Route path="/" element={<Navigate to="/settings/notifications" replace />} />
            </Routes>
        </div>
      </Group>
    </div>
  );
};

export default SettingsPage;
