# CSPMEXA Frontend Web Application

## 1. Visão Geral

Esta é a aplicação frontend para o CSPMEXA (Cloud Security Posture Management). Ela fornece a interface do usuário para interagir com os serviços de backend do CSPMEXA, permitindo que os usuários façam login, acionem análises de postura de segurança em nuvem, visualizem alertas, e acessem relatórios e indicadores.

A aplicação é construída como um Single Page Application (SPA).

## 2. Tecnologias Utilizadas

*   **React 18:** Biblioteca principal para construção da interface do usuário.
*   **TypeScript:** Superset do JavaScript que adiciona tipagem estática.
*   **Vite:** Ferramenta de build e servidor de desenvolvimento rápido.
*   **React Router DOM v6:** Para roteamento do lado do cliente.
*   **Axios:** Para realizar chamadas HTTP para a API do backend.
*   **i18next & react-i18next:** Para internacionalização (i18n).
*   **ESLint:** Para linting de código TypeScript/JavaScript.
*   **Jest & React Testing Library:** Para testes unitários e de integração.
    *   `ts-jest` para integração do Jest com TypeScript.
    *   `@testing-library/jest-dom` para matchers customizados.
    *   `axios-mock-adapter` para mockar chamadas Axios em testes.
*   **Recharts:** Para renderização de gráficos nos dashboards.
*   **(Planejado/Simulado)** Uma biblioteca de componentes UI como [Mantine UI](https://mantine.dev/), Chakra UI, ou similar para padronização visual e componentes reutilizáveis. Os exemplos atuais usam simulações desses componentes.

## 3. Estrutura de Pastas (Principais)

```
frontend/webapp/
├── public/                     # Arquivos estáticos e locales para i18n
│   └── locales/
│       ├── en/
│       │   └── translation.json
│       └── pt-BR/
│           └── translation.json
├── src/                        # Código fonte da aplicação
│   ├── assets/                 # Imagens, fontes, etc.
│   ├── components/             # Componentes React reutilizáveis
│   │   └── Dashboard/          # Componentes específicos do Dashboard
│   │       ├── ProviderAnalysisSection.tsx
│   │   ├── ProviderAnalysisSection.tsx
│   │       └── AlertsTable.tsx
│   │   └── Insights/             # Componentes específicos do Dashboard de Insights
│   │       ├── CriticalAssetsDisplay.tsx
│   │       ├── AttackPathsDisplay.tsx
│   │       └── ProactiveRecommendationsDisplay.tsx
│   ├── contexts/               # Contextos React (ex: AuthContext.tsx)
│   ├── pages/                  # Componentes de página (mapeados para rotas)
│   │   ├── DashboardPage.tsx
│   │   ├── LoginPage.tsx
│   │   ├── ReportsPage.tsx
│   │   └── InsightsPage.tsx
│   ├── services/               # Lógica de chamada de API e manipulação de dados
│   │   └── reportsService.ts
│   ├── App.tsx                 # Componente raiz da aplicação, define rotas e layout principal
│   ├── main.tsx                # Ponto de entrada da aplicação, renderiza o App
│   ├── i18n.ts                 # Configuração do i18next
│   ├── setupTests.ts           # Configuração para Jest (mocks globais, etc.)
│   ├── index.css               # Estilos globais
│   └── vite-env.d.ts           # Declarações de tipo para Vite
├── .env.example                # Exemplo de variáveis de ambiente (se houver específicas do frontend)
├── eslint.config.js            # Configuração do ESLint
├── index.html                  # Ponto de entrada HTML para Vite
├── package.json                # Dependências e scripts do projeto
├── tsconfig.json               # Configuração do TypeScript
├── tsconfig.node.json          # Configuração do TypeScript para Node (ex: Vite config)
└── vite.config.ts              # Configuração do Vite (build, proxy de desenvolvimento)
```

## 4. Configuração do Ambiente de Desenvolvimento

1.  **Clone o repositório principal** (se ainda não o fez).
2.  **Navegue até `frontend/webapp`**:
    ```bash
    cd frontend/webapp
    ```
3.  **Instale as dependências**:
    ```bash
    npm install
    # ou
    yarn install
    ```
4.  **Variáveis de Ambiente (Frontend):**
    *   O frontend utiliza o `api-gateway-service` como backend. A URL base da API é configurada em `vite.config.ts` e, para desenvolvimento, utiliza um proxy.
    *   `VITE_DEV_API_PROXY_TARGET`: Define o alvo do proxy de desenvolvimento para o `api-gateway-service`. Por padrão, é `http://localhost:8050`. Pode ser sobrescrito via arquivo `.env` na raiz de `frontend/webapp` (ex: crie `.env.development.local`).
        ```env
        VITE_DEV_API_PROXY_TARGET=http://localhost:8050
        ```
    *   `VITE_API_BASE_URL`: Define o prefixo base para todas as chamadas de API. Por padrão, é `/api/v1`. Esta variável é injetada no build e usada pelo `axios` e `AuthContext`.

5.  **Garanta que o Backend (especialmente `api-gateway-service`) esteja rodando**, conforme as instruções no README principal do projeto.

## 5. Scripts Disponíveis

No diretório `frontend/webapp`:

*   **`npm run dev` ou `yarn dev`**:
    Inicia o servidor de desenvolvimento Vite na porta `3000` (padrão). Acessível em `http://localhost:3000`.
    Inclui Hot Module Replacement (HMR).

*   **`npm run build` ou `yarn build`**:
    Compila a aplicação TypeScript e gera o build de produção na pasta `dist/`.

*   **`npm run lint` ou `yarn lint`**:
    Executa o ESLint para verificar erros de linting e estilo no código.

*   **`npm run preview` ou `yarn preview`**:
    Serve a pasta `dist/` (build de produção) localmente para pré-visualização.

*   **`npm run test` ou `yarn test`**:
    Executa os testes unitários e de integração usando Jest.

## 6. Decisões de Arquitetura e Padrões

*   **Gerenciamento de Estado de Autenticação:**
    *   Utiliza a React Context API (`AuthContext` em `src/contexts/AuthContext.tsx`).
    *   O contexto gerencia o token JWT, informações do usuário e o estado de autenticação.
    *   O token é persistido no `localStorage`.
*   **Chamadas de API:**
    *   `axios` é usado para todas as chamadas HTTP para o backend.
    *   Uma instância base de `axios` é configurada no `AuthContext` (e pode ser reutilizada ou recriada em outros locais) para incluir automaticamente o `baseURL` e o token de autorização.
*   **Roteamento:**
    *   `react-router-dom v6` é usado para o roteamento do lado do cliente.
    *   As rotas são definidas em `App.tsx`. Rotas protegidas verificam o estado de autenticação do `AuthContext`.
*   **Internacionalização (i18n):**
    *   `i18next` e `react-i18next` são usados para suportar múltiplos idiomas.
    *   Os arquivos de tradução JSON estão em `public/locales/{idioma}/translation.json`.
*   **Estilização:**
    *   Estilos globais em `index.css`.
    *   Estilos específicos de componentes em seus respectivos arquivos CSS (ex: `App.css`) ou inline/CSS-in-JS (atualmente mais inline para simulações).
    *   Planejada a adoção de uma biblioteca de UI para componentização e estilização mais robusta.
*   **Testes:**
    *   Jest e React Testing Library para testes.
    *   Foco em testar a lógica de negócios, interações do usuário e renderização de componentes.

## 7. Adicionando Novos Componentes/Páginas

*   **Novas Páginas:**
    1.  Crie o componente da página em `src/pages/NovaPagina.tsx`.
    2.  Adicione a rota em `src/App.tsx`, protegendo-a com a lógica de autenticação se necessário.
    3.  Adicione um link de navegação (se aplicável) no local apropriado (ex: `App.tsx` para navegação principal).
    4.  Adicione as traduções necessárias para os textos da nova página.
*   **Novos Componentes Reutilizáveis:**
    1.  Crie o componente em `src/components/` (ou um subdiretório apropriado).
    2.  Importe e utilize no local desejado.
    3.  Se o componente tiver lógica complexa ou estado próprio, considere escrever testes para ele.

## 8. Considerações Futuras e Melhorias

*   **Integração completa de uma Biblioteca de Componentes UI:** Para melhorar a consistência visual, acessibilidade e velocidade de desenvolvimento.
*   **Gerenciamento de Estado Avançado:** Se a complexidade da aplicação crescer muito, considerar bibliotecas como Zustand ou Jotai para estados globais além da autenticação.
*   **Otimizações de Performance:** Continuar monitorando e aplicando otimizações como code splitting, virtualização de listas longas, etc.
*   **Cobertura de Testes:** Expandir a cobertura de testes para abranger mais cenários e componentes.
*   **Tratamento de Erros e Notificações:** Implementar um sistema de notificações global (ex: toasts) para feedback ao usuário.

Este README serve como um guia inicial para o desenvolvimento do frontend do CSPMEXA.
```
