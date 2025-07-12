import React from 'react';
import { useTranslation } from 'react-i18next';
import { Title, Text, Button, Container, Group } from '@mantine/core';
import { IconLock } from '@tabler/icons-react';
import { Link } from 'react-router-dom';

const AccessDeniedPage: React.FC = () => {
  const { t } = useTranslation();

  return (
    <Container style={{ textAlign: 'center', paddingTop: '5rem' }}>
      <IconLock size={80} style={{ margin: 'auto', color: 'var(--mantine-color-red-6)' }} />
      <Title order={1} mt="xl">
        {t('accessDenied.title', 'Access Denied')}
      </Title>
      <Text c="dimmed" size="lg" mt="md">
        {t('accessDenied.message', 'You do not have permission to view this page.')}
      </Text>
      <Group justify="center" mt="xl">
        <Button component={Link} to="/dashboard" variant="outline">
          {t('accessDenied.button', 'Take me to the dashboard')}
        </Button>
      </Group>
    </Container>
  );
};

export default AccessDeniedPage;
