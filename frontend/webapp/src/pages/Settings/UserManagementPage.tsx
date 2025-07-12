import React, { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Title, Paper, Table, Select, ActionIcon, Text, Skeleton } from '@mantine/core';
import { IconDeviceFloppy } from '@tabler/icons-react';
import { useAuth } from '../../contexts/AuthContext';
import axios, { AxiosInstance } from 'axios';
import ErrorMessage from '../../components/Common/ErrorMessage';

// Tipos de dados da API
interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'User' | 'TechnicalLead' | 'Manager' | 'Administrator' | 'SuperAdministrator';
}

const UserManagementPage: React.FC = () => {
  const { t } = useTranslation();
  const { token, user } = useAuth();

  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [editingStates, setEditingStates] = useState<Record<number, { role: User['role'], isSubmitting: boolean }>>({});

  const apiClient = useMemo<AxiosInstance>(() => {
    return axios.create({
      baseURL: `${import.meta.env.VITE_API_BASE_URL || '/api/v1'}`,
      headers: { 'Authorization': `Bearer ${token}` }
    });
  }, [token]);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<User[]>('/users/');
      setUsers(response.data || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch users.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [apiClient]);

  const handleRoleChange = (userId: number, newRole: string | null) => {
    if (!newRole) return;
    setEditingStates(prev => ({
        ...prev,
        [userId]: { ...prev[userId], role: newRole as User['role'] }
    }));
  };

  const handleSaveChanges = async (userId: number) => {
    const newRole = editingStates[userId]?.role;
    if (!newRole) return;

    setEditingStates(prev => ({...prev, [userId]: { ...prev[userId], isSubmitting: true }}));
    setError(null);

    try {
        // Presumindo um endpoint PATCH /api/v1/users/{user_id}/role
        await apiClient.patch(`/users/${userId}/role`, { role: newRole });
        // Atualiza a lista local para refletir a mudança imediatamente
        setUsers(prevUsers => prevUsers.map(u => u.id === userId ? { ...u, role: newRole } : u));
    } catch (err: any) {
        setError(err.response?.data?.detail || `Failed to update role for user ${userId}.`);
    } finally {
        setEditingStates(prev => ({...prev, [userId]: { ...prev[userId], isSubmitting: false }}));
    }
  };


  const rows = users.map((u) => {
    const isCurrentUser = u.id === user?.user_id;
    const currentRole = editingStates[u.id]?.role || u.role;
    const isSubmitting = editingStates[u.id]?.isSubmitting || false;

    return (
      <Table.Tr key={u.id}>
        <Table.Td>{u.id}</Table.Td>
        <Table.Td>{u.email}</Table.Td>
        <Table.Td>{u.full_name}</Table.Td>
        <Table.Td>
          <Select
            value={currentRole}
            onChange={(newRole) => handleRoleChange(u.id, newRole)}
            disabled={isCurrentUser || isSubmitting} // Não pode editar o próprio papel
            data={['User', 'TechnicalLead', 'Manager', 'Administrator', 'SuperAdministrator']}
          />
        </Table.Td>
        <Table.Td>
            <ActionIcon
                onClick={() => handleSaveChanges(u.id)}
                disabled={currentRole === u.role || isCurrentUser || isSubmitting}
                loading={isSubmitting}
                variant="light"
            >
                <IconDeviceFloppy size={16} />
            </ActionIcon>
        </Table.Td>
      </Table.Tr>
    );
  });

  if (loading) {
      return (
          <Paper withBorder p="xl" radius="md">
              <Title order={2} mb="lg">{t('settings.users.title', 'User Management')}</Title>
              <Skeleton height={40} mt="md" />
              <Skeleton height={40} mt="xs" />
              <Skeleton height={40} mt="xs" />
          </Paper>
      );
  }

  return (
    <Paper withBorder p="xl" radius="md">
      <Title order={2} mb="lg">{t('settings.users.title', 'User Management')}</Title>
      <ErrorMessage message={error} onClose={() => setError(null)} />
      <Table verticalSpacing="md">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>{t('settings.users.table.id', 'ID')}</Table.Th>
            <Table.Th>{t('settings.users.table.email', 'Email')}</Table.Th>
            <Table.Th>{t('settings.users.table.name', 'Name')}</Table.Th>
            <Table.Th>{t('settings.users.table.role', 'Role')}</Table.Th>
            <Table.Th>{t('settings.users.table.actions', 'Actions')}</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>{rows}</Table.Tbody>
      </Table>
    </Paper>
  );
};

export default UserManagementPage;
