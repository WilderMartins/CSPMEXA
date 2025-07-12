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
*   **@mantine/core & @mantine/hooks:** Biblioteca de componentes UI e hooks.
*   **@mantine/charts:** Para renderização de gráficos.
*   **@tabler/icons-react:** Biblioteca de ícones usada com Mantine.

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
│   │   ├── Dashboard/          # Componentes específicos do Dashboard
│   │   │   ├── ProviderAnalysisSection.tsx
│   │   │   ├── ProviderAnalysisSection.test.tsx
│   │   │   ├── AlertsTable.tsx
│   │   │   └── AlertsTable.test.tsx
│   │   └── Insights/           # Componentes específicos para a página de Insights
│   │       ├── CriticalAssetsDisplay.tsx
│   │       ├── CriticalAssetsDisplay.test.tsx
│   │       ├── AttackPathsDisplay.tsx
│   │       ├── AttackPathsDisplay.test.tsx
│   │       ├── ProactiveRecommendationsDisplay.tsx
│   │       └── ProactiveRecommendationsDisplay.test.tsx
│   ├── contexts/               # Contextos React (ex: AuthContext.tsx)
│   ├── pages/                  # Componentes de página (mapeados para rotas)
│   │   ├── DashboardPage.tsx
│   │   ├── LoginPage.tsx
│   │   ├── ReportsPage.tsx
│   │   └── InsightsPage.tsx
│   ├── services/               # Lógica de chamada de API e manipulação de dados (ex: reportsService.ts)
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

## 7. Integração com Backend

Para detalhes sobre os endpoints de API e schemas de dados que o frontend espera do backend, consulte o [Guia de Integração do Backend](../../docs/backend_integration_guide.md).

## 8. Adicionando Novos Componentes/Páginas

*   **Novas Páginas:**
    1.  Crie o componente da página em `src/pages/NovaPagina.tsx`.
    2.  Adicione a rota em `src/App.tsx`, protegendo-a com a lógica de autenticação se necessário.
    3.  Adicione um link de navegação (se aplicável) no local apropriado (ex: `App.tsx` para navegação principal).
    4.  Adicione as traduções necessárias para os textos da nova página.
*   **Novos Componentes Reutilizáveis:**
    1.  Crie o componente em `src/components/` (ou um subdiretório apropriado).
    2.  Importe e utilize no local desejado.
    3.  Se o componente tiver lógica complexa ou estado próprio, considere escrever testes para ele.

## 9. Considerações Futuras e Melhorias

*   **Integração completa de uma Biblioteca de Componentes UI:** (Concluído com Mantine) - Manter foco em utilizar consistentemente os componentes Mantine.
*   **Gerenciamento de Estado Avançado:** Se a complexidade da aplicação crescer muito, considerar bibliotecas como Zustand ou Jotai para estados globais específicos, complementando o React Context.
*   **Otimizações de Performance:** Continuar monitorando e aplicando otimizações como code splitting, virtualização de listas longas, etc.
*   **Cobertura de Testes:** Expandir a cobertura de testes para abranger mais cenários e componentes.
*   **Tratamento de Erros e Notificações:** Implementar um sistema de notificações global (ex: toasts) para feedback ao usuário (parcialmente melhorado com `ErrorMessage.tsx`).

## 10. Fluxo de Dados para Relatórios e Insights (Considerações de Performance)

Atualmente, as páginas de Relatórios (`ReportsPage.tsx`) e Insights (`InsightsPage.tsx`) operam da seguinte maneira:

1.  **Busca de Dados:** Ambas as páginas buscam uma lista potencialmente grande de alertas (todos os alertas ou todos os alertas abertos, com um limite alto) da API (`GET /alerts`).
2.  **Processamento no Frontend:**
    *   A filtragem por período (para relatórios) é feita no frontend.
    *   A agregação de dados para gerar as contagens para os gráficos (ex: alertas por severidade, por provedor) e para os insights (top políticas, top recursos) também é realizada no frontend, utilizando `useMemo` hooks para otimizar o re-cálculo.

**Limitações da Abordagem Atual:**

*   **Performance:** Para um grande volume de alertas, buscar todos os dados e processá-los no cliente pode se tornar lento e consumir muita memória no navegador.
*   **Transferência de Dados:** Tráfego de rede desnecessário ao buscar dados que poderiam ser agregados ou filtrados no backend.

**Otimizações Sugeridas (Dependem de Evolução do Backend):**

Para melhorar a performance e escalabilidade, as seguintes otimizações na API de backend são recomendadas:

1.  **Endpoints de Agregação para Relatórios:**
    *   A API poderia expor endpoints que já retornam dados agregados.
    *   Exemplo: `GET /api/v1/reports/alerts-by-severity?period=last7days` retornaria `{ "CRITICAL": 10, "HIGH": 25, ... }`.
    *   Exemplo: `GET /api/v1/reports/alerts-by-provider?period=last30days`.
2.  **Endpoints de Agregação para Insights:**
    *   Similarmente, endpoints para buscar diretamente os "top N" dados.
    *   Exemplo: `GET /api/v1/insights/top-violated-policies?count=5&status=OPEN`
    *   Exemplo: `GET /api/v1/insights/top-vulnerable-resources?count=5&status=OPEN`
3.  **Filtragem Avançada no Endpoint `/alerts`:**
    *   Permitir filtros mais granulares diretamente na API, como `date_from`, `date_to`, `status`, e outros campos relevantes, para que o frontend busque apenas o subconjunto de alertas necessário para tabelas detalhadas.

Os arquivos `frontend/webapp/src/utils/reportUtils.ts` e `frontend/webapp/src/utils/insightUtils.ts` contêm a lógica de processamento que atualmente reside no frontend. Com a evolução da API, essa lógica seria gradualmente substituída por chamadas diretas aos novos endpoints otimizados. Os comentários `// TODO:` nos arquivos `ReportsPage.tsx` e `InsightsPage.tsx` indicam os locais onde essas otimizações seriam integradas.

Este README serve como um guia inicial para o desenvolvimento do frontend do CSPMEXA.
```
