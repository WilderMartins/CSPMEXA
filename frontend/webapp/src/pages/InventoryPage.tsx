import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Table, Title, Container, Pagination, Group, Text } from '@mantine/core';
import apiClient from '../services/api';

interface Asset {
    id: number;
    name: string;
    asset_id: string;
    asset_type: string;
    provider: string;
    account_id: string;
    region: string;
}

const ITEMS_PER_PAGE = 15;

const InventoryPage: React.FC = () => {
    const { t } = useTranslation();
    const [assets, setAssets] = useState<Asset[]>([]);
    const [loading, setLoading] = useState(true);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalAssets, setTotalAssets] = useState(0);

    const fetchAssets = async (page: number) => {
        setLoading(true);
        try {
            const response = await apiClient.get<Asset[]>('/assets', {
                params: {
                    skip: (page - 1) * ITEMS_PER_PAGE,
                    limit: ITEMS_PER_PAGE,
                },
            });
            setAssets(response.data);
            // A API precisaria retornar o total de ativos para a paginação funcionar corretamente.
            // Por enquanto, vamos assumir que o total é o que veio na primeira página.
            // Em uma implementação real, o header X-Total-Count ou um objeto de resposta seria melhor.
            // setTotalAssets(Number(response.headers['x-total-count']));
        } catch (error) {
            console.error("Erro ao buscar ativos:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAssets(currentPage);
    }, [currentPage]);

    const rows = assets.map((asset) => (
        <Table.Tr key={asset.id}>
            <Table.Td>{asset.name || '-'}</Table.Td>
            <Table.Td>{asset.asset_type}</Table.Td>
            <Table.Td>{asset.provider.toUpperCase()}</Table.Td>
            <Table.Td>{asset.account_id}</Table.Td>
            <Table.Td>{asset.region || 'global'}</Table.Td>
            <Table.Td>{asset.asset_id}</Table.Td>
        </Table.Tr>
    ));

    return (
        <Container fluid>
            <Title order={2} mb="lg">Inventário de Ativos na Nuvem</Title>

            {loading ? (
                <Text>Carregando ativos...</Text>
            ) : (
                <>
                    <Table striped highlightOnHover withTableBorder>
                        <Table.Thead>
                            <Table.Tr>
                                <Table.Th>Nome</Table.Th>
                                <Table.Th>Tipo</Table.Th>
                                <Table.Th>Provedor</Table.Th>
                                <Table.Th>ID da Conta</Table.Th>
                                <Table.Th>Região</Table.Th>
                                <Table.Th>ID do Ativo</Table.Th>
                            </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>{rows}</Table.Tbody>
                    </Table>
                    <Group justify="flex-end" mt="md">
                        <Pagination
                            total={Math.ceil(totalAssets / ITEMS_PER_PAGE)}
                            value={currentPage}
                            onChange={setCurrentPage}
                        />
                    </Group>
                </>
            )}
        </Container>
    );
};

export default InventoryPage;
