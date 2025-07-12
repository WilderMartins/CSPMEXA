import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Title, Paper, TextInput, Button, Table, ActionIcon, Group, Text } from '@mantine/core';
import { IconTrash, IconPlus } from '@tabler/icons-react';
import { useAuth } from '../../contexts/AuthContext';
import axios, { AxiosInstance } from 'axios';
import ErrorMessage from '../../components/Common/ErrorMessage';
import { Skeleton, useMantineTheme, Modal } from '@mantine/core'; // Adicionar imports
import { useDisclosure } from '@mantine/hooks';

// Tipos de dados da API
interface Webhook {
  id: number;
  name: string;
  url: string;
  provider: 'generic' | 'google_chat';
}

interface NotificationConfig {
  emails: { id: number; address: string }[];
  webhooks: Webhook[];
}

const NotificationSettingsPage: React.FC = () => {
  const { t } = useTranslation();
  const { token } = useAuth();
  const theme = useMantineTheme();

  // Estado da UI
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Estado dos dados
  const [emails, setEmails] = useState<NotificationConfig['emails']>([]);
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [googleChatWebhooks, setGoogleChatWebhooks] = useState<Webhook[]>([]);

  // Estado para modais
  const [newEmail, setNewEmail] = useState<string>('');
  const [newWebhook, setNewWebhook] = useState<{name: string, url: string, provider: 'generic' | 'google_chat'}>({name: '', url: '', provider: 'generic'});
  const [webhookModalOpened, { open: openWebhookModal, close: closeWebhookModal }] = useDisclosure(false);
  const [gchatModalOpened, { open: openGchatModal, close: closeGchatModal }] = useDisclosure(false);

  const apiClient = useMemo<AxiosInstance>(() => {
    return axios.create({
      baseURL: `${import.meta.env.VITE_API_BASE_URL || '/api/v1'}/notifications`,
      headers: { 'Authorization': `Bearer ${token}` }
    });
  }, [token]);

  const fetchConfig = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<NotificationConfig>('/config');
      const config = response.data;
      setEmails(config.emails || []);
      setWebhooks(config.webhooks.filter(wh => wh.provider === 'generic') || []);
      setGoogleChatWebhooks(config.webhooks.filter(wh => wh.provider === 'google_chat') || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch notification settings.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, [apiClient]);

  const handleAddEmail = async () => {
    const emailToAdd = newEmail.trim();
    if (!emailToAdd || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailToAdd)) {
        setError('Please enter a valid email address.');
        return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
        await apiClient.post('/config/emails', { address: emailToAdd });
        await fetchConfig(); // Re-fetch para obter a lista atualizada com IDs
        setNewEmail('');
    } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to add email.');
    } finally {
        setIsSubmitting(false);
    }
  };

  const handleRemoveEmail = async (emailId: number) => {
    setIsSubmitting(true);
    setError(null);
    try {
        await apiClient.delete(`/config/emails/${emailId}`);
        setEmails(prev => prev.filter(email => email.id !== emailId));
    } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to remove email.');
    } finally {
        setIsSubmitting(false);
    }
  };

  const handleAddWebhook = async () => {
    const { name, url, provider } = newWebhook;
    if (!name.trim() || !url.trim()) {
        setError('Webhook name and URL are required.');
        return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
        await apiClient.post('/config/webhooks', { name, url, provider });
        await fetchConfig();
        closeWebhookModal();
        closeGchatModal();
        setNewWebhook({name: '', url: '', provider: 'generic'});
    } catch (err: any) {
        setError(err.response?.data?.detail || `Failed to add ${provider} webhook.`);
    } finally {
        setIsSubmitting(false);
    }
  };

  const handleRemoveWebhook = async (webhookId: number) => {
      setIsSubmitting(true);
      setError(null);
      try {
          await apiClient.delete(`/config/webhooks/${webhookId}`);
          await fetchConfig(); // Re-fetch para atualizar ambas as listas de webhooks
      } catch (err: any) {
          setError(err.response?.data?.detail || 'Failed to remove webhook.');
      } finally {
          setIsSubmitting(false);
      }
  };

  const renderWebhookRows = (hooks: Webhook[]) => hooks.map((hook) => (
    <Table.Tr key={hook.id}>
      <Table.Td>{hook.name}</Table.Td>
      <Table.Td>{hook.url}</Table.Td>
      <Table.Td>
        <ActionIcon color="red" onClick={() => handleRemoveWebhook(hook.id)} loading={isSubmitting}>
          <IconTrash size={16} />
        </ActionIcon>
      </Table.Td>
    </Table.Tr>
  ));

  const renderWebhookModal = (provider: 'generic' | 'google_chat') => {
      const modalProps = {
          opened: provider === 'generic' ? webhookModalOpened : gchatModalOpened,
          onClose: provider === 'generic' ? closeWebhookModal : closeGchatModal,
          title: t(provider === 'generic' ? 'settings.notifications.webhook.addModalTitle' : 'settings.notifications.gchat.addModalTitle', 'Add New Webhook'),
      };
      return (
          <Modal {...modalProps}>
              <TextInput
                  label={t('settings.notifications.webhook.form.nameLabel', 'Name')}
                  placeholder={t('settings.notifications.webhook.form.namePlaceholder', 'e.g., Slack Alerts')}
                  value={newWebhook.name}
                  onChange={(e) => setNewWebhook(prev => ({...prev, name: e.currentTarget.value, provider}))}
                  required
              />
              <TextInput
                  mt="md"
                  label={t('settings.notifications.webhook.form.urlLabel', 'URL')}
                  placeholder="https://..."
                  value={newWebhook.url}
                  onChange={(e) => setNewWebhook(prev => ({...prev, url: e.currentTarget.value, provider}))}
                  required
              />
              <Button fullWidth mt="xl" onClick={handleAddWebhook} loading={isSubmitting}>
                  {t('settings.notifications.webhook.form.addButton', 'Add Webhook')}
              </Button>
          </Modal>
      )
  };

  return (
    <Paper withBorder p="xl" radius="md">
      <Title order={2} mb="lg">{t('settings.notifications.title', 'Notification Settings')}</Title>

      <ErrorMessage message={error} onClose={() => setError(null)} />

      {loading ? (
          <Skeleton height={300} />
      ) : (
      <>
      {/* Seção de E-mail */}
      <section>
        <Title order={4} mb="md">{t('settings.notifications.email.title', 'Email Recipients')}</Title>
        <Text size="sm" c="dimmed" mb="md">
          {t('settings.notifications.email.description', 'Add email addresses to receive critical alert notifications.')}
        </Text>
        <Table>
          <Table.Tbody>
            {emails.map(email => (
              <Table.Tr key={email.id}>
                <Table.Td>{email.address}</Table.Td>
                <Table.Td align="right">
                  <ActionIcon color="red" onClick={() => handleRemoveEmail(email.id)} loading={isSubmitting}>
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
            disabled={isSubmitting}
          />
          <Button onClick={handleAddEmail} leftSection={<IconPlus size={16} />} loading={isSubmitting}>
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
            <Table.Tbody>{renderWebhookRows(webhooks)}</Table.Tbody>
        </Table>
         <Button mt="md" variant="light" leftSection={<IconPlus size={16} />} onClick={openWebhookModal}>
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
             <Table>
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th>{t('settings.notifications.webhook.tableNameHeader', 'Name')}</Table.Th>
                        <Table.Th>{t('settings.notifications.webhook.tableUrlHeader', 'URL')}</Table.Th>
                        <Table.Th />
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>{renderWebhookRows(googleChatWebhooks)}</Table.Tbody>
            </Table>
        ) : (
            <Text size="sm" c="dimmed">{t('settings.notifications.gchat.noWebhooks', 'No Google Chat webhooks configured.')}</Text>
        )}
         <Button mt="md" variant="light" leftSection={<IconPlus size={16} />} onClick={openGchatModal}>
            {t('settings.notifications.gchat.addButton', 'Add Google Chat Webhook')}
        </Button>
      </section>
      </>
      )}
      {renderWebhookModal('generic')}
      {renderWebhookModal('google_chat')}
    </Paper>
  );
};

export default NotificationSettingsPage;
