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
    *   **RDS:** Detalhes de instâncias (configuração, status, endpoint, SGs, MultiAZ, criptografia, backups, logging, etc.), tags.
*   **Motor de Políticas AWS (Básico):**
    *   **S3:** Verificações para ACLs públicas, políticas públicas, versionamento desabilitado, logging desabilitado.
    *   **EC2:** Verificações para Security Groups com acesso público total ou a portas específicas (SSH, RDP), instâncias com IP público, instâncias sem perfil IAM.
    *   **IAM Users:** Verificações para MFA desabilitado, chaves de acesso não utilizadas, chaves de acesso ativas para usuário root.
    *   **RDS:** Verificações para instâncias publicamente acessíveis, armazenamento não criptografado, backups desabilitados ou com baixa retenção.
*   **Persistência de Alertas:**
    *   Os alertas gerados pelo `policy_engine_service` são persistidos em um banco de dados PostgreSQL, permitindo consulta e gerenciamento (listagem, filtragem, atualização de status) via API.
*   **Serviço de Notificação (`notification_service`):**
    *   **E-mail:** Envio de notificações para alertas críticos via e-mail (configurável para usar AWS SES ou SMTP genérico).
    *   **Webhook:** Capacidade de enviar dados de alertas para URLs de webhook configuráveis.
    *   **Google Chat:** Capacidade de enviar mensagens de alerta formatadas para webhooks de espaços do Google Chat.
    *   *Nota: A ativação e configuração específica de cada canal (e para quais alertas/severidades são enviados) é gerenciada no backend, com algumas configurações globais via variáveis de ambiente.*
*   **Coleta de Dados Google Workspace:**
    *   **Usuários:** Detalhes de usuários (ID, email, nome, status de admin, status de 2SV/MFA, último login, data de criação, status da conta - suspenso/arquivado, OU).
    *   **Drive (MVP):** Foco em Drives Compartilhados - Detalhes (ID, nome, restrições de compartilhamento como `domainUsersOnly`, `driveMembersOnly`), e identificação de arquivos dentro desses drives que estão compartilhados publicamente ou via link "qualquer pessoa com o link".
*   **Motor de Políticas Google Workspace (Básico):**
    *   **Usuários:** Verificações para usuários suspensos, 2SV/MFA desabilitado (com criticidade maior para admins), privilégios de admin (informativo), inatividade.
    *   **Drive (MVP):** Verificações para arquivos em Drives Compartilhados que são públicos na web ou acessíveis via link. Verificações para configurações de Drives Compartilhados que permitem membros externos ou acesso a arquivos por não-membros.
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
    *   **GKE (Google Kubernetes Engine):** Detalhes de clusters (configuração, node pools, versões, status, networking, private cluster config, network policy, addons, logging/monitoring, autopilot), localização.
*   **Motor de Políticas GCP (Básico):**
    *   **Cloud Storage:** Verificações para buckets públicos (IAM), versionamento desabilitado, logging desabilitado.
    *   **Compute Engine:** Verificações para VMs com IP público, VMs com Service Account padrão e acesso total, Firewalls VPC permitindo acesso público irrestrito.
    *   **IAM (Projeto):** Verificações para membros externos (`allUsers`, `allAuthenticatedUsers`) com papéis primitivos (Owner, Editor, Viewer).
    *   **GKE:** Verificações para endpoint público do master, NetworkPolicy desabilitada, auto-upgrade de nós desabilitado, integração de logging/monitoring incompleta.
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
        *   Os escopos OAuth 2.0 necessários devem ser autorizados para o Client ID da Service Account no Admin Console. Para Usuários: `https://www.googleapis.com/auth/admin.directory.user.readonly`. Para Drive: `https://www.googleapis.com/auth/drive.readonly`. Outros escopos podem ser necessários para funcionalidades futuras.
    *   `GOOGLE_WORKSPACE_DELEGATED_ADMIN_EMAIL`: O endereço de e-mail de um administrador do Google Workspace que a Service Account irá impersonar. Este administrador deve ter as permissões necessárias para ler os dados desejados.
    *   `GOOGLE_WORKSPACE_CUSTOMER_ID`: (Opcional) O ID do cliente do Google Workspace (ex: `C0xxxxxxx` ou `my_customer` como padrão). Se não definido, o `collector-service` usará `my_customer`.
*   **Google OAuth (para `auth-service`):** Um projeto no Google Cloud Platform com OAuth 2.0 Client ID e Secret configurados.

### 1. Clone o Repositório

```bash
git clone <URL_DO_REPOSITORIO_AQUI> # Substitua pela URL correta
cd cspmexa
```

### 2. Configuração do Ambiente (Usando Docker Compose)

O método recomendado para rodar o ambiente de desenvolvimento completo é utilizando Docker Compose.

1.  **Crie o Arquivo de Configuração `.env` Raiz:**
    *   Na raiz do projeto, copie o arquivo `.env.example` para um novo arquivo chamado `.env`:
        ```bash
        cp .env.example .env
        ```
    *   Edite o arquivo `.env` e preencha **todas** as variáveis necessárias, especialmente:
        *   `JWT_SECRET_KEY`: Gere uma chave forte (ex: `openssl rand -hex 32`).
        *   `INTERNAL_API_KEY`: Gere outra chave forte para a comunicação entre serviços.
        *   Credenciais do Google para OAuth de login (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`).
        *   Caminhos no **seu host** para os arquivos de credenciais JSON do GCP e Google Workspace (`GCP_CREDENTIALS_PATH_HOST`, `GWS_SA_KEY_PATH_HOST`). Crie uma pasta `secrets` na raiz do projeto e coloque os arquivos lá, ou ajuste os caminhos.
        *   Credenciais para AWS, Azure e Huawei Cloud, conforme necessário para os provedores que você deseja testar.
        *   Verifique as portas expostas (`AUTH_DB_EXPOSED_PORT`, `AUTH_SERVICE_PORT`, etc.) se precisar alterar os defaults.

2.  **Build e Inicialização dos Containers:**
    *   Na raiz do projeto, execute:
        ```bash
        docker compose up --build -d
        ```
        O `-d` executa em modo detached (background). Remova-o para ver os logs de todos os serviços no terminal.
        A primeira execução pode demorar um pouco para construir todas as imagens.

3.  **Execute as Migrações do Banco de Dados (para `auth_service`):**
    *   Após os containers estarem rodando (especialmente `cspmexa-postgres`), execute as migrações do Alembic para o `auth_service`. Você pode fazer isso executando um comando dentro do container do `auth_service`:
        ```bash
        docker compose exec auth_service alembic upgrade head
        ```
        Ou, se preferir rodar localmente (requer ambiente Python configurado para `auth_service`):
        Navegue até `cd backend/auth_service`, ative o venv, configure o `.env` local para apontar para o DB do Docker (`AUTH_DB_HOST=localhost`, `AUTH_DB_PORT` conforme definido no `.env` raiz) e rode `alembic upgrade head`. **O método `docker compose exec` é mais simples se o Docker estiver rodando tudo.**

4.  **Acessando os Serviços:**
    *   **Frontend (WebApp):** `http://localhost:${FRONTEND_PORT}` (default: `http://localhost:3000`)
    *   **API Gateway Service (Swagger UI):** `http://localhost:${API_GATEWAY_PORT}/docs` (default: `http://localhost:8050/docs`)
    *   **Outros Backends (Swagger UI):**
        *   Auth Service: `http://localhost:${AUTH_SERVICE_PORT}/docs` (default: `http://localhost:8000/docs`)
        *   Collector Service: `http://localhost:${COLLECTOR_SERVICE_PORT}/docs` (default: `http://localhost:8001/docs`)
        *   Policy Engine Service: `http://localhost:${POLICY_ENGINE_SERVICE_PORT}/docs` (default: `http://localhost:8002/docs`)

    O frontend é servido pelo Nginx e configurado para fazer proxy das chamadas `/api/v1/*` para o `api_gateway_service` dentro da rede Docker.

5.  **Parando os Serviços:**
    ```bash
    docker compose down
    ```
    Para remover os volumes (incluindo dados do banco de dados), adicione `-v`: `docker compose down -v`.

### (Alternativo) Rodando Serviços Individualmente (Desenvolvimento Granular)

Se preferir rodar cada serviço manualmente (sem o Docker Compose principal para todos os serviços, exceto talvez o `postgres_auth_db`), siga os passos abaixo. Isso é útil para depuração focada em um único serviço.

1.  **Inicie o Banco de Dados PostgreSQL:**
    *   Você pode usar o serviço `postgres_auth_db` do `docker-compose.yml` existente:
        ```bash
        docker compose up -d postgres_auth_db
        ```
        Certifique-se que as variáveis `AUTH_DB_USER`, `AUTH_DB_PASSWORD`, `AUTH_DB_NAME` no seu `.env` raiz (ou nos `.env` dos serviços que acessam o DB) correspondem às do serviço `postgres_auth_db`. A porta exposta será `AUTH_DB_EXPOSED_PORT`.

2.  **Para cada serviço backend (`auth_service`, `collector_service`, `policy_engine_service`, `api_gateway_service`):**
    *   Navegue até a pasta do serviço (ex: `cd backend/auth_service`).
    *   Crie um ambiente virtual Python: `python -m venv .venv`.
    *   Ative o ambiente: `source .venv/bin/activate` (Linux/macOS) ou `.venv\Scripts\activate` (Windows).
    *   Instale as dependências: `pip install -r requirements.txt`.
    *   Copie o arquivo `.env.example` local do serviço para `.env` (ex: `cp app/.env.example app/.env`).
    *   Edite o `.env` local e preencha as variáveis. **Importante:**
        *   Para `DATABASE_URL` (no `auth_service` e `policy_engine_service`), use `localhost` e a porta `AUTH_DB_EXPOSED_PORT` se estiver usando o DB do Docker.
        *   Para URLs de outros serviços (no `api_gateway_service`), use `http://localhost:<PORTA_DO_SERVICO_DEPENDENTE>`.
        *   Certifique-se que `JWT_SECRET_KEY` é a mesma entre `auth_service` e `api_gateway_service`.
    *   Se for o `auth_service`, execute as migrações: `alembic upgrade head`.
    *   Inicie o serviço (já configurado para reload se `DEBUG_MODE=true` no `.env` local):
        ```bash
        python app/main.py
        ```

3.  **Para o Frontend (`frontend/webapp`):**
    *   Navegue até `cd frontend/webapp`.
    *   Instale dependências: `npm install`.
    *   Crie um arquivo `.env.development.local` (ou similar, dependendo de como o `vite.config.ts` carrega envs para `VITE_DEV_API_PROXY_TARGET`) se precisar sobrescrever o target do proxy Vite (default `http://localhost:8050`).
    *   Execute: `npm run dev`. O frontend estará em `http://localhost:3000`.

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
