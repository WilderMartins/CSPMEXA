import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

interface AppState {
    // Exemplo de estado global
    theme: 'light' | 'dark';
    toggleTheme: () => void;

    // Estado relacionado à conta selecionada
    selectedAccountId: number | null;
    setSelectedAccountId: (id: number | null) => void;
}

export const useAppStore = create<AppState>()(
    devtools(
        persist(
            (set) => ({
                theme: 'light',
                toggleTheme: () => set((state) => ({ theme: state.theme === 'light' ? 'dark' : 'light' })),

                selectedAccountId: null,
                setSelectedAccountId: (id) => set({ selectedAccountId: id }),
            }),
            {
                name: 'app-storage', // nome do item no localStorage
            }
        )
    )
);
