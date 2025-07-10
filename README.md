# CSPMEXA - Cloud Security Posture Management (Alpha)

**CSOMEXA** (nome provisório, podemos alterá-lo!) é um software CSPM (Cloud Security Posture Management) inovador e disruptivo, projetado para monitorar, gerenciar e controlar a postura de segurança de ambientes em nuvem com foco em eficiência, leveza, escalabilidade e personalização.

## Visão Geral

Este projeto visa criar uma solução de segurança em nuvem de ponta, oferecendo:

*   **Monitoramento Contínuo:** Detecção de más configurações e vulnerabilidades em tempo real.
*   **Ampla Compatibilidade:** Suporte aos principais provedores de nuvem (AWS, GCP, Azure, Huawei Cloud) e plataformas SaaS (Google Workspace, Microsoft 365).
*   **Segurança Robusta:** Login seguro com SSO, MFA, RBAC granular e trilhas de auditoria completas.
*   **Arquitetura Moderna:** Baseada em microsserviços, containerizada, escalável e de fácil instalação.
*   **UX Intuitiva:** Design leve, responsivo e acessível, com dashboards interativos e relatórios personalizáveis.
*   **Inteligência Embutida:** Recomendações automáticas, remediação assistida e planos para IA e análise de caminhos de ataque.
*   **Customização:** Totalmente whitelabel e adaptável a múltiplos idiomas.

## Primeiros Passos (Ambiente de Desenvolvimento)

Esta seção descreve como configurar e rodar o ambiente de desenvolvimento localmente.

### Pré-requisitos

*   Git
*   Python 3.9+ e Pip
*   Node.js (v18+) e npm/yarn
*   Docker e Docker Compose (recomendado para rodar dependências como PostgreSQL)
*   Credenciais AWS configuradas localmente (para o `collector-service` acessar a AWS).

### 1. Clone o Repositório

```bash
git clone <URL_DO_REPOSITORIO_AQUI>
cd cspmexa
```

### 2. Configuração do Backend

Cada microsserviço backend está localizado em `backend/<nome_do_servico>/`.
Para cada serviço:
*   Crie um ambiente virtual Python: `python -m venv .venv`
*   Ative o ambiente: `source .venv/bin/activate` (Linux/macOS) ou `.venv\Scripts\activate` (Windows)
*   Instale as dependências: `pip install -r requirements.txt`
*   Configure as variáveis de ambiente necessárias (ex: `DATABASE_URL`, `JWT_SECRET_KEY`, credenciais do Google OAuth). Isso pode ser feito criando um arquivo `.env` na raiz de cada serviço e usando `python-dotenv` (que precisaria ser adicionado aos `requirements.txt` e carregado no `config.py` de cada serviço) ou configurando as variáveis diretamente no seu shell.

**Serviços Backend e Portas Padrão (Desenvolvimento):**
*   **Auth Service (`auth_service`):** Porta `8000`
    *   Depende de: PostgreSQL (ex: `postgresql://user:password@localhost:5432/authdb_mvp`)
*   **Collector Service (`collector_service`):** Porta `8001`
*   **Policy Engine Service (`policy_engine_service`):** Porta `8002`
*   **API Gateway Service (`api_gateway_service`):** Porta `8050` (ponto de entrada principal para o frontend)

Para rodar um serviço individualmente (ex: `auth_service`):
```bash
cd backend/auth_service
source .venv/bin/activate # ou equivalente
# Exporte as variáveis de ambiente necessárias se não usar .env
# Ex: export DATABASE_URL="postgresql://user:password@localhost:5432/authdb_mvp"
# Ex: export JWT_SECRET_KEY="seu-segredo-super-secreto"
# Ex: export GOOGLE_CLIENT_ID="seu-google-client-id"
# Ex: export GOOGLE_CLIENT_SECRET="seu-google-client-secret"
uvicorn app.main:app --reload --port 8000
```
Repita para os outros serviços em seus respectivos terminais e portas.

### 3. Configuração do Frontend

O frontend é uma aplicação React (Vite) localizada em `frontend/webapp/`.

```bash
cd frontend/webapp
npm install
```

### 4. Rodando a Aplicação (Desenvolvimento)

1.  **Inicie as dependências:**
    *   Se estiver usando PostgreSQL para o `auth-service`, garanta que ele esteja rodando.
2.  **Inicie os Microsserviços Backend:**
    *   Abra um terminal para cada serviço backend (`auth_service`, `collector_service`, `policy_engine_service`, `api_gateway_service`), navegue até suas pastas, ative seus ambientes virtuais, configure as variáveis de ambiente e rode-os com Uvicorn nas portas especificadas acima.
3.  **Inicie o Frontend:**
    *   Em um novo terminal:
    ```bash
    cd frontend/webapp
    npm run dev
    ```
    O frontend estará disponível em `http://localhost:3000` e fará proxy das chamadas `/api/v1/*` para o API Gateway na porta `8050`.

### Documentação da API (Swagger/OpenAPI)

Quando os serviços backend estiverem rodando, suas documentações OpenAPI estarão disponíveis nos seguintes endpoints:
*   **Auth Service:** `http://localhost:8000/docs`
*   **Collector Service:** `http://localhost:8001/docs`
*   **Policy Engine Service:** `http://localhost:8002/docs`
*   **API Gateway Service:** `http://localhost:8050/docs`

*(Nota: Para um ambiente de produção, todos os serviços seriam containerizados e orquestrados, por exemplo, com Docker Compose ou Kubernetes.)*

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
