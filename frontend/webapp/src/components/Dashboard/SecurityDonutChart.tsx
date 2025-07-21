import React from 'react';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from 'recharts';
import { useMantineTheme } from '@mantine/core';

interface ChartData {
  name: string;
  value: number;
}

interface SecurityDonutChartProps {
  data: ChartData[];
}

const SecurityDonutChart: React.FC<SecurityDonutChartProps> = ({ data }) => {
    const theme = useMantineTheme();

    // Usando as cores do tema Mantine para consistência
    const COLORS = [
      theme.colors.blue[6],
      theme.colors.red[6],
      theme.colors.green[6],
      theme.colors.orange[6],
      theme.colors.grape[6],
      theme.colors.teal[6],
    ];

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={80}
          fill="#8884d8"
          paddingAngle={5}
          dataKey="value"
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
};

export default SecurityDonutChart;
