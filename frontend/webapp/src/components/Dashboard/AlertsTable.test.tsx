// import React from 'react';
// import { render, screen } from '@testing-library/react';
// import AlertsTable from './AlertsTable';

// const mockAlerts = [
//   { id: '1', policy_id: 'S3_BUCKET_PUBLIC_ACL', resource_id: 'my-bucket', region: 'us-east-1', status: 'OPEN', severity: 'CRITICAL', created_at: new Date().toISOString() },
//   { id: '2', policy_id: 'IAM_USER_NO_MFA', resource_id: 'my-user', region: 'us-east-1', status: 'OPEN', severity: 'HIGH', created_at: new Date().toISOString() },
// ];

// describe('AlertsTable', () => {
//   it('renders the table with the provided alerts', () => {
//     render(<AlertsTable alerts={mockAlerts} title="Test Alerts" onUpdateStatus={() => {}} canUpdateStatus={true} onRemediate={() => {}} />);
//     expect(screen.getByText(/Test Alerts/i)).toBeInTheDocument();
//     expect(screen.getByText(/my-bucket/i)).toBeInTheDocument();
//     expect(screen.getByText(/my-user/i)).toBeInTheDocument();
//   });
// });
it.todo('should be tested');
