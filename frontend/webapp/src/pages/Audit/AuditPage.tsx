import React, { useEffect, useState } from 'react';
import { api } from '../../services/api';

const AuditPage: React.FC = () => {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const response = await api.get('/audit/events');
        setEvents(response.data);
      } catch (err) {
        setError('Failed to fetch audit events.');
      } finally {
        setLoading(false);
      }
    };

    fetchEvents();
  }, []);

  if (loading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div style={{ color: 'red' }}>{error}</div>;
  }

  return (
    <div>
      <h1>Audit Trail</h1>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ border: '1px solid #ddd', padding: '8px' }}>Timestamp</th>
            <th style={{ border: '1px solid #ddd', padding: '8px' }}>Actor</th>
            <th style={{ border: '1px solid #ddd', padding: '8px' }}>Action</th>
            <th style={{ border: '1px solid #ddd', padding: '8px' }}>Resource</th>
            <th style={{ border: '1px solid #ddd', padding: '8px' }}>Details</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => (
            <tr key={event.id}>
              <td style={{ border: '1px solid #ddd', padding: '8px' }}>{new Date(event.timestamp).toLocaleString()}</td>
              <td style={{ border: '1px solid #ddd', padding: '8px' }}>{event.actor}</td>
              <td style={{ border: '1px solid #ddd', padding: '8px' }}>{event.action}</td>
              <td style={{ border: '1px solid #ddd', padding: '8px' }}>{event.resource}</td>
              <td style={{ border: '1px solid #ddd', padding: '8px' }}>{JSON.stringify(event.details)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default AuditPage;
