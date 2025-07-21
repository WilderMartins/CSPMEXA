import { calculateTopViolatedPolicies, calculateTopVulnerableResources } from './insightUtils';
import { Alert as AlertType } from '../components/Dashboard/AlertsTable';

const mockAlerts: AlertType[] = [
  // Policy counts: p1=3, p2=2, p3=1
  { id: 1, policy_id: 'p1', resource_id: 'r1', resource_type: 'S3', severity: 'High', provider: 'aws', created_at: '', title: '', description: '', status: 'OPEN', updated_at: '', first_seen_at: '', last_seen_at: '' },
  { id: 2, policy_id: 'p2', resource_id: 'r2', resource_type: 'EC2', severity: 'High', provider: 'aws', created_at: '', title: '', description: '', status: 'OPEN', updated_at: '', first_seen_at: '', last_seen_at: '' },
  { id: 3, policy_id: 'p1', resource_id: 'r3', resource_type: 'VM', severity: 'High', provider: 'gcp', created_at: '', title: '', description: '', status: 'OPEN', updated_at: '', first_seen_at: '', last_seen_at: '' },
  { id: 4, policy_id: 'p2', resource_id: 'r1', resource_type: 'S3', severity: 'High', provider: 'aws', created_at: '', title: '', description: '', status: 'OPEN', updated_at: '', first_seen_at: '', last_seen_at: '' },
  { id: 5, policy_id: 'p1', resource_id: 'r1', resource_type: 'S3', severity: 'High', provider: 'aws', created_at: '', title: '', description: '', status: 'OPEN', updated_at: '', first_seen_at: '', last_seen_at: '' },
  { id: 6, policy_id: 'p3', resource_id: 'r4', resource_type: 'RDS', severity: 'High', provider: 'aws', created_at: '', title: '', description: '', status: 'OPEN', updated_at: '', first_seen_at: '', last_seen_at: '' },
  // Resource counts: S3:r1=3, EC2:r2=1, VM:r3=1, RDS:r4=1
];

describe('insightUtils', () => {
  describe('calculateTopViolatedPolicies', () => {
    it('should return the top N most violated policies in descending order', () => {
      const result = calculateTopViolatedPolicies(mockAlerts, 3);

      expect(result).toHaveLength(3);
      expect(result[0]).toEqual({ name: 'p1', count: 3 });
      expect(result[1]).toEqual({ name: 'p2', count: 2 });
      expect(result[2]).toEqual({ name: 'p3', count: 1 });
    });

    it('should return fewer than N if there are not enough unique policies', () => {
      const result = calculateTopViolatedPolicies(mockAlerts, 5);
      expect(result).toHaveLength(3);
    });

    it('should return an empty array if no alerts are provided', () => {
      const result = calculateTopViolatedPolicies([]);
      expect(result).toEqual([]);
    });
  });

  describe('calculateTopVulnerableResources', () => {
    it('should return the top N most vulnerable resources in descending order', () => {
      const result = calculateTopVulnerableResources(mockAlerts, 2);

      expect(result).toHaveLength(2);
      expect(result[0]).toEqual({ name: 'S3: r1', count: 3 });
      expect(result[1]).toEqual({ name: 'EC2: r2', count: 1 }); // Could be r2, r3, or r4 as they all have count 1
    });

    it('should correctly group resources by type and id', () => {
        const result = calculateTopVulnerableResources(mockAlerts, 1);
        expect(result[0].name).toBe('S3: r1');
        expect(result[0].count).toBe(3);
    });

    it('should return an empty array if no alerts are provided', () => {
      const result = calculateTopVulnerableResources([]);
      expect(result).toEqual([]);
    });
  });
});
