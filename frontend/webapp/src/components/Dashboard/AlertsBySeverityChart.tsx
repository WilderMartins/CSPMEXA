import React from 'react';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Card, Text, Center } from '@mantine/core';

interface AlertsBySeverityChartProps {
  data: { [key: string]: number };
}

const COLORS = {
  CRITICAL: '#fa5252',
  HIGH: '#fd7e14',
  MEDIUM: '#fcc419',
  LOW: '#40c057',
  INFORMATIONAL: '#4dabf7',
};

const AlertsBySeverityChart: React.FC<AlertsBySeverityChartProps> = ({ data }) => {
  const chartData = Object.entries(data).map(([name, value]) => ({ name, value }));

  if (chartData.length === 0) {
    return (
      <Card withBorder shadow="sm" p="lg" radius="md" style={{ height: '100%' }}>
        <Center style={{ height: '100%' }}>
          <Text c="dimmed">Nenhum dado de severidade para exibir.</Text>
        </Center>
      </Card>
    );
  }

  return (
    <Card withBorder shadow="sm" p="lg" radius="md">
      <Text fw={500} mb="md">Alertas por Severidade</Text>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[entry.name] || '#8884d8'} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </Card>
  );
};

export default AlertsBySeverityChart;
