import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Container, Title, Card, Text, SimpleGrid, Badge } from '@mantine/core';
import { api } from '../services/api';

interface AttackPath {
    id: number;
    path_id: string;
    description: string;
    severity: string;
    nodes: any[]; // Simplificado por enquanto
}

const AttackPathsPage: React.FC = () => {
    const { t } = useTranslation();
    const [attackPaths, setAttackPaths] = useState<AttackPath[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.get<AttackPath[]>('/attack-paths')
            .then(response => {
                setAttackPaths(response.data);
                setLoading(false);
            })
            .catch(error => {
                console.error("Erro ao buscar caminhos de ataque:", error);
                setLoading(false);
            });
    }, []);

    const getSeverityColor = (severity: string) => {
        switch (severity.toUpperCase()) {
            case 'CRITICAL': return 'red';
            case 'HIGH': return 'orange';
            case 'MEDIUM': return 'yellow';
            default: return 'gray';
        }
    };

    return (
        <Container fluid>
            <Title order={2} mb="lg">Análise de Caminhos de Ataque</Title>

            {loading ? (
                <Text>Carregando...</Text>
            ) : (
                <SimpleGrid cols={{ base: 1, md: 2, lg: 3 }}>
                    {attackPaths.map(path => (
                        <Card shadow="sm" p="lg" radius="md" withBorder key={path.id}>
                            <Badge color={getSeverityColor(path.severity)} variant="light">
                                {path.severity}
                            </Badge>
                            <Title order={4} mt="md">{path.path_id}</Title>
                            <Text size="sm" c="dimmed" mt="xs">{path.description}</Text>
                        </Card>
                    ))}
                </SimpleGrid>
            )}
        </Container>
    );
};

export default AttackPathsPage;
