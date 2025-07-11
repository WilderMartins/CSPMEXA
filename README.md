# CSPMEXA - Cloud Security Posture Management (Alpha)

**CSPMEXA** (nome provisório, podemos alterá-lo!) é um software CSPM (Cloud Security Posture Management) inovador e disruptivo, projetado para monitorar, gerenciar e controlar a postura de segurança de ambientes em nuvem com foco em eficiência, leveza, escalabilidade e personalização.

## Visão Geral

Este projeto visa criar uma solução de segurança em nuvem de ponta, oferecendo:

*   **Monitoramento Contínuo:** Detecção de más configurações e vulnerabilidades em tempo real.
*   **Ampla Compatibilidade:** Suporte aos principais provedores de nuvem (AWS, GCP, Azure, Huawei Cloud) e plataformas SaaS (Google Workspace, Microsoft 365).
*   **Segurança Robusta:** Login seguro com SSO, MFA, RBAC granular e trilhas de auditoria completas.
*   **Arquitetura Moderna:** Baseada em microsserviços, containerizada, escalável e de fácil instalação.
*   **UX Intuitiva:** Design leve, responsivo e acessível, com dashboards interativos e relatórios personalizáveis.
*   **Inteligência Embutida:** Recomendações automáticas, remediação assistida e planos para IA e análise de caminhos de ataque.
*   **Customização:** Totalmente whitelabel e adaptável a múltiplos idiomas.

## Funcionalidades Implementadas (MVP Alpha)

*   **Autenticação:** Login com Google OAuth2.
*   **Coleta de Dados AWS:**
    *   **S3:** Detalhes de buckets, ACLs, políticas, versionamento, logging, configuração de bloqueio de acesso público.
    *   **EC2:** Detalhes de instâncias (estado, tipo, IPs, perfil IAM, SGs, tags, região), Security Groups (regras de entrada/saída, tags, região).
    *   **IAM:** Detalhes de usuários (políticas, MFA, chaves de acesso com último uso, tags), Roles (políticas, assume role policy, último uso, tags), Políticas gerenciadas (documento da política).
*   **Motor de Políticas AWS (Básico):**
    *   **S3:** Verificações para ACLs públicas, políticas públicas, versionamento desabilitado, logging desabilitado.
    *   **EC2:** Verificações para Security Groups com acesso público total ou a portas específicas (SSH, RDP), instâncias com IP público, instâncias sem perfil IAM.
    *   **IAM Users:** Verificações para MFA desabilitado, chaves de acesso não utilizadas, chaves de acesso ativas para usuário root.
*   **Coleta de Dados Azure:**
    *   **Virtual Machines:** Detalhes de VMs (nome, ID, localização, tamanho, tipo de SO, estado de energia, tags), Interfaces de Rede (IPs públicos/privados, NSGs associados).
    *   **Storage Accounts:** Detalhes de Contas de Armazenamento (nome, ID, localização, tipo, SKU), configurações de segurança (acesso público a blobs, versão TLS, HTTPS), propriedades do serviço Blob (versionamento).
*   **Motor de Políticas Azure (Básico):**
    *   **Virtual Machines:** Verificações para VMs com IP público, VMs sem NSG associado à NIC.
    *   **Storage Accounts:** Verificações para Contas de Armazenamento permitindo acesso público a blobs, não exigindo transferência HTTPS, com versionamento de blob desabilitado.
*   **Coleta de Dados GCP (Google Cloud Platform):**
    *   **Cloud Storage:** Detalhes de buckets (IAM, versionamento, logging).
    *   **Compute Engine:** Detalhes de VMs (IPs, Service Accounts, tags), Firewalls VPC (regras).
    *   **IAM:** Políticas IAM a nível de projeto.
*   **Motor de Políticas GCP (Básico):**
    *   **Cloud Storage:** Verificações para buckets públicos (IAM), versionamento desabilitado, logging desabilitado.
    *   **Compute Engine:** Verificações para VMs com IP público, VMs com Service Account padrão e acesso total, Firewalls VPC permitindo acesso público irrestrito.
    *   **IAM (Projeto):** Verificações para membros externos (`allUsers`, `allAuthenticatedUsers`) com papéis primitivos (Owner, Editor, Viewer).
*   **Coleta de Dados Huawei Cloud:**
    *   **OBS (Object Storage Service):** Detalhes de buckets (política, ACL, versionamento, logging).
    *   **ECS (Elastic Cloud Server):** Detalhes de VMs (IPs, SGs associados, etc.).
    *   **VPC (Virtual Private Cloud):** Detalhes de Security Groups e suas regras.
    *   **IAM:** Detalhes de Usuários (status de MFA para console, AK/SKs).
*   **Motor de Políticas Huawei Cloud (Básico):**
    *   **OBS:** Verificações para buckets públicos (política/ACL), versionamento e logging desabilitados.
    *   **ECS/VPC:** Verificações para VMs ECS com IP público, SGs VPC com acesso público.
    *   **IAM Users:** Verificações para MFA de console desabilitado, chaves de acesso inativas.
*   **API Gateway:**
    *   Proxy para endpoints de coleta AWS, GCP, Huawei Cloud e Azure.
    *   Endpoints de orquestração para coletar e analisar dados de AWS, GCP, Huawei Cloud e Azure.
    *   Proteção de endpoints relevantes com JWT.
*   **Frontend (Básico):**
    *   Página de login e callback OAuth.
    *   Dashboard para acionar análises AWS, GCP (requer Project ID), Huawei Cloud (requer Project/Domain ID e Region ID), Azure (requer Subscription ID) e visualizar alertas.
    *   Internacionalização (Inglês, Português-BR).

## Primeiros Passos (Ambiente de Desenvolvimento)

Esta seção descreve como configurar e rodar o ambiente de desenvolvimento localmente.

### Pré-requisitos

*   Git
*   Python 3.9+ e Pip
*   Node.js (v18+) e npm (ou yarn)
*   Docker e Docker Compose (para rodar dependências como PostgreSQL e, opcionalmente, os serviços da aplicação).
*   **Credenciais AWS:** Configuradas localmente para o `collector-service` acessar a AWS (via variáveis de ambiente ou `~/.aws/credentials`).
*   **Credenciais GCP:** Um arquivo JSON de chave de Service Account do GCP. A Service Account deve ter permissões de leitura para os serviços a serem monitorados. Defina a variável de ambiente `GOOGLE_APPLICATION_CREDENTIALS` para o caminho deste arquivo JSON.
*   **Credenciais Huawei Cloud:** Access Key ID (AK), Secret Access Key (SK), Project ID e Domain ID (para IAM) da Huawei Cloud. Configure as variáveis de ambiente: `HUAWEICLOUD_SDK_AK`, `HUAWEICLOUD_SDK_SK`, `HUAWEICLOUD_SDK_PROJECT_ID`, `HUAWEICLOUD_SDK_DOMAIN_ID`.
*   **Credenciais Azure:** Para o `collector-service` acessar o Azure:
    *   `AZURE_SUBSCRIPTION_ID`: ID da Subscrição do Azure.
    *   `AZURE_TENANT_ID`: ID do Tenant do Azure (Directory ID).
    *   `AZURE_CLIENT_ID`: ID do Cliente (Application ID) de um App Registration/Service Principal.
    *   `AZURE_CLIENT_SECRET`: Segredo do Cliente (Chave) do Service Principal.
    O Service Principal deve ter permissões de leitura (como "Reader") na subscrição ou nos grupos de recursos relevantes.
*   **Credenciais Google Workspace:** Para o `collector-service` acessar dados do Google Workspace:
    *   `GOOGLE_SERVICE_ACCOUNT_KEY_PATH`: Caminho absoluto para o arquivo JSON da chave da Service Account do Google Cloud Platform.
        *   A Service Account deve ter a "Delegação em todo o Domínio" habilitada no Google Workspace Admin Console.
        *   Os escopos OAuth 2.0 necessários (ex: `https://www.googleapis.com/auth/admin.directory.user.readonly`) devem ser autorizados para o Client ID da Service Account no Admin Console.
    *   `GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL`: O endereço de e-mail de um administrador do Google Workspace que a Service Account irá impersonar. Este administrador deve ter as permissões necessárias para ler os dados desejados.
    *   `GOOGLE_WORKSPACE_CUSTOMER_ID`: (Opcional) O ID do cliente do Google Workspace (ex: `C0xxxxxxx` ou `my_customer` como padrão). Se não definido, o `collector-service` usará `my_customer`.
*   **Google OAuth (para `auth-service`):** Um projeto no Google Cloud Platform com OAuth 2.0 Client ID e Secret configurados.

### 1. Clone o Repositório

```bash
git clone <URL_DO_REPOSITORIO_AQUI> # Substitua pela URL correta
cd cspmexa
```

### 2. Configuração do Backend

Cada microsserviço backend está localizado em `backend/<nome_do_servico>/`.

**Para cada serviço (`auth_service`, `collector_service`, `policy_engine_service`, `api_gateway_service`):**

1.  **Navegue até a pasta do serviço:** `cd backend/<nome_do_servico>`
2.  **Crie um ambiente virtual Python:** `python -m venv .venv`
3.  **Ative o ambiente:**
    *   Linux/macOS: `source .venv/bin/activate`
    *   Windows: `.venv\Scripts\activate`
4.  **Instale as dependências:** `pip install -r requirements.txt`
5.  **Configure as variáveis de ambiente:**
    *   Copie o arquivo `.env.example` para `.env` (ex: `cp .env.example .env`).
    *   Edite o arquivo `.env` e preencha as variáveis necessárias. Valores padrão para desenvolvimento local (como URLs de outros serviços) geralmente já estão configurados nos `.env.example`.
    *   **`auth_service/.env` (Crítico):**
        *   `DATABASE_URL`: URL de conexão do PostgreSQL (ex: `postgresql://user:password@localhost:5432/authdb_mvp_dev`).
        *   `JWT_SECRET_KEY`: Uma chave secreta forte e única (ex: gerada com `openssl rand -hex 32`). **Deve ser a mesma** no `api_gateway_service`.
        *   `GOOGLE_CLIENT_ID`: Seu Google OAuth Client ID.
        *   `GOOGLE_CLIENT_SECRET`: Seu Google OAuth Client Secret.
        *   `GOOGLE_REDIRECT_URI`: Deve ser `http://localhost:8050/api/v1/auth/google/callback` (aponta para o API Gateway).
        *   `FRONTEND_URL`: `http://localhost:3000` (URL base do frontend).
    *   **`collector_service/.env`:**
        *   `AWS_REGION_NAME`: Região AWS padrão (ex: `us-east-1`).
        *   `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`: Opcional se usando perfis IAM ou variáveis de ambiente globais da AWS.
        *   `POLICY_ENGINE_URL`: `http://localhost:8002/api/v1` (URL base do policy-engine). (Nota: Este é para comunicação direta, o fluxo principal é via Gateway).
        *   **Nota para GCP:** A autenticação é via `GOOGLE_APPLICATION_CREDENTIALS`.
        *   **Nota para Huawei Cloud:** A autenticação é via variáveis de ambiente `HUAWEICLOUD_SDK_AK`, `HUAWEICLOUD_SDK_SK`, `HUAWEICLOUD_SDK_PROJECT_ID`, `HUAWEICLOUD_SDK_DOMAIN_ID`.
    *   **`policy_engine_service/.env`:** Geralmente não requer configuração específica no `.env` para o MVP.
    *   **`api_gateway_service/.env`:**
        *   `AUTH_SERVICE_URL`, `COLLECTOR_SERVICE_URL`, `POLICY_ENGINE_SERVICE_URL`: Verifique se apontam para as portas corretas dos outros serviços locais.
        *   `JWT_SECRET_KEY`: **Deve ser a mesma** chave do `auth_service`.

**Serviços Backend e Portas Padrão (Desenvolvimento Local):**
*   **Auth Service (`auth_service`):** Porta `8000`
*   **Collector Service (`collector_service`):** Porta `8001`
*   **Policy Engine Service (`policy_engine_service`):** Porta `8002`
*   **API Gateway Service (`api_gateway_service`):** Porta `8050` (ponto de entrada principal para o frontend)

### 3. Configuração do Frontend

O frontend é uma aplicação React (Vite) localizada em `frontend/webapp/`.

1.  Navegue até a pasta do frontend: `cd frontend/webapp`
2.  Instale as dependências: `npm install` (ou `yarn install`)

### 4. Rodando a Aplicação Completa (Desenvolvimento Local)

1.  **Inicie o Banco de Dados PostgreSQL:**
    *   Use o Docker Compose fornecido para facilitar:
        ```bash
        docker compose up -d postgresqldb
        ```
        (Certifique-se que `postgresqldb` é o nome do serviço do PostgreSQL no `docker-compose.yml`)
        Aguarde alguns segundos para o banco iniciar.
    *   Alternativamente, se você tem um PostgreSQL rodando localmente, configure o `DATABASE_URL` no `.env` do `auth_service` apropriadamente.

2.  **Execute as Migrações do Banco de Dados (para `auth_service`):**
    *   Navegue até `backend/auth_service`.
    *   Ative o ambiente virtual (`source .venv/bin/activate`).
    *   Execute o Alembic: `alembic upgrade head`

3.  **Inicie os Microsserviços Backend:**
    *   Abra um terminal separado para cada serviço backend (`auth_service`, `collector_service`, `policy_engine_service`, `api_gateway_service`).
    *   Em cada terminal:
        1.  Navegue até a pasta do serviço (ex: `cd backend/auth_service`).
        2.  Ative seu ambiente virtual (`source .venv/bin/activate`).
        3.  Inicie o serviço com Uvicorn (os arquivos `main.py` já estão configurados para rodar com reload na porta correta):
            ```bash
            python app/main.py
            ```
            ou
            ```bash
            uvicorn app.main:app --reload --port <PORTA_DO_SERVICO>
            ```
            (Ex: `uvicorn app.main:app --reload --port 8000` para `auth_service`)

4.  **Inicie o Frontend:**
    *   Abra um novo terminal.
    *   Navegue até `frontend/webapp`.
    *   Execute: `npm run dev`
    *   O frontend estará disponível em `http://localhost:3000`.

    O frontend fará proxy das chamadas `/api/v1/*` para o API Gateway Service na porta `8050`, conforme configurado em `vite.config.ts`.

### Documentação da API (Swagger/OpenAPI)

Quando os serviços backend estiverem rodando, suas documentações OpenAPI (Swagger UI) estarão disponíveis nos seguintes endpoints:
*   **Auth Service:** `http://localhost:8000/docs`
*   **Collector Service:** `http://localhost:8001/docs` (Inclui endpoints para AWS, GCP, Huawei Cloud e Azure)
*   **Policy Engine Service:** `http://localhost:8002/docs`
*   **API Gateway Service:** `http://localhost:8050/docs` (Ponto de entrada principal, documenta todos os endpoints proxy e de orquestração para AWS, GCP, Huawei Cloud e Azure)

*(Nota: Para um ambiente de produção, todos os serviços seriam containerizados e orquestrados de forma mais robusta, por exemplo, com um `docker-compose.yml` completo para todos os serviços ou Kubernetes.)*

## Estrutura do Projeto

```
.
├── backend/         # Código-fonte dos microsserviços do backend
├── docs/            # Documentação técnica, diagramas, etc.
├── frontend/        # Código-fonte da aplicação frontend
├── scripts/         # Scripts de utilidade (build, deploy, etc.)
└── README.md        # Este arquivo
```

## Roadmap de Alto Nível

Consultar o plano de desenvolvimento para o roadmap detalhado das fases e features.

## Contribuição

*(Detalhes sobre como contribuir virão aqui futuramente)*

## Licença

*(Informações sobre a licença do projeto virão aqui)*
---

*Este README é um documento vivo e será atualizado continuamente ao longo do projeto.*
