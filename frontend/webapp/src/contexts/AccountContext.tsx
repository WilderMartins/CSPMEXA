import React, { createContext, useState, useContext, useEffect, ReactNode } from 'react';
import { api } from '../services/api';

interface LinkedAccount {
    id: number;
    name: string;
    provider: string;
    account_id: string;
}

interface AccountContextType {
    accounts: LinkedAccount[];
    selectedAccountId: number | null;
    setSelectedAccountId: (id: number | null) => void;
    isLoading: boolean;
}

const AccountContext = createContext<AccountContextType | undefined>(undefined);

export const AccountProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [accounts, setAccounts] = useState<LinkedAccount[]>([]);
    const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        api.get<LinkedAccount[]>('/accounts')
            .then(response => {
                setAccounts(response.data);
                if (response.data.length > 0) {
                    // Seleciona a primeira conta por padrão
                    setSelectedAccountId(response.data[0].id);
                }
                setIsLoading(false);
            })
            .catch(error => {
                console.error("Erro ao buscar contas vinculadas:", error);
                setIsLoading(false);
            });
    }, []);

    const value = { accounts, selectedAccountId, setSelectedAccountId, isLoading };

    return (
        <AccountContext.Provider value={value}>
            {children}
        </AccountContext.Provider>
    );
};

export const useAccount = () => {
    const context = useContext(AccountContext);
    if (context === undefined) {
        throw new Error('useAccount must be used within an AccountProvider');
    }
    return context;
};
