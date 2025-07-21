import { calculateSeverityData, calculateProviderData } from './reportUtils';
import { Alert as AlertType } from '../components/Dashboard/AlertsTable';

// Mock de dados de alertas
const mockAlerts: AlertType[] = [
  { id: 1, severity: 'Critical', provider: 'aws', created_at: new Date().toISOString(), title: 't', description: 'd', policy_id: 'p1', resource_id: 'r1', resource_type: 'rt1', status: 'OPEN', updated_at: '' , first_seen_at: '', last_seen_at: '' },
  { id: 2, severity: 'High', provider: 'aws', created_at: new Date().toISOString(), title: 't', description: 'd', policy_id: 'p2', resource_id: 'r2', resource_type: 'rt2', status: 'OPEN', updated_at: '' , first_seen_at: '', last_seen_at: '' },
  { id: 3, severity: 'Critical', provider: 'gcp', created_at: new Date().toISOString(), title: 't', description: 'd', policy_id: 'p3', resource_id: 'r3', resource_type: 'rt3', status: 'OPEN', updated_at: '' , first_seen_at: '', last_seen_at: '' },
  { id: 4, severity: 'Medium', provider: 'azure', created_at: new Date().toISOString(), title: 't', description: 'd', policy_id: 'p4', resource_id: 'r4', resource_type: 'rt4', status: 'OPEN', updated_at: '' , first_seen_at: '', last_seen_at: '' },
  { id: 5, severity: 'High', provider: 'aws', created_at: new Date().toISOString(), title: 't', description: 'd', policy_id: 'p2', resource_id: 'r2', resource_type: 'rt2', status: 'OPEN', updated_at: '' , first_seen_at: '', last_seen_at: '' },
];

describe('reportUtils', () => {
  describe('calculateSeverityData', () => {
    it('should correctly calculate alert counts by severity', () => {
      const result = calculateSeverityData(mockAlerts);

      const critical = result.find(item => item.name === 'Critical');
      const high = result.find(item => item.name === 'High');
      const medium = result.find(item => item.name === 'Medium');

      expect(critical?.value).toBe(2);
      expect(high?.value).toBe(2);
      expect(medium?.value).toBe(1);
    });

    it('should assign correct colors to severities', () => {
      const result = calculateSeverityData(mockAlerts);

      const critical = result.find(item => item.name === 'Critical');
      const high = result.find(item => item.name === 'High');
      const medium = result.find(item => item.name === 'Medium');

      expect(critical?.color).toBe('var(--mantine-color-red-6)');
      expect(high?.color).toBe('var(--mantine-color-orange-6)');
      expect(medium?.color).toBe('var(--mantine-color-yellow-5)');
    });

    it('should return an empty array if no alerts are provided', () => {
      const result = calculateSeverityData([]);
      expect(result).toEqual([]);
    });
  });

  describe('calculateProviderData', () => {
    it('should correctly calculate alert counts by provider', () => {
      const result = calculateProviderData(mockAlerts);

      const aws = result.find(item => item.name === 'AWS');
      const gcp = result.find(item => item.name === 'GCP');
      const azure = result.find(item => item.name === 'AZURE');

      expect(aws?.value).toBe(3);
      expect(gcp?.value).toBe(1);
      expect(azure?.value).toBe(1);
    });

    it('should return an empty array if no alerts are provided', () => {
      const result = calculateProviderData([]);
      expect(result).toEqual([]);
    });
  });
});
