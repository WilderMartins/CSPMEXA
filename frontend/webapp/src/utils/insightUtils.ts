import { Alert as AlertType } from '../components/Dashboard/AlertsTable';

export interface InsightDataItem {
  name: string;
  count: number;
}

/**
 * Calcula as top N políticas mais violadas.
 * @param alerts - A lista de alertas (geralmente alertas abertos).
 * @param topN - O número de principais políticas a serem retornadas.
 * @returns Um array dos top N políticas e suas contagens.
 */
export function calculateTopViolatedPolicies(alerts: AlertType[], topN: number = 5): InsightDataItem[] {
  if (!alerts.length) return [];
  const policyCounts: Record<string, number> = {};
  alerts.forEach(alert => {
    policyCounts[alert.policy_id] = (policyCounts[alert.policy_id] || 0) + 1;
  });
  return Object.entries(policyCounts)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, topN);
}

/**
 * Calcula os top N recursos mais vulneráveis.
 * @param alerts - A lista de alertas (geralmente alertas abertos).
 * @param topN - O número de principais recursos a serem retornados.
 * @returns Um array dos top N recursos e suas contagens.
 */
export function calculateTopVulnerableResources(alerts: AlertType[], topN: number = 5): InsightDataItem[] {
  if (!alerts.length) return [];
  const resourceCounts: Record<string, number> = {};
  alerts.forEach(alert => {
    const resourceKey = `${alert.resource_type}: ${alert.resource_id}`;
    resourceCounts[resourceKey] = (resourceCounts[resourceKey] || 0) + 1;
  });
  return Object.entries(resourceCounts)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, topN);
}
