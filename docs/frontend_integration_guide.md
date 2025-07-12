# Guia de Integração do Frontend com a API CSPMEXA

## 1. Introdução

Este guia destina-se aos desenvolvedores frontend do projeto CSPMEXA. Ele detalha os endpoints da API expostos pelo `api_gateway_service` que o frontend precisará consumir para implementar as funcionalidades da aplicação, como autenticação, visualização de dados, início de análises de segurança e gerenciamento de alertas.

O foco é fornecer informações claras sobre como interagir com o backend, incluindo fluxos de autenticação, formatos de requisição/resposta e as permissões de acesso baseadas em papéis (RBAC).

## 2. URL Base da API

A aplicação frontend é construída usando Vite. A URL base para todas as chamadas de API para o backend (via `api_gateway_service`) deve ser configurada através da variável de ambiente `VITE_API_BASE_URL`.

No ambiente de desenvolvimento com Docker Compose, esta variável é geralmente definida como `http://localhost:${API_GATEWAY_PORT}/api/v1` (onde `API_GATEWAY_PORT` default é `8050`).
Exemplo: `http://localhost:8050/api/v1`

O `apiClient` (instância do Axios) no `DashboardPage.tsx` já utiliza esta variável:
```typescript
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1', // Fallback para /api/v1
  // ... headers
});
```
Todos os caminhos de endpoint neste guia são relativos a esta URL base. Por exemplo, se o endpoint é `/users/me`, a URL completa da chamada seria `[VITE_API_BASE_URL]/users/me`.

## 3. Autenticação

O sistema utiliza OAuth 2.0 com o Google como provedor de identidade. O `auth_service` lida com a lógica OAuth, e o `api_gateway_service` faz proxy para esses endpoints. Após a autenticação bem-sucedida, um token JWT é gerado e deve ser usado pelo frontend para todas as chamadas subsequentes a endpoints protegidos.

### 3.1. Fluxo de Login com Google

1.  **Iniciar Login:**
    *   O frontend deve direcionar o usuário para o endpoint de login do API Gateway:
        *   `GET /auth/google/login`
    *   O API Gateway fará proxy para o `auth_service`, que por sua vez redirecionará o browser do usuário para a página de consentimento do Google.

2.  **Callback do OAuth:**
    *   Após o usuário autorizar no Google, o Google redirecionará de volta para a URI de callback registrada, que é um endpoint no `auth_service`, acessado via API Gateway:
        *   `GET /auth/google/callback?code=<code>&state=<state>`
    *   O `auth_service` (via API Gateway) processará o código, obterá informações do usuário do Google, criará ou atualizará o usuário no banco de dados local, gerará um token JWT interno e, finalmente, redirecionará o browser do usuário de volta para o frontend.
    *   **Redirecionamento para o Frontend:** O `auth_service` redirecionará para a URL configurada em `FRONTEND_URL_AUTH_CALLBACK` (ex: `http://localhost:3000/auth/callback`) e incluirá o token JWT como um parâmetro de query.
        *   Exemplo de URL de redirecionamento para o frontend: `http://localhost:3000/auth/callback?token=<SEU_TOKEN_JWT_AQUI>`
        *   Se o MFA estiver habilitado para o usuário, o redirecionamento será para `FRONTEND_URL_MFA_REQUIRED` (ex: `http://localhost:3000/mfa-login`) com `?user_id=<ID_DO_USUARIO>`.

### 3.2. Tratamento do Token no Frontend

*   **Captura do Token:** Na página de callback do frontend (ex: `/auth/callback`), o componente React (atualmente `OAuthCallbackPage` em `App.tsx`) deve:
    1.  Ler o token JWT do parâmetro de query `token`.
    2.  Armazenar o token de forma segura. Atualmente, ele é armazenado no `localStorage`: `localStorage.setItem('authToken', token);`.
    3.  Redirecionar o usuário para a página principal da aplicação (ex: `/dashboard`).
*   **Tratamento de Erro no Callback:** Se o redirecionamento do `auth_service` contiver um parâmetro `error` (ex: `?error=oauth_failed`), a página de callback do frontend deve exibir uma mensagem de erro apropriada.

### 3.3. Envio do Token JWT em Requisições

*   Para todas as chamadas a endpoints protegidos da API, o frontend deve incluir o token JWT no header `Authorization`.
*   Formato: `Authorization: Bearer <token_jwt_armazenado>`
*   O `apiClient` (Axios) no `DashboardPage.tsx` já está configurado para fazer isso:
    ```typescript
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('authToken')}`
    }
    ```

### 3.4. Verificação de Usuário Autenticado / Informações do Usuário

*   **Endpoint:** `GET /users/me`
*   **Protegido:** Sim (requer token JWT válido).
*   **Resposta de Sucesso (200 OK):** Retorna um objeto JSON com os dados extraídos do token JWT.
    ```json
    {
      "user_id": 123, // ID do usuário no sistema CSPMEXA
      "email": "usuario@example.com",
      "role": "User" // Ou "Administrator", "Manager", etc., conforme o UserRoleEnum
      // Outros claims customizados podem ser adicionados aqui pelo auth_service, como "full_name"
    }
    ```
    *   O frontend pode usar esta chamada para:
        *   Verificar se o token JWT atual ainda é válido (uma resposta 401 indicaria token inválido/expirado).
        *   Obter o `role` do usuário para controlar a exibição de funcionalidades na UI (RBAC no frontend).
        *   Exibir informações do usuário (email, nome).

### 3.5. Logout

*   O logout é primariamente uma operação do lado do cliente.
*   O frontend deve:
    1.  Remover o token JWT do `localStorage`: `localStorage.removeItem('authToken');`.
    2.  Redirecionar o usuário para a página de login (ex: `/`).
*   Não há um endpoint de "logout" no backend para invalidar o token JWT (tokens JWT são stateless). A expiração do token é gerenciada pelo seu claim `exp`. Para um "logout" mais robusto no backend (ex: blacklisting de tokens), seria necessária uma implementação adicional.

---
*(Continuará com as seções de Endpoints de Coleta e Análise, Gerenciamento de Alertas, etc.)*

## 4. Endpoints de Coleta de Dados e Análise de Segurança

Estes endpoints são usados para iniciar varreduras de segurança em provedores de nuvem e plataformas SaaS. Eles são orquestrados pelo `api_gateway_service`: primeiro, os dados de configuração são coletados do provedor alvo (chamando o `collector_service` internamente) e, em seguida, esses dados são enviados ao `policy_engine_service` para análise e geração/persistência de alertas.

Todos os endpoints listados abaixo requerem autenticação (token JWT) e o papel mínimo de **`User`**.

O frontend (`DashboardPage.tsx`) já possui a lógica para chamar esses endpoints.

### 4.1. Formato Geral

*   **Método:** `POST`
*   **Payload da Requisição:** Geralmente um corpo JSON vazio `{}` é suficiente, pois os parâmetros necessários (como IDs de projeto/subscrição) são passados via query string.
*   **Resposta de Sucesso (200 OK):** Uma lista de objetos `AlertSchema` representando os alertas gerados ou atualizados pela análise. Se nenhum alerta for gerado, uma lista vazia `[]` é retornada.
    ```json
    // Exemplo de AlertSchema (simplificado, ver Seção 5 para detalhes)
    [
      {
        "id": 1, // ID do alerta no DB
        "resource_id": "meu-bucket-s3",
        "resource_type": "S3Bucket",
        "provider": "aws",
        "severity": "High", // Valor do AlertSeverityEnum
        "title": "S3 Bucket com ACL de Leitura Pública",
        "description": "O bucket S3 permite leitura pública...",
        "policy_id": "S3_Public_Read_ACL",
        "status": "OPEN", // Valor do AlertStatusEnum
        "account_id": "123456789012",
        "region": "us-east-1",
        "created_at": "2023-10-27T10:30:00Z",
        "updated_at": "2023-10-27T10:30:00Z",
        // ... outros campos como details, recommendation, first_seen_at, last_seen_at
      }
    ]
    ```

### 4.2. Endpoints por Provedor

#### 4.2.1. AWS

*   **Análise de S3 Buckets:**
    *   Endpoint: `/analyze/aws/s3`
*   **Análise de EC2 Instances:**
    *   Endpoint: `/analyze/aws/ec2/instances`
*   **Análise de EC2 Security Groups:**
    *   Endpoint: `/analyze/aws/ec2/security-groups`
*   **Análise de IAM Users:**
    *   Endpoint: `/analyze/aws/iam/users`
*   **Análise de RDS Instances:** (Se implementado e exposto no gateway)
    *   Endpoint: `/analyze/aws/rds/instances` (Verificar se este endpoint existe no `data_router.py` do gateway)

#### 4.2.2. GCP (Google Cloud Platform)

*   Todos os endpoints de análise GCP requerem o parâmetro de query `project_id` (string).
*   **Análise de Cloud Storage Buckets:**
    *   Endpoint: `/analyze/gcp/storage/buckets?project_id=<ID_DO_PROJETO>`
*   **Análise de Compute Engine VMs:**
    *   Endpoint: `/analyze/gcp/compute/instances?project_id=<ID_DO_PROJETO>`
*   **Análise de Compute Engine Firewalls:**
    *   Endpoint: `/analyze/gcp/compute/firewalls?project_id=<ID_DO_PROJETO>`
*   **Análise de IAM de Projeto:**
    *   Endpoint: `/analyze/gcp/iam/project-policies?project_id=<ID_DO_PROJETO>`
*   **Análise de GKE Clusters:**
    *   Endpoint: `/analyze/gcp/gke/clusters?project_id=<ID_DO_PROJETO>&location=<REGIAO_OU_ZONA_OU_'-'_PARA_TODAS>`
    *   Parâmetro de query adicional `location` (string, default: `-`).
*   **Análise de Findings do Security Command Center (SCC):**
    *   Endpoint: `/analyze/gcp/scc/findings?parent_resource=<RECURSO_PAI>&scc_filter=<FILTRO_OPCIONAL>&max_total_results=<NUM_MAX_OPCIONAL>`
    *   Parâmetros:
        *   `parent_resource` (string, obrigatório): Recurso pai para listar findings (ex: `organizations/ID_ORG/sources/-` ou `projects/ID_PROJETO/sources/-`). O sufixo `/sources/-` indica todas as fontes.
        *   `scc_filter` (string, opcional): Filtro da API SCC (ex: `state="ACTIVE" AND severity="HIGH"`).
        *   `max_total_results` (int, opcional, default: 1000): Número máximo de findings a retornar.
*   **Análise de Ativos do Cloud Asset Inventory (CAI):**
    *   Endpoint: `/analyze/gcp/cai/assets?scope=<ESCOPO>&asset_types=<TIPOS_OPCIONAL>&content_type=<TIPO_CONTEUDO_OPC>&max_total_results=<NUM_MAX_OPCIONAL>`
    *   Parâmetros:
        *   `scope` (string, obrigatório): Escopo da consulta (ex: `projects/ID_PROJETO`, `organizations/ID_ORG`).
        *   `asset_types` (lista de strings, opcional): Tipos de ativos (ex: `compute.googleapis.com/Instance`).
        *   `content_type` (string, opcional, default: `RESOURCE`): `RESOURCE`, `IAM_POLICY`, etc.
        *   `max_total_results` (int, opcional, default: 1000).
*   **Análise de Cloud Audit Logs:**
    *   Endpoint: `/analyze/gcp/auditlogs?project_ids=<ID_PROJETO_1>&project_ids=<ID_PROJETO_2>&log_filter=<FILTRO_OPCIONAL>&max_total_results=<NUM_MAX_OPCIONAL>`
    *   Parâmetros:
        *   `project_ids` (lista de strings, obrigatório): IDs dos projetos para consulta. (Nota: a API aceita `organizations/{org_id}` ou `folders/{folder_id}` como `resourceNames` para o coletor, o endpoint do gateway pode precisar ser ajustado para aceitar um `resource_scope` mais genérico em vez de apenas `project_ids`).
        *   `log_filter` (string, opcional): Filtro avançado da API de Logging.
        *   `max_total_results` (int, opcional, default: 1000).

#### 4.2.3. Azure

*   Todos os endpoints de análise Azure requerem o parâmetro de query `subscription_id` (string).
*   **Análise de Virtual Machines:**
    *   Endpoint: `/analyze/azure/virtualmachines?subscription_id=<ID_DA_SUBSCRICAO>`
*   **Análise de Storage Accounts:**
    *   Endpoint: `/analyze/azure/storageaccounts?subscription_id=<ID_DA_SUBSCRICAO>`

#### 4.2.4. Huawei Cloud

*   A maioria dos endpoints de análise Huawei Cloud requerem os parâmetros de query `project_id` (string) e `region_id` (string).
*   Para IAM Users, `domain_id` (string, opcional) pode ser usado em vez de `project_id` para a coleta, mas o `project_id` geral da conta ainda pode ser relevante para o `account_id` do alerta. O `region_id` é usado para o endpoint do cliente IAM.
*   **Análise de OBS Buckets:**
    *   Endpoint: `/analyze/huawei/obs/buckets?project_id=<ID_DO_PROJETO>&region_id=<ID_DA_REGIAO>`
*   **Análise de ECS Instances:**
    *   Endpoint: `/analyze/huawei/ecs/instances?project_id=<ID_DO_PROJETO>&region_id=<ID_DA_REGIAO>`
*   **Análise de VPC Security Groups:**
    *   Endpoint: `/analyze/huawei/vpc/security-groups?project_id=<ID_DO_PROJETO>&region_id=<ID_DA_REGIAO>`
*   **Análise de IAM Users:**
    *   Endpoint: `/analyze/huawei/iam/users?region_id=<ID_DA_REGIAO_IAM>&domain_id=<ID_DO_DOMINIO_OPCIONAL>`
    *   (O `account_id` nos alertas gerados será o `domain_id` se fornecido, caso contrário, o `project_id` da configuração do cliente Huawei).
*   **Análise de Logs CTS (Cloud Trace Service):**
    *   Endpoint: `/analyze/huawei/cts/traces?project_id=<ID_PROJETO>&region_id=<ID_REGIAO>&tracker_name=<NOME_TRACKER>&max_total_traces=<NUM_MAX>&domain_id=<ID_DOMINIO_OPC>`
    *   Parâmetros:
        *   `project_id` (string, obrigatório)
        *   `region_id` (string, obrigatório)
        *   `tracker_name` (string, default: `system`)
        *   `max_total_traces` (int, default: 1000)
        *   `domain_id` (string, opcional)
*   **Análise de Riscos do Cloud Security Guard (CSG):**
    *   Endpoint: `/analyze/huawei/csg/risks?project_id=<ID_PROJETO>&region_id=<ID_REGIAO>&max_total_results=<NUM_MAX_OPC>&domain_id=<ID_DOMINIO_OPC>`
    *   Parâmetros:
        *   `project_id` (string, obrigatório)
        *   `region_id` (string, obrigatório)
        *   `max_total_results` (int, opcional, default: 1000)
        *   `domain_id` (string, opcional)

#### 4.2.5. Google Workspace

*   Endpoints de análise requerem parâmetros de query opcionais `customer_id` (string, default: `my_customer`) e `delegated_admin_email` (string, email do admin a ser impersonado). Se não fornecidos, o backend tentará usar valores das configurações de ambiente do `collector_service`.
*   **Análise de Usuários:**
    *   Endpoint: `/analyze/googleworkspace/users?customer_id=<ID_CUSTOMER>&delegated_admin_email=<EMAIL_ADMIN>`
*   **Análise de Shared Drives (e arquivos públicos dentro deles):**
    *   Endpoint: `/analyze/googleworkspace/drive/shared-drives?customer_id=<ID_CUSTOMER>&delegated_admin_email=<EMAIL_ADMIN>`
*   **Análise de Audit Logs:**
    *   Endpoint: `/analyze/googleworkspace/auditlogs?application_name=<NOME_APP>&customer_id=<ID_CUSTOMER_OPC>&delegated_admin_email=<EMAIL_ADMIN_OPC>&max_total_results=<NUM_OPC>&start_time_iso=<DATETIME_OPC>&end_time_iso=<DATETIME_OPC>`
    *   Parâmetros:
        *   `application_name` (string, obrigatório): Ex: `login`, `drive`, `admin`, `token`, `groups`, `calendar`, `chat`, `meet`, `user_accounts`, `access_transparency`.
        *   Outros parâmetros são opcionais e permitem filtrar a coleta.

#### 4.2.6. Microsoft 365

*   Os endpoints de análise M365 não requerem parâmetros de query no API Gateway, pois o Tenant ID é configurado no backend.
*   **Análise de Status de MFA de Usuários:**
    *   Endpoint: `/analyze/m365/users-mfa-status`
*   **Análise de Políticas de Acesso Condicional:**
    *   Endpoint: `/analyze/m365/conditional-access-policies`

### 4.3. Endpoints de Coleta Direta (Proxy)

O API Gateway também expõe endpoints `GET /collect/...` que fazem proxy direto para o `collector_service`. Estes podem ser usados para buscar os dados de configuração brutos sem acionar uma análise. O frontend geralmente não precisará deles, preferindo os endpoints `/analyze/...`. Todos requerem papel `User`.

Exemplos:
*   `GET /collect/aws/s3`
*   `GET /collect/gcp/storage/buckets?project_id=<ID_DO_PROJETO>`

Consultar o `api_gateway_service/app/api/v1/data_router.py` para a lista completa.

---
*(Continuará com Gerenciamento de Alertas, Tratamento de Erros, RBAC e i18n)*

## 5. Endpoints de Gerenciamento de Alertas

Estes endpoints permitem interagir com os alertas que foram persistidos pelo `policy_engine_service`. Eles são acessados via `api_gateway_service` que faz proxy para o `policy_engine_service`.

### Schemas Relevantes

*   **`AlertSeverityEnum`**: (String Enum) `"Critical"`, `"High"`, `"Medium"`, `"Low"`, `"Informational"`
*   **`AlertStatusEnum`**: (String Enum) `"OPEN"`, `"ACKNOWLEDGED"`, `"RESOLVED"`, `"IGNORED"`

*   **`AlertSchema` (Resposta para GET, PATCH, PUT, DELETE):**
    ```json
    {
      "id": 1, // int, ID do alerta no DB
      "resource_id": "string",
      "resource_type": "string",
      "account_id": "string (opcional)",
      "region": "string (opcional)",
      "provider": "string", // ex: "aws", "gcp"
      "severity": "AlertSeverityEnum", // ex: "High"
      "title": "string",
      "description": "string",
      "policy_id": "string",
      "status": "AlertStatusEnum", // ex: "OPEN"
      "details": {}, // JSON object, opcional
      "recommendation": "string (opcional)",
      "created_at": "datetime (string ISO 8601)", // Data de criação original do alerta no Policy Engine
      "updated_at": "datetime (string ISO 8601)", // Última atualização do alerta no Policy Engine
      "first_seen_at": "datetime (string ISO 8601)", // Quando este alerta específico (recurso+política) foi visto pela primeira vez
      "last_seen_at": "datetime (string ISO 8601)" // Quando este alerta específico (recurso+política) foi visto pela última vez
    }
    ```

*   **`AlertUpdate` (Payload para `PUT /alerts/{alert_id}`):**
    Permite atualizar `status`, `severity`, `details`, `recommendation`. Todos os campos são opcionais.
    ```json
    {
      "status": "AlertStatusEnum (opcional)", // ex: "ACKNOWLEDGED"
      "severity": "AlertSeverityEnum (opcional)",
      "details": {}, // JSON object, opcional
      "recommendation": "string (opcional)"
    }
    ```

### 5.1. Listar Alertas

*   **Endpoint:** `GET /alerts`
*   **Papel Mínimo:** `User`
*   **Parâmetros de Query Opcionais:**
    *   `skip` (int, default: 0): Número de alertas a pular (paginação).
    *   `limit` (int, default: 100, max: 500): Número máximo de alertas a retornar.
    *   `sort_by` (string, ex: `created_at`, `severity`, `status`): Campo para ordenação. Default: `last_seen_at`.
    *   `sort_order` (string, `asc` ou `desc`, default: `desc`).
    *   `provider` (string, ex: `aws`).
    *   `severity` (string, valor do `AlertSeverityEnum`).
    *   `status` (string, valor do `AlertStatusEnum`).
    *   `resource_id` (string, busca parcial/ilike).
    *   `policy_id` (string).
    *   `account_id` (string).
    *   `region` (string).
    *   `start_date` (string ISO datetime, ex: `2023-01-01T00:00:00Z`): Filtra alertas criados após esta data.
    *   `end_date` (string ISO datetime): Filtra alertas criados antes desta data.
*   **Resposta de Sucesso (200 OK):** Lista de objetos `AlertSchema`.

### 5.2. Obter Detalhes de um Alerta Específico

*   **Endpoint:** `GET /alerts/{alert_id}`
*   **Papel Mínimo:** `User`
*   **Parâmetro de Path:**
    *   `alert_id` (int): ID do alerta.
*   **Resposta de Sucesso (200 OK):** Objeto `AlertSchema`.
*   **Resposta de Erro (404 Not Found):** Se o alerta não existir.

### 5.3. Atualizar Detalhes de um Alerta

*   **Endpoint:** `PUT /alerts/{alert_id}`
*   **Papel Mínimo:** `Manager`
*   **Parâmetro de Path:**
    *   `alert_id` (int): ID do alerta.
*   **Payload da Requisição:** Objeto `AlertUpdate`.
*   **Resposta de Sucesso (200 OK):** Objeto `AlertSchema` atualizado.
*   **Resposta de Erro (404 Not Found):** Se o alerta não existir.

### 5.4. Atualizar Status de um Alerta

*   **Endpoint:** `PATCH /alerts/{alert_id}/status`
*   **Papel Mínimo:** `TechnicalLead`
*   **Parâmetro de Path:**
    *   `alert_id` (int): ID do alerta.
*   **Parâmetro de Query Obrigatório:**
    *   `new_status` (string, valor do `AlertStatusEnum`, ex: `ACKNOWLEDGED`, `RESOLVED`, `IGNORED`).
*   **Resposta de Sucesso (200 OK):** Objeto `AlertSchema` atualizado.
*   **Resposta de Erro (404 Not Found):** Se o alerta não existir.

### 5.5. Deletar um Alerta

*   **Endpoint:** `DELETE /alerts/{alert_id}`
*   **Papel Mínimo:** `Administrator`
*   **Parâmetro de Path:**
    *   `alert_id` (int): ID do alerta.
*   **Resposta de Sucesso (200 OK):** Objeto `AlertSchema` do alerta deletado. (Pode ser 204 No Content se o backend for alterado).
*   **Resposta de Erro (404 Not Found):** Se o alerta não existir.

---
*(Continuará com Tratamento de Erros, RBAC e i18n)*

## 6. Tratamento de Erros da API

O frontend deve estar preparado para lidar com diferentes códigos de status HTTP e formatos de erro retornados pela API Gateway.

*   **200 OK:** Requisição bem-sucedida.
*   **201 Created:** (Menos comum para este CSPM, mas possível se criarmos recursos via API).
*   **202 Accepted:** A requisição foi aceita para processamento (ex: endpoints de notificação que usam `BackgroundTasks`). O corpo da resposta geralmente indica o status "accepted".
*   **204 No Content:** Requisição bem-sucedida, mas não há conteúdo para retornar (ex: um `DELETE` pode retornar isso).
*   **400 Bad Request:** A requisição está malformada ou faltam parâmetros obrigatórios. O corpo da resposta geralmente contém `{"detail": "mensagem de erro"}`.
*   **401 Unauthorized:** O token JWT não foi fornecido, é inválido ou expirou. O frontend deve redirecionar para a página de login. O header `WWW-Authenticate: Bearer` pode estar presente.
*   **403 Forbidden:** O usuário está autenticado (token válido), mas não possui o papel (`role`) necessário para acessar o recurso ou executar a ação. O corpo da resposta geralmente contém `{"detail": "User does not have the required 'RoleName' role."}` ou similar.
*   **404 Not Found:** O recurso solicitado não existe (ex: `GET /alerts/99999` para um alerta inexistente).
*   **422 Unprocessable Entity:** A requisição foi bem formada, mas contém erros semânticos (ex: payload JSON com tipos de dados incorretos que falham na validação Pydantic). O corpo da resposta conterá detalhes sobre os erros de validação:
    ```json
    {
      "detail": [
        {
          "loc": ["body", "campo_com_erro"],
          "msg": "mensagem de erro de validação",
          "type": "tipo_do_erro"
        }
      ]
    }
    ```
*   **500 Internal Server Error:** Um erro inesperado ocorreu no servidor. O corpo da resposta pode conter `{"detail": "mensagem de erro do servidor"}`.
*   **503 Service Unavailable:** Um serviço downstream (ex: `collector_service`) pode estar temporariamente indisponível.
*   **504 Gateway Timeout:** Um serviço downstream demorou demais para responder.

O `apiClient` (Axios) no frontend deve ter interceptores de resposta para lidar com esses erros de forma centralizada, se possível, ou cada chamada deve tratar seus erros.

## 7. Papéis de Usuário (RBAC) e Implicações na UI/UX

Conforme detalhado na seção de segurança do `docs/architecture.md`, o sistema possui os seguintes papéis com permissões hierárquicas:
1.  `User`
2.  `TechnicalLead`
3.  `Manager`
4.  `Administrator`
5.  `SuperAdministrator`

O frontend obtém o papel do usuário atual através do endpoint `GET /users/me`. Com base nesse papel, a UI deve ser ajustada dinamicamente:

*   **Ocultar/Desabilitar Funcionalidades:** Botões ou seções inteiras da UI que correspondem a ações não permitidas para o papel do usuário devem ser ocultados ou desabilitados. Por exemplo:
    *   Um `User` não deve ver botões para editar detalhes de um alerta (`PUT /alerts/{id}`), alterar status para `IGNORED` (se essa for uma decisão de papel mais alto), ou deletar alertas.
    *   Apenas `TechnicalLead` ou superior podem ver opções para alterar status de alertas.
    *   Apenas `Manager` ou superior podem ver opções para editar todos os detalhes de um alerta.
    *   Apenas `Administrator` ou superior podem ver a opção de deletar alertas.
*   **Feedback ao Usuário:** Se uma ação falhar com um status 403 Forbidden, o frontend deve fornecer feedback claro ao usuário de que ele não tem permissão.

## 8. Internacionalização (i18n)

O frontend já utiliza `i18next` para internacionalização (suporte inicial para Inglês 'en' e Português-BR 'pt-BR').

*   Todos os textos visíveis na UI devem ser traduzíveis e gerenciados pelos arquivos de locale (ex: `public/locales/en/translation.json`).
*   O seletor de idioma no header (`App.tsx`) permite ao usuário trocar o idioma.

## 9. Considerações Futuras (Preview para Frontend)

À medida que o backend evolui, o frontend precisará integrar novas funcionalidades, como:

*   **Configuração de Notificações:** Interface para usuários (provavelmente Admins) configurarem para quais alertas e para quais canais (e-mail, webhook específico, sala de Google Chat específica) as notificações devem ser enviadas.
*   **Gerenciamento de Usuários e Papéis:** Interface para `SuperAdministrator` (ou `Administrator`) gerenciar usuários e atribuir papéis.
*   **Visualizações Avançadas de Dados:** Dashboards mais ricos, gráficos de tendência de alertas, etc.
*   **Remediação Assistida:** Interface para guiar usuários em passos de remediação.
*   **Suporte a Microsoft 365:** Novas seções no dashboard para análises do M365.

Este guia será atualizado conforme novas funcionalidades de backend relevantes para o frontend forem implementadas.
