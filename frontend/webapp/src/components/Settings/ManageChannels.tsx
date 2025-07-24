import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Table, Button, Modal, TextInput, Select, Group, Title, Stack } from '@mantine/core';
import { useForm } from '@mantine/form';
import apiClient from '../../services/api';
import { showNotification } from '@mantine/notifications';

interface Channel {
    id: number;
    name: string;
    type: string;
    configuration: string;
}

const ManageChannels: React.FC = () => {
    const { t } = useTranslation();
    const [channels, setChannels] = useState<Channel[]>([]);
    const [isModalOpen, setIsModalOpen] = useState(false);

    const form = useForm({
        initialValues: {
            name: '',
            type: 'webhook',
            configuration: '',
        },
        validate: {
            name: (value) => (value.length > 2 ? null : 'O nome deve ter pelo menos 3 caracteres'),
            configuration: (value) => (value.includes('http') ? null : 'A configuração parece inválida (ex: URL para webhook)'),
        },
    });

    const fetchChannels = async () => {
        try {
            const response = await apiClient.get<Channel[]>('/management/channels');
            setChannels(response.data);
        } catch (error) {
            console.error("Erro ao buscar canais:", error);
            showNotification({
                title: 'Erro',
                message: 'Não foi possível carregar os canais de notificação.',
                color: 'red',
            });
        }
    };

    useEffect(() => {
        fetchChannels();
    }, []);

    const handleAddChannel = async (values: typeof form.values) => {
        try {
            await apiClient.post('/management/channels', values);
            showNotification({
                title: 'Sucesso!',
                message: 'Canal de notificação adicionado com sucesso.',
                color: 'green',
            });
            fetchChannels(); // Re-fetch a lista
            setIsModalOpen(false);
            form.reset();
        } catch (error) {
            console.error("Erro ao adicionar canal:", error);
            showNotification({
                title: 'Erro',
                message: 'Não foi possível adicionar o canal.',
                color: 'red',
            });
        }
    };

    const handleDeleteChannel = async (channelId: number) => {
        try {
            await apiClient.delete(`/management/channels/${channelId}`);
            showNotification({
                title: 'Sucesso!',
                message: 'Canal de notificação removido com sucesso.',
                color: 'teal',
            });
            fetchChannels(); // Re-fetch a lista
        } catch (error) {
            console.error("Erro ao remover canal:", error);
            showNotification({
                title: 'Erro',
                message: 'Não foi possível remover o canal.',
                color: 'red',
            });
        }
    };

    const rows = channels.map((channel) => (
        <Table.Tr key={channel.id}>
            <Table.Td>{channel.name}</Table.Td>
            <Table.Td>{channel.type.toUpperCase()}</Table.Td>
            <Table.Td>{channel.configuration}</Table.Td>
            <Table.Td>
                <Button color="red" size="xs" onClick={() => handleDeleteChannel(channel.id)}>
                    Excluir
                </Button>
            </Table.Td>
        </Table.Tr>
    ));

    return (
        <div>
            <Group justify="space-between" mb="lg">
                <Title order={3}>Canais de Notificação</Title>
                <Button onClick={() => setIsModalOpen(true)}>Adicionar Canal</Button>
            </Group>

            <Table striped highlightOnHover withTableBorder>
                <Table.Thead>
                    <Table.Tr>
                        <Table.Th>Nome</Table.Th>
                        <Table.Th>Tipo</Table.Th>
                        <Table.Th>Configuração (URL/Email)</Table.Th>
                        <Table.Th>Ações</Table.Th>
                    </Table.Tr>
                </Table.Thead>
                <Table.Tbody>{rows}</Table.Tbody>
            </Table>

            <Modal opened={isModalOpen} onClose={() => setIsModalOpen(false)} title="Adicionar Novo Canal">
                <form onSubmit={form.onSubmit(handleAddChannel)}>
                    <Stack>
                        <TextInput
                            required
                            label="Nome do Canal"
                            placeholder="Ex: Webhook do Slack #security-alerts"
                            {...form.getInputProps('name')}
                        />
                        <Select
                            required
                            label="Tipo de Canal"
                            data={[
                                { value: 'webhook', label: 'Webhook' },
                                { value: 'email', label: 'E-mail' },
                                { value: 'google_chat', label: 'Google Chat' },
                            ]}
                            {...form.getInputProps('type')}
                        />
                        <TextInput
                            required
                            label="Configuração (URL ou Email)"
                            placeholder="Cole a URL do webhook ou o endereço de e-mail"
                            {...form.getInputProps('configuration')}
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

export default ManageChannels;
