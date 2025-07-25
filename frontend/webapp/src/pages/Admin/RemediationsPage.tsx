import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Table, Button, Group, Title, Container, Text, Badge } from '@mantine/core';
import apiClient from '../../services/api';
import { showNotification } from '@mantine/notifications';

interface RemediationRequest {
    id: number;
    alert_id: number;
    status: string;
    requested_at: string;
    alert: {
        title: string;
        severity: string;
    };
}

const RemediationsPage: React.FC = () => {
    const { t } = useTranslation();
    const [requests, setRequests] = useState<RemediationRequest[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchRequests = async () => {
        setLoading(true);
        try {
            // A API precisaria de um endpoint para buscar solicitações pendentes
            const response = await apiClient.get<RemediationRequest[]>('/remediations?status=PENDING');
            setRequests(response.data);
        } catch (error) {
            console.error("Erro ao buscar solicitações de remediação:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRequests();
    }, []);

    const handleApprove = async (id: number) => {
        try {
            await apiClient.post(`/remediations/${id}/approve`);
            showNotification({ title: 'Sucesso', message: 'Remediação aprovada e agendada.', color: 'green' });
            fetchRequests();
        } catch (error) {
            showNotification({ title: 'Erro', message: 'Não foi possível aprovar a remediação.', color: 'red' });
        }
    };

    const rows = requests.map((req) => (
        <Table.Tr key={req.id}>
            <Table.Td>{req.alert.title}</Table.Td>
            <Table.Td><Badge color="red">{req.alert.severity}</Badge></Table.Td>
            <Table.Td>{new Date(req.requested_at).toLocaleString()}</Table.Td>
            <Table.Td>
                <Group>
                    <Button size="xs" color="green" onClick={() => handleApprove(req.id)}>Aprovar</Button>
                    <Button size="xs" color="red">Rejeitar</Button>
                </Group>
            </Table.Td>
        </Table.Tr>
    ));

    return (
        <Container fluid>
            <Title order={2} mb="lg">Solicitações de Remediação Pendentes</Title>
            {loading ? <Text>Carregando...</Text> : (
                <Table>
                    <Table.Thead>
                        <Table.Tr>
                            <Table.Th>Alerta</Table.Th>
                            <Table.Th>Severidade</Table.Th>
                            <Table.Th>Solicitado em</Table.Th>
                            <Table.Th>Ações</Table.Th>
                        </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>{rows}</Table.Tbody>
                </Table>
            )}
        </Container>
    );
};

export default RemediationsPage;
