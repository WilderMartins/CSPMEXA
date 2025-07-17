import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Table, Button, Modal, TextInput, Select, Group, Title, Stack, JsonInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { api } from '../../services/api';
import { showNotification } from '@mantine/notifications';

interface LinkedAccount {
    id: number;
    name: string;
    provider: string;
    account_id: string;
}

const LinkedAccountsPage: React.FC = () => {
    const { t } = useTranslation();
    const [accounts, setAccounts] = useState<LinkedAccount[]>([]);
    const [isModalOpen, setIsModalOpen] = useState(false);

    const form = useForm({
        initialValues: {
            name: '',
            provider: 'aws',
            account_id: '',
            credentials: '{}',
        },
        validate: {
            name: (value) => (value.length > 2 ? null : 'O nome deve ter pelo menos 3 caracteres'),
            account_id: (value) => (value ? null : 'O ID da conta é obrigatório'),
            credentials: (value) => {
                try {
                    JSON.parse(value);
                    return null;
                } catch {
                    return 'As credenciais devem ser um JSON válido.';
                }
            },
        },
    });

    const fetchAccounts = async () => {
        try {
            const response = await api.get<LinkedAccount[]>('/accounts');
            setAccounts(response.data);
        } catch (error) {
            console.error("Erro ao buscar contas vinculadas:", error);
            showNotification({
                title: 'Erro',
                message: 'Não foi possível carregar as contas vinculadas.',
                color: 'red',
            });
        }
    };

    useEffect(() => {
        fetchAccounts();
    }, []);

    const handleAddAccount = async (values: typeof form.values) => {
        try {
            await api.post('/accounts', {
                ...values,
                credentials: JSON.parse(values.credentials),
            });
            showNotification({
                title: 'Sucesso!',
                message: 'Conta vinculada adicionada com sucesso.',
                color: 'green',
            });
            fetchAccounts();
            setIsModalOpen(false);
            form.reset();
        } catch (error) {
            console.error("Erro ao adicionar conta:", error);
            showNotification({
                title: 'Erro',
                message: 'Não foi possível adicionar a conta.',
                color: 'red',
            });
        }
    };

    const handleDeleteAccount = async (accountId: number) => {
        try {
            await api.delete(`/accounts/${accountId}`);
            showNotification({
                title: 'Sucesso!',
                message: 'Conta vinculada removida com sucesso.',
                color: 'teal',
            });
            fetchAccounts();
        } catch (error) {
            console.error("Erro ao remover conta:", error);
            showNotification({
                title: 'Erro',
                message: 'Não foi possível remover a conta.',
                color: 'red',
            });
        }
    };

    const rows = accounts.map((account) => (
        <Table.Tr key={account.id}>
            <Table.Td>{account.name}</Table.Td>
            <Table.Td>{account.provider.toUpperCase()}</Table.Td>
            <Table.Td>{account.account_id}</Table.Td>
            <Table.Td>
                <Button color="red" size="xs" onClick={() => handleDeleteAccount(account.id)}>
                    Excluir
                </Button>
            </Table.Td>
        </Table.Tr>
    ));

    return (
        <div>
            <Group justify="space-between" mb="lg">
                <Title order={3}>Contas Vinculadas</Title>
                <Button onClick={() => setIsModalOpen(true)}>Adicionar Conta</Button>
            </Group>

            <Table striped highlightOnHover withTableBorder>
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th>Nome</Table.Th>
                        <Table.Th>Provedor</Table.Th>
                        <Table.Th>ID da Conta/Projeto</Table.Th>
                        <Table.Th>Ações</Table.Th>
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>{rows}</Table.Tbody>
            </Table>

            <Modal opened={isModalOpen} onClose={() => setIsModalOpen(false)} title="Adicionar Nova Conta Vinculada" size="lg">
                <form onSubmit={form.onSubmit(handleAddAccount)}>
                    <Stack>
                        <TextInput required label="Nome" placeholder="Ex: Conta de Produção AWS" {...form.getInputProps('name')} />
                        <Select
                            required
                            label="Provedor"
                            data={['aws', 'gcp', 'azure']}
                            {...form.getInputProps('provider')}
                        />
                        <TextInput required label="ID da Conta/Projeto" placeholder="Ex: 123456789012" {...form.getInputProps('account_id')} />
                        <JsonInput
                            required
                            label="Credenciais"
                            placeholder='{ "aws_access_key_id": "...", "aws_secret_access_key": "..." }'
                            validationError="JSON inválido"
                            formatOnBlur
                            autosize
                            minRows={4}
                            {...form.getInputProps('credentials')}
                        />
                        <Group justify="flex-end" mt="md">
                            <Button type="submit">Adicionar</Button>
                        </Group>
                    </Stack>
                </form>
            </Modal>
        </div>
    );
};

export default LinkedAccountsPage;
