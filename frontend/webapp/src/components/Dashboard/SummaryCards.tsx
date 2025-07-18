import React, { useEffect, useState } from 'react';
import { Card, Text, Group, SimpleGrid, ThemeIcon } from '@mantine/core';
import { IconAlertTriangle, IconCircleCheck, IconCircleX } from '@tabler/icons-react';
import { api } from '../../services/api';

interface SummaryData {
  total_alerts: number;
  by_severity: { [key: string]: number };
  by_status: { [key: string]: number };
}

const SummaryCards: React.FC = () => {
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<SummaryData>('/dashboard/summary')
      .then(response => {
        setSummary(response.data);
        setLoading(false);
      })
      .catch(error => {
        console.error('Error fetching summary data:', error);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <Text>Loading summary...</Text>;
  }

  if (!summary) {
    return <Text>Could not load summary data.</Text>;
  }

  const criticalAlerts = summary.by_severity['CRITICAL'] || 0;
  const openAlerts = summary.by_status['OPEN'] || 0;
  const resolvedAlerts = summary.by_status['RESOLVED'] || 0;

  return (
    <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
      <Card withBorder shadow="sm" p="lg" radius="md">
        <Group >
          <ThemeIcon color="red" size={48} radius="xl">
            <IconAlertTriangle size={24} />
          </ThemeIcon>
          <div>
            <Text size="xl" fw={700}>{criticalAlerts}</Text>
            <Text size="sm" c="dimmed">Alertas Críticos</Text>
          </div>
        </Group>
      </Card>
      <Card withBorder shadow="sm" p="lg" radius="md">
        <Group >
          <ThemeIcon color="orange" size={48} radius="xl">
            <IconCircleX size={24} />
          </ThemeIcon>
          <div>
            <Text size="xl" fw={700}>{openAlerts}</Text>
            <Text size="sm" c="dimmed">Alertas Abertos</Text>
          </div>
        </Group>
      </Card>
      <Card withBorder shadow="sm" p="lg" radius="md">
        <Group >
          <ThemeIcon color="green" size={48} radius="xl">
            <IconCircleCheck size={24} />
          </ThemeIcon>
          <div>
            <Text size="xl" fw={700}>{resolvedAlerts}</Text>
            <Text size="sm" c="dimmed">Alertas Resolvidos</Text>
          </div>
        </Group>
      </Card>
    </SimpleGrid>
  );
};

export default SummaryCards;
