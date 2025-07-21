// import React from 'react';
// import { render, screen, fireEvent } from '@testing-library/react';
// import ProviderAnalysisSection from './ProviderAnalysisSection';

// const mockProviderConfig = {
//   providerId: 'aws',
//   providerNameKey: 'AWS',
//   analysisButtons: [
//     { id: 's3', labelKey: 'S3', servicePath: 's3', analysisType: 'AWS S3' },
//     { id: 'ec2', labelKey: 'EC2', servicePath: 'ec2', analysisType: 'AWS EC2' },
//   ],
// };

// describe('ProviderAnalysisSection', () => {
//   it('renders the section with the provider name', () => {
//     render(<ProviderAnalysisSection {...mockProviderConfig} onAnalyze={() => {}} isLoading={false} currentAnalysisType={null} />);
//     expect(screen.getByText(/AWS/i)).toBeInTheDocument();
//   });

//   it('calls onAnalyze when a button is clicked', () => {
//     const onAnalyze = jest.fn();
//     render(<ProviderAnalysisSection {...mockProviderConfig} onAnalyze={onAnalyze} isLoading={false} currentAnalysisType={null} />);
//     fireEvent.click(screen.getByText(/S3/i));
//     expect(onAnalyze).toHaveBeenCalledWith('aws', 's3', 'AWS S3');
//   });
// });
it.todo('should be tested');
