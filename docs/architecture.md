# Arquitetura de Microsserviços (MVP)

Este documento descreve a arquitetura de microsserviços de alto nível para o MVP do CSPMEXA.

## Visão Geral

A arquitetura é projetada para ser modular, escalável e permitir o desenvolvimento iterativo. O foco inicial é em funcionalidades essenciais para o monitoramento da AWS.

## Microsserviços Implementados (MVP Alpha)

1.  **`auth-service` (Serviço de Autenticação e Autorização):**
    *   **Responsabilidades Atuais:**
        *   Login de usuários via Google OAuth 2.0.
        *   Emissão e validação de tokens JWT.
        *   (Estrutura para RBAC e MFA existe, mas não totalmente explorada na UI/fluxos).
    *   **Tecnologia:** Python com FastAPI, Pydantic, SQLAlchemy, PostgreSQL, python-json-logger, starlette-prometheus.
    *   **Comunicação:** REST API.
    *   **Porta Dev Padrão:** `8000`

2.  **`collector-service` (Serviço de Coleta de Dados):**
    *   **Responsabilidades Atuais (AWS, GCP, Huawei Cloud & Azure):**
        *   **AWS:** Coleta de dados para S3, EC2 (Instâncias, SGs), IAM (Usuários, Roles, Policies).
        *   **GCP:** Coleta de dados para Cloud Storage Buckets, Compute Engine VMs, Firewalls VPC, Políticas IAM de Projeto.
        *   **Huawei Cloud:** Coleta de dados para OBS Buckets, ECS VMs, VPC SGs, IAM Users.
        *   **Azure:** Coleta de dados para Virtual Machines (VMs) e Storage Accounts.
        *   Conexão com APIs dos provedores de nuvem.
        *   Coleta de metadados de configuração.
    *   **Tecnologia:** Python com FastAPI, Boto3 (AWS), google-cloud-python (GCP), huaweicloudsdkpython (Huawei), azure-sdk-for-python (Azure), google-api-python-client (Google Workspace), Pydantic, python-json-logger, starlette-prometheus.
    *   **Comunicação:** REST API. Os dados são retornados diretamente nas respostas da API.
    *   **Porta Dev Padrão:** `8001`

3.  **`policy-engine-service` (Serviço do Motor de Políticas):**
    *   **Responsabilidades Atuais:**
        *   **Inventário de Ativos**: Receber dados de configuração do `collector-service` e persistir informações sobre os ativos da nuvem (VMs, buckets, etc.) em um banco de dados de inventário.
        *   **Análise de Políticas**: Aplicar um conjunto de regras e políticas de segurança contra os dados de configuração coletados para identificar más configurações.
        *   **Análise de Caminhos de Ataque**: Construir um grafo de ativos e suas relações para identificar sequências de vulnerabilidades que poderiam ser exploradas por um atacante.
        *   **Geração de Alertas**: Criar e persistir alertas para cada má configuração ou caminho de ataque encontrado.
    *   **Tecnologia:** Python com FastAPI, Pydantic, SQLAlchemy, **NetworkX** (para análise de grafos), python-json-logger, starlette-prometheus.
    *   **Comunicação:** REST API.
    *   **Porta Dev Padrão:** `8002`

4.  **`api-gateway-service` (Serviço de API Gateway):**
    *   **Responsabilidades Atuais:**
        *   Ponto de entrada único para o frontend.
        *   Proxy para endpoints de autenticação do `auth-service`.
        *   Proxy para endpoints de coleta de dados AWS, GCP, Huawei Cloud, Azure e Google Workspace (Usuários, Drive) do `collector-service`.
        *   Endpoints de orquestração que chamam o `collector-service` e depois o `policy-engine-service` para recursos AWS, GCP, Huawei Cloud, Azure e Google Workspace.
        *   Validação de token JWT para endpoints protegidos.
    *   **Tecnologia:** Python com FastAPI, Pydantic, HTTPX, python-json-logger, starlette-prometheus.
    *   **Comunicação:** REST/HTTP com frontend e outros serviços.
    *   **Porta Dev Padrão:** `8050`

5.  **`webapp-frontend` (Aplicação Frontend):**
    *   **Responsabilidades Atuais:**
        *   Interface de login com Google OAuth2.
        *   Dashboard para iniciar análises de AWS (S3, EC2 Instâncias, SGs, Usuários IAM).
        *   Exibição dos alertas gerados em formato de tabela.
        *   Internacionalização (i18n) básica para EN e PT-BR.
    *   **Tecnologia:** React com TypeScript, Vite, React Router, Axios, i18next.
    *   **Comunicação:** HTTP (REST) com `api-gateway-service`.
    *   **Porta Dev Padrão:** `3000`

6.  **`notification-service` (Serviço de Notificações):**
    *   **Status:** Implementado no MVP Alpha.
    *   **Responsabilidades Atuais:**
        *   Receber payloads de alerta e despachá-los para canais configurados.
        *   **E-mail:** Envio de notificações formatadas em HTML via AWS SES (preferencial) ou SMTP genérico.
        *   **Webhook:** Envio de payloads de alerta JSON para URLs de webhook genéricas.
        *   **Google Chat:** Envio de mensagens de alerta formatadas como cards para webhooks de espaços do Google Chat.
        *   Integrado com `policy-engine-service` para receber alertas críticos.
    *   **Tecnologia:** Python com FastAPI, `httpx` (para webhooks), `boto3` (para SES), python-json-logger, starlette-prometheus. A biblioteca `emails` e `Jinja2` são usadas para formatação de e-mail HTML.
    *   **Comunicação:** REST API (recebe alertas do `policy-engine-service` ou diretamente via API).
    *   **Porta Dev Padrão:** `8003`

## Escolhas de Banco de Dados (MVP Alpha)

*   **`auth-service`**: PostgreSQL. Armazena dados de usuários, roles e contas vinculadas. As migrações são gerenciadas via Alembic.
*   **`policy-engine-service`**: PostgreSQL. Armazena os alertas gerados, o inventário de ativos (`cloud_assets`, `asset_relationships`) e os caminhos de ataque (`attack_paths`). As migrações são gerenciadas via Alembic.
*   **`notification-service`**: PostgreSQL. Armazena os canais e as regras de notificação. As migrações são gerenciadas via Alembic.
*   **Dados de Configuração da Nuvem (Coletados)**: Os dados brutos coletados pelo `collector-service` são enviados para o `policy-engine-service`, que os processa e os salva de forma estruturada no seu banco de dados de inventário.

**Limitações do MVP Alpha:**
*   Os dados de configuração da nuvem coletados não são persistidos; cada análise de configuração é feita sob demanda. (Alertas SÃO persistidos).
*   O `notification-service` está parcialmente implementado (suporta e-mail para alertas críticos). Funcionalidades como configuração de múltiplos destinos ou outros canais (Slack, webhooks) são para futuras iterações.
*   Cobertura de provedores atual: AWS (S3, EC2, IAM), GCP (Cloud Storage, Compute Engine VMs/Firewalls, IAM de Projeto), Huawei Cloud (OBS Buckets, ECS VMs, VPC SGs, IAM Users) e Azure (Virtual Machines, Storage Accounts).
*   Conjunto de políticas de segurança ainda é básico para os serviços e provedores cobertos.

## Comunicação entre Microsserviços (MVP Alpha)

*   **Frontend <-> API Gateway:** HTTP/REST.
*   **API Gateway <-> Auth Service:** HTTP/REST.
*   **API Gateway <-> Collector Service:** HTTP/REST (para endpoints de proxy direto e para coleta nos fluxos de orquestração).
*   **API Gateway <-> Policy Engine Service:** HTTP/REST (API Gateway envia dados coletados para o Policy Engine nos fluxos de orquestração).

A comunicação é predominantemente síncrona. Filas de mensagens (RabbitMQ, SQS) para desacoplamento e processamento assíncrono são consideradas para evoluções futuras, especialmente para a coleta de dados e o envio de notificações.

### Considerações de Segurança na Comunicação Interna:
*   **Autenticação de Usuário Final:** A autenticação do usuário final (via token JWT) é realizada exclusivamente pelo `api-gateway-service`. Os microsserviços internos (Collector, Policy Engine, Notification, Auth Service para operações pós-login) confiam que as requisições originadas do API Gateway já foram autenticadas.
*   **Rede Interna:** Os serviços de backend são projetados para operar dentro de uma rede interna confiável (ex: rede Docker, VPC em nuvem). Não há, neste MVP, autenticação serviço-a-serviço implementada entre os microsserviços internos. O acesso direto a esses serviços de fora da rede interna deve ser bloqueado por configurações de firewall/rede.

### Controle de Acesso Baseado em Função (RBAC) no API Gateway:
*   O `api-gateway-service` implementa restrições de acesso aos seus endpoints com base no papel (`role`) do usuário, contido no token JWT.
*   Os papéis definidos (com hierarquia crescente de permissões) são: `User`, `TechnicalLead`, `Manager`, `Administrator`, `SuperAdministrator`.
*   **Política de Acesso (MVP Alpha):**
    *   **User (Usuário):**
        *   Visualizar informações do próprio perfil (`/users/me`).
        *   Listar e visualizar detalhes de alertas (`GET /alerts`, `GET /alerts/{id}`).
        *   Iniciar coletas de dados e análises de segurança (`GET /collect/...`, `POST /analyze/...`).
    *   **TechnicalLead (Líder Técnico):**
        *   Todas as permissões de `User`.
        *   Modificar o status de alertas (Ex: Acusar Recebimento, Resolver, Ignorar - `PATCH /alerts/{id}/status`).
    *   **Manager (Gerente):**
        *   Todas as permissões de `TechnicalLead`.
        *   Atualizar detalhes de alertas (Ex: descrição, recomendação customizada - `PUT /alerts/{id}`).
    *   **Administrator (Administrador):**
        *   Todas as permissões de `Manager`.
        *   Deletar alertas (`DELETE /alerts/{id}`).
        *   (Futuro) Gerenciar configurações da plataforma.
    *   **SuperAdministrator (Super Administrador):**
        *   Todas as permissões de `Administrator`.
        *   (Futuro) Gerenciar usuários, papéis e configurações globais críticas.
*   Endpoints de autenticação (`/auth/google/login`, `/auth/google/callback`) são públicos.

## Diagrama Conceitual (MVP Alpha)

```mermaid
graph TD
    subgraph "Usuário via Browser"
        A[Frontend (React/TS - Porta 3000)]
    end

    subgraph "Gateway & Orquestração"
        B(API Gateway Service - Porta 8050)
    end

    subgraph "Serviços de Backend"
        C[Auth Service - Porta 8000]
        D[Collector Service (AWS, GCP, Huawei, Azure) - Porta 8001]
        E[Policy Engine Service (AWS, GCP, Huawei, Azure) - Porta 8002]
        G[Notification Service (Email) - Porta 8003]
    end

    subgraph "Bancos de Dados & Externos"
        DB_Auth[(PostgreSQL - AuthDB)]
        DB_Engine[(PostgreSQL - EngineDB)]
        DB_Notify[(PostgreSQL - NotifyDB)]
        AWSAPI[AWS APIs]
        GCPApi[GCP APIs]
        HuaweiAPI[Huawei Cloud APIs]
        AzureAPI[Azure APIs]
        GoogleOAuth[Google OAuth2 API]
        GoogleWorkspaceAPI[Google Workspace APIs]
    end

    subgraph "Monitoramento"
        Prometheus[Prometheus]
        Grafana[Grafana]
    end

    A <-->|Chamadas API /api/v1/*| B;

    B <-->|Login, Callback| C;
    C --> GoogleOAuth;
    C --- DB_Auth;

    B -->|/collect/* (Proxy)| D;
    B -->|/analyze/* (Coleta)| D;
    D --> AWSAPI;
    D --> GCPApi;
    D --> HuaweiAPI;
    D --> AzureAPI;
    D --> GoogleWorkspaceAPI;

    B -->|/analyze/* (Análise)| E;
    D -- Dados Coletados (via B) --> E;

    E -- Alertas Gerados (via B) --> A;
    E ---|Persiste Inventário, Alertas, Caminhos de Ataque| DB_Engine;
    E -->|Aciona Notificação| G;
    G --- DB_Notify;
    G -.->|Envia Notificações| ExternalSystems[Sistemas Externos];

    C -->|Métricas| Prometheus;
    D -->|Métricas| Prometheus;
    E -->|Métricas| Prometheus;
    G -->|Métricas| Prometheus;
    B -->|Métricas| Prometheus;
    Grafana -->|Visualiza| Prometheus;
```
*Os dados de configuração da nuvem coletados são transitórios. Alertas SÃO persistidos no backend neste MVP Alpha.*

## Considerações de Escalabilidade e Evolução

*   **Containerização:** Docker será usado para empacotar cada serviço, facilitando o deploy e a orquestração com Kubernetes no futuro.
*   **CI/CD:** Pipelines básicos no GitHub Actions para build e teste.
*   **Filas de Mensagens:** A introdução de um message broker (RabbitMQ, Kafka, AWS SQS) será crucial para escalar o processamento de dados e alertas.
*   **Bancos de Dados Dedicados:** Conforme a carga aumenta, cada serviço pode ter seu próprio banco de dados otimizado.

Este design inicial provê uma fundação sólida para o MVP e permite expansão futura.

---

## Alvos de Cobertura Detalhada por Provedor (Backlog para Expansão)

Esta seção detalha os serviços e fontes de dados alvo para expansão da cobertura do CSPMEXA, com base no feedback e requisitos. A implementação será iterativa.

### Visão Geral de Capacidades Essenciais por Provedor para CSPM:
Para cada provedor, um CSPM robusto geralmente necessita de integração com serviços que forneçam:
*   **Visibilidade de Ativos:** Descoberta e inventário de todos os recursos.
*   **Logs de Auditoria e Atividade:** Registros detalhados de operações e acessos.
*   **Gerenciamento de Identidade e Acesso (IAM):** Análise de permissões e políticas.
*   **Configurações de Segurança de Serviços Chave:** Monitoramento de armazenamento, computação, rede, etc.
*   **APIs de Segurança Nativas:** Integração com serviços de segurança do provedor (ex: Security Hub, SCC, Defender for Cloud) para consolidar e enriquecer descobertas.

### Cobertura Alvo para AWS:
*   **AWS CloudTrail:** Logs de atividade de API (essencial).
*   **AWS Config:** Avaliação contínua de configurações de recursos (essencial).
*   **AWS Identity and Access Management (IAM):** Análise profunda de permissões, roles, usuários, políticas (aprofundar o existente).
*   **Amazon S3:** Configurações de buckets, acesso público, criptografia (aprofundar o existente).
*   **Amazon EC2 e VPC:** Configurações de instâncias, Security Groups, Network ACLs, Flow Logs (aprofundar o existente).
*   **AWS GuardDuty:** Consumo de descobertas de detecção de ameaças.
*   **Outros Serviços Prioritários (a definir):** RDS (já iniciado), Lambda, EKS, etc.

### Cobertura Alvo para GCP (Google Cloud Platform):
*   **Security Command Center (SCC):** Integração para consumir e correlacionar descobertas (essencial).
*   **Cloud Audit Logs:** Registros de auditoria para operações e acesso a dados (essencial).
*   **Cloud Asset Inventory:** Catalogação e pesquisa de recursos (essencial).
*   **Identity and Access Management (IAM):** Análise de políticas de acesso (aprofundar o existente).
*   **Cloud Storage:** Configurações de buckets, permissões, criptografia (aprofundar o existente).
*   **Compute Engine e VPC:** Segurança de VMs, firewalls, configurações de rede (aprofundar o existente).
*   **Google Kubernetes Engine (GKE):** Configurações de segurança de clusters (aprofundar o existente).
*   **Outros Serviços Prioritários (a definir):** Cloud SQL, BigQuery (permissões), etc.

### Cobertura Alvo para Azure:
*   **Azure Activity Log:** Logs de operações no Azure.
*   **Azure Resource Graph:** Inventário e consulta de recursos.
*   **Microsoft Entra ID (anteriormente Azure AD):** Análise de permissões, configurações de segurança de identidade.
*   **Azure Storage Accounts:** Configurações de segurança de blobs, filas, tabelas (aprofundar o existente).
*   **Azure Virtual Network (VNet) e Network Security Groups (NSGs):** Segurança de rede e VMs (aprofundar o existente).
*   **Microsoft Defender for Cloud:** Consumo de recomendações e alertas de segurança.
*   **Outros Serviços Prioritários (a definir):** Azure SQL Database, Azure Kubernetes Service (AKS), etc.

### Cobertura Alvo para Huawei Cloud:
*   **Cloud Security Guard (CSG):** Integração para obter dados de segurança.
*   **Cloud Trace Service (CTS):** Logs de auditoria (em progresso inicial).
*   **Identity and Access Management (IAM):** Gerenciamento e auditoria de permissões (aprofundar o existente).
*   **Object Storage Service (OBS):** Segurança de buckets (aprofundar o existente).
*   **Virtual Private Cloud (VPC) e Elastic Cloud Server (ECS):** Configurações de rede e VMs (aprofundar o existente).
*   **Outros Serviços Prioritários (a definir).**

### Cobertura Alvo para Google Workspace:
*   **Google Admin Console (via APIs):** Auditoria de configurações de segurança e conformidade.
*   **Audit Reports/Logs (Admin Console):** Logs de atividades de usuários, administradores e eventos de segurança (Gmail, Drive, Calendar, etc.).
*   **Google Drive Security Settings:** Permissões de compartilhamento, acesso, criptografia (aprofundar o existente).
*   **Gmail Security Settings:** Políticas anti-spam/phishing, roteamento, DLP.
*   **Google Meet/Chat Security Settings:** Configurações de segurança de videoconferências e mensagens.
*   **Google Cloud Identity (se aplicável):** Gerenciamento de identidades, autenticação, autorização.

### Cobertura Alvo para Microsoft 365 (Novo Provedor):
*   **Segurança do Tenant:** Políticas de MFA, Acesso Condicional (em progresso inicial).
*   **Exchange Online:** Regras de transporte, anti-spam/malware.
*   **SharePoint Online / OneDrive:** Configurações de compartilhamento externo.
*   **Logs de Auditoria e Atividade de Login.**
*   **Microsoft Defender for Office 365 / Microsoft Secure Score:** Consumo de descobertas.
