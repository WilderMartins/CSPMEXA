# Guia de Integração do Backend para o Frontend CSPMEXA

**Versão:** 1.0
**Data:** (Data Atual)

## 1. Introdução

Este documento detalha os endpoints de API e os schemas de dados que o frontend do CSPMEXA espera do backend para habilitar todas as suas funcionalidades atuais e planejadas. O objetivo é servir como uma especificação clara para o time de desenvolvimento do backend e facilitar a integração entre as duas partes da aplicação.

Todos os endpoints são prefixados pelo `api-gateway-service`, por exemplo: `/api/v1/...`

## 2. Autenticação

O frontend utiliza Google OAuth2 para autenticação, orquestrado pelo backend.

### 2.1. Início do Fluxo de Login com Google
*   **Frontend Action:** O usuário clica no botão "Login com Google".
*   **Frontend Call:** Redirecionamento para `GET /api/v1/auth/google/login`
*   **Backend Expectation:**
    *   Este endpoint deve iniciar o fluxo OAuth2 com o Google.
    *   Após a autenticação bem-sucedida no Google, o Google redirecionará para o endpoint de callback do backend.

### 2.2. Callback do OAuth e Obtenção do Token
*   **Frontend Action:** O backend (após o callback do Google) redireciona o navegador do usuário para o frontend.
*   **Frontend Expectation (URL de Redirecionamento):** `[URL_BASE_FRONTEND]/auth/callback?token=<SEU_TOKEN_JWT_AQUI>`
    *   Se houver erro: `[URL_BASE_FRONTEND]/?error=<MENSAGEM_DE_ERRO_OU_CODIGO>`
*   **Backend Logic:**
    *   Processar o callback do Google.
    *   Gerar um token JWT para o usuário.
    *   Redirecionar para o frontend, passando o token como parâmetro de query.

### 2.3. Obter Informações do Usuário Autenticado
*   **Frontend Action:** Após receber o token, o frontend o armazena (ex: `localStorage`) e faz uma chamada para obter os detalhes do usuário.
*   **Endpoint:** `GET /api/v1/users/me`
*   **Headers:** `Authorization: Bearer <TOKEN_JWT>`
*   **Backend Expectation (Schema de Resposta - JSON):**
    ```json
    {
      "user_id": "string (id único do usuário)",
      "email": "string (email do usuário)",
      "name": "string (nome do usuário, opcional)",
      "picture": "string (URL da foto do perfil, opcional)"
      // Outros campos relevantes, como papéis/roles, se RBAC estiver implementado
    }
    ```

## 3. Análise de Postura de Segurança (Sob Demanda)

O frontend permite que o usuário inicie análises de postura para diferentes provedores de nuvem e serviços.

### 3.1. Endpoint de Análise Genérico
*   **Frontend Action:** Usuário seleciona um provedor/serviço e clica em "Analisar".
*   **Endpoint:** `POST /api/v1/analyze/{provider}/{service_path}`
    *   `{provider}`: `aws`, `gcp`, `azure`, `huawei`, `googleworkspace`
    *   `{service_path}`:
        *   AWS: `s3`, `ec2/instances`, `ec2/security-groups`, `iam/users`, `rds/instances`
        *   GCP: `storage/buckets`, `compute/instances`, `compute/firewalls`, `iam/project-policies`, `gke/clusters`
        *   Huawei Cloud: `obs/buckets`, `ecs/instances`, `vpc/security-groups`, `iam/users`
        *   Azure: `virtualmachines`, `storageaccounts`
        *   Google Workspace: `users`, `drive/shared-drives`
*   **Headers:** `Authorization: Bearer <TOKEN_JWT>`
*   **Query Parameters (Obrigatórios dependendo do provedor/serviço):**
    *   **GCP:** `project_id=string`
    *   **Huawei Cloud:**
        *   `region_id=string` (obrigatório para todos os serviços Huawei)
        *   `project_id=string` (obrigatório, exceto para `iam/users`)
        *   `domain_id=string` (obrigatório para `iam/users`)
    *   **Azure:** `subscription_id=string`
    *   **Google Workspace:**
        *   `customer_id=string` (opcional, default `my_customer`)
        *   `delegated_admin_email=string` (opcional, se a Service Account precisar impersonar)
*   **Corpo da Requisição:** Vazio (`{}`) para `POST`.
*   **Backend Expectation (Schema de Resposta - JSON):** Uma lista de objetos de Alerta (ver schema 3.2 abaixo). A resposta deve ser a lista de alertas *resultantes desta análise específica*.
    ```json
    [
      // Array de Alertas (ver schema 3.2)
    ]
    ```
*   **Backend Logic:**
    1.  Autenticar o usuário via JWT.
    2.  Identificar o provedor e o serviço com base nos path parameters.
    3.  Validar os query parameters necessários.
    4.  Orquestrar a chamada ao `collector-service` para obter os dados de configuração do provedor/serviço especificado.
    5.  Enviar os dados coletados para o `policy-engine-service` para análise.
    6.  O `policy-engine-service` (ou o `api-gateway-service` após receber do engine) deve persistir os alertas gerados.
    7.  Retornar a lista de alertas gerados/atualizados por esta análise.

### 3.2. Schema do Objeto de Alerta (Usado na resposta de Análise e Listagem)
```json
{
  "id": "integer (ID único do alerta no banco de dados)",
  "resource_id": "string (ID do recurso afetado)",
  "resource_type": "string (Tipo do recurso, ex: 'S3 Bucket', 'EC2 Instance')",
  "account_id": "string (ID da conta/projeto no provedor, opcional)",
  "region": "string (Região do recurso, opcional)",
  "provider": "string (Provedor: 'AWS', 'GCP', 'Azure', 'Huawei', 'GoogleWorkspace')",
  "severity": "string ('Critical', 'High', 'Medium', 'Low', 'Informational')",
  "title": "string (Título conciso do alerta/política violada)",
  "description": "string (Descrição detalhada do problema)",
  "policy_id": "string (ID da política interna que gerou o alerta)",
  "status": "string (Status do alerta, ex: 'Open', 'Closed', 'Acknowledged', 'Suppressed')",
  "details": "object (Objeto JSON com detalhes específicos da configuração que causou o alerta, opcional)",
  "recommendation": "string (Texto com a recomendação para corrigir o problema, opcional)",
  "created_at": "string (ISO 8601 timestamp da criação do alerta)",
  "updated_at": "string (ISO 8601 timestamp da última atualização do alerta)",
  "first_seen_at": "string (ISO 8601 timestamp de quando o problema foi detectado pela primeira vez)",
  "last_seen_at": "string (ISO 8601 timestamp de quando o problema foi detectado pela última vez nesta análise ou de forma contínua)"
}
```

## 4. Listagem de Alertas Persistidos

O frontend precisa de um endpoint para buscar todos os alertas que foram persistidos no sistema.

*   **Endpoint:** `GET /api/v1/alerts`
*   **Headers:** `Authorization: Bearer <TOKEN_JWT>`
*   **Query Parameters (Opcionais para filtro e paginação):**
    *   `limit=integer` (default: 100)
    *   `offset=integer` (default: 0) ou `page=integer` (default: 1, se usar paginação baseada em página)
    *   `sort_by=string` (campo para ordenação, ex: `last_seen_at`, `severity`, `provider`, default: `last_seen_at`)
    *   `sort_order=string` (`asc` ou `desc`, default: `desc`)
    *   `provider=string` (filtrar por provedor)
    *   `severity=string` (filtrar por severidade)
    *   `status=string` (filtrar por status)
    *   `resource_id=string` (filtrar por ID de recurso específico)
    *   `search_term=string` (termo para busca textual em campos como title, description, resource_id)
*   **Backend Expectation (Schema de Resposta - JSON):**
    ```json
    {
      "total_items": "integer (Número total de alertas que correspondem aos filtros, antes da paginação)",
      "items": [
        // Array de Alertas (ver schema 3.2)
      ],
      "page": "integer (Página atual, se aplicável)",
      "per_page": "integer (Itens por página, se aplicável)",
      "total_pages": "integer (Total de páginas, se aplicável)"
    }
    ```
    Ou, se a paginação for mais simples (apenas `items` e talvez um header `X-Total-Count`):
    ```json
    [
      // Array de Alertas (ver schema 3.2)
    ]
    ```
    O frontend atualmente está preparado para uma lista simples de alertas, mas pode ser adaptado para uma resposta paginada mais estruturada.
*   **Backend Logic:** Consultar o banco de dados de alertas, aplicar filtros, ordenação e paginação, e retornar os resultados.

## 5. Dashboard de Relatórios

Estes endpoints são para alimentar a `ReportsPage.tsx`. Eles requerem agregação e, possivelmente, processamento de dados históricos. **A persistência de dados de alertas e configurações ao longo do tempo é crucial aqui.**

### 5.1. Tendência da Pontuação de Segurança
*   **Endpoint:** `GET /api/v1/reports/security-score-trend`
*   **Headers:** `Authorization: Bearer <TOKEN_JWT>`
*   **Query Parameters (Opcionais):**
    *   `period='daily' | 'weekly' | 'monthly' | 'custom'` (default: `weekly`)
    *   `range_start=YYYY-MM-DD` (usado se `period='custom'`)
    *   `range_end=YYYY-MM-DD` (usado se `period='custom'`)
    *   `provider=string` (ex: 'AWS', 'GCP', '' para todos)
*   **Backend Expectation (Schema de Resposta - JSON):**
    ```json
    [
      {
        "date": "YYYY-MM-DD",
        "overallScore": "number (0-100)",
        "awsScore": "number (opcional)",
        "gcpScore": "number (opcional)",
        // ... outras pontuações por provedor
        "criticalAlerts": "integer",
        "highAlerts": "integer"
      }
      // ... mais pontos de dados
    ]
    ```

### 5.2. Resumo de Alertas
*   **Endpoint:** `GET /api/v1/reports/alerts-summary`
*   **Headers:** `Authorization: Bearer <TOKEN_JWT>`
*   **Query Parameters:**
    *   `group_by='severity' | 'status' | 'provider' | 'resource_type'` (default: `severity`)
    *   `provider=string` (opcional, para filtrar antes de agrupar)
    *   `period='daily' | 'weekly' | 'monthly' | 'custom'` (opcional)
    *   `range_start=YYYY-MM-DD` (opcional)
    *   `range_end=YYYY-MM-DD` (opcional)
*   **Backend Expectation (Schema de Resposta - JSON):**
    *   Se `group_by='severity'`:
        ```json
        [
          { "severity": "Critical", "count": "integer", "percentage": "number (opcional)" },
          // ... outras severidades
        ]
        ```
    *   Se `group_by='provider'`:
        ```json
        [
          { "provider": "AWS", "count": "integer", "openAlerts": "integer (opcional)" },
          // ... outros provedores
        ]
        ```
    *   Estruturas similares para outros `group_by`.

### 5.3. Visão Geral de Compliance (se aplicável)
*   **Endpoint:** `GET /api/v1/reports/compliance-overview`
*   **Headers:** `Authorization: Bearer <TOKEN_JWT>`
*   **Query Parameters (Opcionais):**
    *   `framework=string` (ex: 'cis', 'nist', '' para um default ou resumo geral)
    *   `provider=string`
*   **Backend Expectation (Schema de Resposta - JSON):**
    ```json
    {
      "framework": "string (Nome do framework)",
      "overallCompliance": "number (percentual)",
      "controls": [
        {
          "controlId": "string",
          "description": "string",
          "status": "'Compliant' | 'Non-Compliant' | 'Not-Assessed'",
          "failingChecks": "integer",
          "totalChecks": "integer"
        }
        // ... mais controles
      ]
    }
    ```

### 5.4. Principais Riscos
*   **Endpoint:** `GET /api/v1/reports/top-risks`
*   **Headers:** `Authorization: Bearer <TOKEN_JWT>`
*   **Query Parameters (Opcionais):**
    *   `limit=integer` (default: 10)
    *   `provider=string`
    *   `severity='Critical' | 'High' | ''` (severidade mínima, opcional)
*   **Backend Expectation (Schema de Resposta - JSON):**
    ```json
    [
      {
        "policyTitle": "string (Título da política/tipo de risco)",
        "severity": "string",
        "instanceCount": "integer (quantos recursos são afetados por este tipo de risco)",
        "provider": "string (opcional, se não filtrado)"
      }
      // ... mais riscos
    ]
    ```

## 6. Dashboard de Insights

Estes endpoints são para alimentar a `InsightsPage.tsx` e geralmente requerem lógica de análise mais complexa no backend.

### 6.1. Ativos Críticos em Risco
*   **Endpoint:** `GET /api/v1/insights/critical-assets`
*   **Headers:** `Authorization: Bearer <TOKEN_JWT>`
*   **Query Parameters (Opcionais):**
    *   `provider=string`
*   **Backend Expectation (Schema de Resposta - JSON):**
    ```json
    [
      {
        "id": "string (ID único do ativo)",
        "name": "string (Nome do ativo)",
        "type": "string (Tipo do ativo)",
        "riskScore": "number (0-100)",
        "relatedAlertsCount": "integer",
        "provider": "string"
      }
      // ... mais ativos
    ]
    ```

### 6.2. Caminhos de Ataque Potenciais (Simplificado)
*   **Endpoint:** `GET /api/v1/insights/attack-paths`
*   **Headers:** `Authorization: Bearer <TOKEN_JWT>`
*   **Query Parameters (Opcionais):**
    *   `provider=string`
*   **Backend Expectation (Schema de Resposta - JSON):**
    ```json
    [
      {
        "id": "string (ID único do caminho de ataque)",
        "description": "string (Descrição resumida)",
        "path": [
          {
            "resourceId": "string",
            "resourceType": "string",
            "vulnerability": "string (Descrição da vulnerabilidade neste segmento)"
          }
          // ... mais segmentos
        ],
        "severity": "'High' | 'Medium' | 'Low'"
      }
      // ... mais caminhos
    ]
    ```

### 6.3. Recomendações Proativas
*   **Endpoint:** `GET /api/v1/insights/proactive-recommendations`
*   **Headers:** `Authorization: Bearer <TOKEN_JWT>`
*   **Query Parameters (Opcionais):**
    *   `category=string` (ex: 'IAM', 'Network')
*   **Backend Expectation (Schema de Resposta - JSON):**
    ```json
    [
      {
        "id": "string (ID único da recomendação)",
        "title": "string",
        "description": "string",
        "category": "string",
        "severity": "'High' | 'Medium' | 'Low'"
      }
      // ... mais recomendações
    ]
    ```

## 7. Considerações Gerais para o Backend

*   **Persistência de Dados:** Para que os Relatórios e Insights sejam significativos, os dados de configuração coletados e os alertas gerados precisam ser persistidos historicamente. O modelo de dados deve permitir consultas eficientes ao longo do tempo.
*   **Performance e Agregação:** Muitos endpoints de relatório exigirão agregação de dados. Considere estratégias para otimizar essas consultas (índices, views materializadas, ou um serviço de agregação/data warehousing separado se o volume for muito alto).
*   **Tratamento de Erros:** Implementar tratamento de erros consistente e retornar códigos de status HTTP apropriados com mensagens de erro claras em JSON (ex: `{"error": "mensagem", "details": "..."}`).
*   **Segurança e RBAC:** Todos os endpoints devem ser protegidos e, se o sistema implementar Role-Based Access Control (RBAC), os dados retornados devem ser filtrados de acordo com as permissões do usuário autenticado.
*   **Paginação e Ordenação:** Para endpoints que retornam listas (especialmente `/alerts`), implementar paginação e ordenação robustas no lado do servidor.
*   **Consistência de Schemas:** Manter consistência nos nomes de campos e tipos de dados entre diferentes endpoints sempre que possível.

Este guia deve fornecer uma base sólida para o desenvolvimento dos endpoints do backend necessários para o frontend do CSPMEXA. Recomenda-se uma comunicação contínua entre as equipes de frontend e backend para refinar esses requisitos à medida que o desenvolvimento avança.
