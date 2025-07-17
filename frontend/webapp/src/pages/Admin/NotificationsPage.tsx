import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Container, Title, Tabs } from '@mantine/core';
import ManageChannels from '../../components/Settings/ManageChannels';
import ManageRules from '../../components/Settings/ManageRules';

const NotificationsPage: React.FC = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<string | null>('channels');

  return (
    <Container fluid>
      <Title order={2} mb="lg">{t('notificationsPage.title', 'Gerenciamento de Notificações')}</Title>

      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tabs.List>
          <Tabs.Tab value="channels">
            {t('notificationsPage.tabs.channels', 'Canais de Notificação')}
          </Tabs.Tab>
          <Tabs.Tab value="rules">
            {t('notificationsPage.tabs.rules', 'Regras de Notificação')}
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="channels" pt="lg">
          <ManageChannels />
        </Tabs.Panel>

        <Tabs.Panel value="rules" pt="lg">
          <ManageRules />
        </Tabs.Panel>
      </Tabs>
    </Container>
  );
};

export default NotificationsPage;
