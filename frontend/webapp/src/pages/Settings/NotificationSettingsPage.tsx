import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Title, Paper, TextInput, Button, Table, ActionIcon, Group, Text } from '@mantine/core';
import { IconTrash, IconPlus } from '@tabler/icons-react';
import { useAuth } from '../../contexts/AuthContext';
// import axios from 'axios'; // Será usado quando a API estiver pronta

// Tipos mockados - substituir pelos tipos reais da API quando disponíveis
interface Webhook {
  id: string;
  name: string;
  url: string;
}

const NotificationSettingsPage: React.FC = () => {
  const { t } = useTranslation();
  const auth = useAuth();
  const [emails, setEmails] = useState<string[]>(['admin@example.com']);
  const [newEmail, setNewEmail] = useState<string>('');
  const [webhooks, setWebhooks] = useState<Webhook[]>([
    { id: '1', name: 'Slack #general', url: 'https://hooks.slack.com/services/...' },
    { id: '2', name: 'Internal Logger', url: 'https://my-internal-logger.com/hooks/...' }
  ]);
  const [googleChatWebhooks, setGoogleChatWebhooks] = useState<Webhook[]>([]);

  // TODO: Implementar chamadas de API para buscar e salvar configurações
  useEffect(() => {
    // Exemplo de como a busca de dados funcionaria
    // const fetchConfig = async () => {
    //   const response = await apiClient.get('/notifications/config');
    //   setEmails(response.data.emails);
    //   setWebhooks(response.data.webhooks);
    //   setGoogleChatWebhooks(response.data.googleChatWebhooks);
    // };
    // fetchConfig();
  }, []);

  const handleAddEmail = () => {
    if (newEmail && !emails.includes(newEmail)) {
      // TODO: Chamar API para adicionar e-mail
      setEmails([...emails, newEmail]);
      setNewEmail('');
    }
  };

  const handleRemoveEmail = (emailToRemove: string) => {
    // TODO: Chamar API para remover e-mail
    setEmails(emails.filter(email => email !== emailToRemove));
  };

  const webhookRows = webhooks.map((hook) => (
    <Table.Tr key={hook.id}>
      <Table.Td>{hook.name}</Table.Td>
      <Table.Td>{hook.url}</Table.Td>
      <Table.Td>
        <ActionIcon color="red">
          <IconTrash size={16} />
        </ActionIcon>
      </Table.Td>
    </Table.Tr>
  ));

  return (
    <Paper withBorder p="xl" radius="md">
      <Title order={2} mb="lg">{t('settings.notifications.title', 'Notification Settings')}</Title>

      {/* Seção de E-mail */}
      <section>
        <Title order={4} mb="md">{t('settings.notifications.email.title', 'Email Recipients')}</Title>
        <Text size="sm" c="dimmed" mb="md">
          {t('settings.notifications.email.description', 'Add email addresses to receive critical alert notifications.')}
        </Text>
        <Table>
          <Table.Tbody>
            {emails.map(email => (
              <Table.Tr key={email}>
                <Table.Td>{email}</Table.Td>
                <Table.Td align="right">
                  <ActionIcon color="red" onClick={() => handleRemoveEmail(email)}>
                    <IconTrash size={16} />
                  </ActionIcon>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        <Group mt="md">
          <TextInput
            placeholder={t('settings.notifications.email.placeholder', 'new.email@example.com')}
            value={newEmail}
            onChange={(e) => setNewEmail(e.currentTarget.value)}
            style={{ flex: 1 }}
          />
          <Button onClick={handleAddEmail} leftSection={<IconPlus size={16} />}>
            {t('settings.notifications.email.addButton', 'Add Email')}
          </Button>
        </Group>
      </section>

      {/* Seção de Webhooks */}
      <section style={{marginTop: '2rem'}}>
        <Title order={4} mb="md">{t('settings.notifications.webhook.title', 'Webhooks')}</Title>
        <Text size="sm" c="dimmed" mb="md">
            {t('settings.notifications.webhook.description', 'Configure webhook URLs to receive alert data as JSON payloads.')}
        </Text>
        <Table>
            <Table.Thead>
                <Table.Tr>
                    <Table.Th>{t('settings.notifications.webhook.tableNameHeader', 'Name')}</Table.Th>
                    <Table.Th>{t('settings.notifications.webhook.tableUrlHeader', 'URL')}</Table.Th>
                    <Table.Th />
                </Table.Tr>
            </Table.Thead>
            <Table.Tbody>{webhookRows}</Table.Tbody>
        </Table>
         <Button mt="md" variant="light" leftSection={<IconPlus size={16} />}>
            {t('settings.notifications.webhook.addButton', 'Add Webhook')}
        </Button>
      </section>

       {/* Seção de Google Chat */}
      <section style={{marginTop: '2rem'}}>
        <Title order={4} mb="md">{t('settings.notifications.gchat.title', 'Google Chat Webhooks')}</Title>
         <Text size="sm" c="dimmed" mb="md">
            {t('settings.notifications.gchat.description', 'Configure Google Chat webhooks to receive formatted alert cards in your spaces.')}
        </Text>
        {googleChatWebhooks.length > 0 ? (
            <Text>...</Text> // Tabela similar a de webhooks aqui
        ) : (
            <Text size="sm" c="dimmed">{t('settings.notifications.gchat.noWebhooks', 'No Google Chat webhooks configured.')}</Text>
        )}
         <Button mt="md" variant="light" leftSection={<IconPlus size={16} />}>
            {t('settings.notifications.gchat.addButton', 'Add Google Chat Webhook')}
        </Button>
      </section>

    </Paper>
  );
};

export default NotificationSettingsPage;
