import { Alert as AlertType } from '../components/Dashboard/AlertsTable';

export interface ChartDataItem {
  name: string;
  value: number;
  color?: string;
}

/**
 * Calcula a contagem de alertas por severidade.
 * @param alerts - A lista de alertas para processar.
 * @returns Um array de dados para o gráfico de severidade.
 */
export function calculateSeverityData(alerts: AlertType[]): ChartDataItem[] {
  const counts: Record<string, number> = {};
  alerts.forEach(alert => {
    counts[alert.severity] = (counts[alert.severity] || 0) + 1;
  });

  return Object.entries(counts).map(([name, value]) => {
    let color;
    switch (name.toLowerCase()) {
      case 'critical': color = 'var(--mantine-color-red-6)'; break;
      case 'high': color = 'var(--mantine-color-orange-6)'; break;
      case 'medium': color = 'var(--mantine-color-yellow-5)'; break;
      case 'low': color = 'var(--mantine-color-blue-5)'; break;
      case 'informational': color = 'var(--mantine-color-gray-5)'; break;
      default: color = 'var(--mantine-color-teal-5)';
    }
    return { name, value, color };
  });
}

/**
 * Calcula a contagem de alertas por provedor.
 * @param alerts - A lista de alertas para processar.
 * @returns Um array de dados para o gráfico de provedor.
 */
export function calculateProviderData(alerts: AlertType[]): ChartDataItem[] {
  const counts: Record<string, number> = {};
  alerts.forEach(alert => {
    counts[alert.provider.toUpperCase()] = (counts[alert.provider.toUpperCase()] || 0) + 1;
  });

  return Object.entries(counts).map(([name, value]) => {
    let color;
    switch (name.toLowerCase()) {
      case 'aws': color = 'var(--mantine-color-orange-7)'; break;
      case 'gcp': color = 'var(--mantine-color-blue-7)'; break;
      case 'azure': color = 'var(--mantine-color-indigo-7)'; break;
      case 'huawei': color = 'var(--mantine-color-red-7)'; break;
      case 'googleworkspace': color = 'var(--mantine-color-green-7)'; break;
      default: color = 'var(--mantine-color-cyan-7)';
    }
    return { name, value, color };
  });
}
