import React from 'react';
import { useTranslation } from 'react-i18next';
import { Select, Group } from '@mantine/core';

interface AlertsTableFiltersProps {
    filterSeverity: string;
    setFilterSeverity: (value: string) => void;
    uniqueSeverities: string[];
    filterProvider: string;
    setFilterProvider: (value: string) => void;
    uniqueProviders: string[];
    filterStatus: string | null;
    setFilterStatus: (value: string | null) => void;
    uniqueStatuses: string[];
}

const AlertsTableFilters: React.FC<AlertsTableFiltersProps> = ({
    filterSeverity, setFilterSeverity, uniqueSeverities,
    filterProvider, setFilterProvider, uniqueProviders,
    filterStatus, setFilterStatus, uniqueStatuses
}) => {
    const { t } = useTranslation();

    return (
        <Group mb="md">
            <Select
                label={t('alertFilters.severity')}
                placeholder={t('alertFilters.allSeverities')}
                value={filterSeverity}
                onChange={(value) => setFilterSeverity(value || '')}
                data={[{ value: '', label: t('alertFilters.allSeverities') }, ...uniqueSeverities.map(s => ({ value: s, label: s }))]}
                clearable
            />
            <Select
                label={t('alertFilters.provider')}
                placeholder={t('alertFilters.allProviders')}
                value={filterProvider}
                onChange={(value) => setFilterProvider(value || '')}
                data={[{ value: '', label: t('alertFilters.allProviders') }, ...uniqueProviders.map(p => ({ value: p, label: p.toUpperCase() }))]}
                clearable
            />
            <Select
                label={t('alertFilters.status')}
                placeholder={t('alertFilters.allStatuses')}
                value={filterStatus}
                onChange={setFilterStatus}
                data={[{ value: '', label: t('alertFilters.allStatuses') }, ...uniqueStatuses.map(s => ({ value: s, label: s }))]}
                clearable
            />
        </Group>
    );
};

export default AlertsTableFilters;
