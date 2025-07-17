import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Table, Button, Modal, Select, Group, Title, Stack, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { api } from '../../services/api';
import { showNotification } from '@mantine/notifications';

interface Channel {
    id: number;
    name: string;
}

interface Rule {
    id: number;
    name: string;
    provider: string;
    severity: string;
    channel: Channel;
}

const ManageRules: React.FC = () => {
    const { t } = useTranslation();
    const [rules, setRules] = useState<Rule[]>([]);
    const [channels, setChannels] = useState<Channel[]>([]);
    const [isModalOpen, setIsModalOpen] = useState(false);

    const form = useForm({
        initialValues: {
            name: '',
            provider: '',
            severity: '',
            channel_id: '',
        },
        validate: {
            name: (value) => (value.length > 2 ? null : 'O nome deve ter pelo menos 3 caracteres'),
            provider: (value) => (value ? null : 'Selecione um provedor'),
            severity: (value) => (value ? null : 'Selecione uma severidade'),
            channel_id: (value) => (value ? null : 'Selecione um canal'),
        },
    });

    const fetchRulesAndChannels = async () => {
        try {
            const [rulesResponse, channelsResponse] = await Promise.all([
                api.get<Rule[]>('/management/rules'),
                api.get<Channel[]>('/management/channels'),
            ]);
            setRules(rulesResponse.data);
            setChannels(channelsResponse.data);
        } catch (error) {
            console.error("Erro ao buscar regras e canais:", error);
            showNotification({
                title: 'Erro',
                message: 'Não foi possível carregar os dados de notificações.',
                color: 'red',
            });
        }
    };

    useEffect(() => {
        fetchRulesAndChannels();
    }, []);

    const handleAddRule = async (values: typeof form.values) => {
        try {
            await api.post('/management/rules', {
                ...values,
                channel_id: parseInt(values.channel_id, 10),
            });
            showNotification({
                title: 'Sucesso!',
                message: 'Regra de notificação adicionada com sucesso.',
                color: 'green',
            });
            fetchRulesAndChannels();
            setIsModalOpen(false);
            form.reset();
        } catch (error) {
            console.error("Erro ao adicionar regra:", error);
            showNotification({
                title: 'Erro',
                message: 'Não foi possível adicionar a regra.',
                color: 'red',
            });
        }
    };

    const handleDeleteRule = async (ruleId: number) => {
        try {
            await api.delete(`/management/rules/${ruleId}`);
            showNotification({
                title: 'Sucesso!',
                message: 'Regra de notificação removida com sucesso.',
                color: 'teal',
            });
            fetchRulesAndChannels();
        } catch (error) {
            console.error("Erro ao remover regra:", error);
            showNotification({
                title: 'Erro',
                message: 'Não foi possível remover a regra.',
                color: 'red',
            });
        }
    };

    const rows = rules.map((rule) => (
        <Table.Tr key={rule.id}>
            <Table.Td>{rule.name}</Table.Td>
            <Table.Td>{rule.provider.toUpperCase()}</Table.Td>
            <Table.Td>{rule.severity}</Table.Td>
            <Table.Td>{rule.channel.name}</Table.Td>
            <Table.Td>
                <Button color="red" size="xs" onClick={() => handleDeleteRule(rule.id)}>
                    Excluir
                </Button>
            </Table.Td>
        </Table.Tr>
    ));

    return (
        <div>
            <Group justify="space-between" mb="lg">
                <Title order={3}>Regras de Notificação</Title>
                <Button onClick={() => setIsModalOpen(true)} disabled={channels.length === 0}>
                    {channels.length > 0 ? 'Adicionar Regra' : 'Adicione um canal primeiro'}
                </Button>
            </Group>

            <Table striped highlightOnHover withTableBorder>
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th>Nome da Regra</Table.Th>
                        <Table.Th>Provedor</Table.Th>
                        <Table.Th>Severidade</Table.Th>
                        <Table.Th>Canal de Destino</Table.Th>
                        <Table.Th>Ações</Table.Th>
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>{rows.length > 0 ? rows : <Table.Tr><Table.Td colSpan={5}>Nenhuma regra criada.</Table.Td></Table.Tr>}</Table.Tbody>
            </Table>

            <Modal opened={isModalOpen} onClose={() => setIsModalOpen(false)} title="Adicionar Nova Regra">
                <form onSubmit={form.onSubmit(handleAddRule)}>
                    <Stack>
                        <TextInput
                            required
                            label="Nome da Regra"
                            placeholder="Ex: Alertas Críticos da AWS"
                            {...form.getInputProps('name')}
                        />
                        <Select
                            required
                            label="Provedor"
                            placeholder="Selecione o provedor"
                            data={['aws', 'gcp', 'azure', 'huawei', 'google_workspace', 'microsoft_365']}
                            {...form.getInputProps('provider')}
                        />
                        <Select
                            required
                            label="Severidade"
                            placeholder="Selecione a severidade"
                            data={['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFORMATIONAL']}
                            {...form.getInputProps('severity')}
                        />
                        <Select
                            required
                            label="Enviar para o Canal"
                            placeholder="Selecione o canal de notificação"
                            data={channels.map(c => ({ value: String(c.id), label: c.name }))}
                            {...form.getInputProps('channel_id')}
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

export default ManageRules;
