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
    *   **Tecnologia:** Python com FastAPI, Pydantic, SQLAlchemy, PostgreSQL.
    *   **Comunicação:** REST API.
    *   **Porta Dev Padrão:** `8000`

2.  **`collector-service` (Serviço de Coleta de Dados):**
    *   **Responsabilidades Atuais (AWS):**
        *   Coleta de dados de configuração para S3 (buckets, ACLs, políticas, versionamento, logging, etc.).
        *   Coleta de dados para EC2 (instâncias, security groups, incluindo dados regionais).
        *   Coleta de dados para IAM (usuários, roles, políticas gerenciadas, com detalhes como MFA, uso de chaves).
    *   **Tecnologia:** Python com FastAPI, Boto3, Pydantic.
    *   **Comunicação:** REST API. Os dados são retornados diretamente nas respostas da API.
    *   **Porta Dev Padrão:** `8001`

3.  **`policy-engine-service` (Serviço do Motor de Políticas):**
    *   **Responsabilidades Atuais (AWS):**
        *   Receber dados de configuração do `collector-service` (via `api-gateway-service`).
        *   Aplicar um conjunto inicial de políticas para S3 (ex: S3 público, versionamento, logging).
        *   Aplicar políticas para EC2 (ex: Security Groups abertos, instâncias com IP público, sem perfil IAM).
        *   Aplicar políticas para Usuários IAM (ex: MFA desabilitado, chaves não usadas, chaves root).
        *   Gerar e retornar uma lista de "Alertas" (descobertas) baseados nas violações de políticas.
    *   **Tecnologia:** Python com FastAPI, Pydantic.
    *   **Comunicação:** REST API (endpoint `/analyze` que aceita dados de vários serviços).
    *   **Porta Dev Padrão:** `8002`

4.  **`api-gateway-service` (Serviço de API Gateway):**
    *   **Responsabilidades Atuais:**
        *   Ponto de entrada único para o frontend.
        *   Proxy para endpoints de autenticação do `auth-service`.
        *   Proxy para endpoints de coleta de dados do `collector-service`.
        *   Endpoints de orquestração que chamam o `collector-service` e depois o `policy-engine-service` para S3, EC2 (Instâncias e SGs) e Usuários IAM.
        *   Validação de token JWT para endpoints protegidos.
    *   **Tecnologia:** Python com FastAPI, Pydantic, HTTPX.
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
    *   **Status:** Não implementado no MVP Alpha. Permanece como um serviço planejado para futuras iterações.

## Escolhas de Banco de Dados (MVP Alpha)

*   **`auth-service`:** PostgreSQL (para usuários, tokens de refresh, configurações de MFA, etc.).
*   **Dados de Configuração da Nuvem (Coletados):** Atualmente, os dados coletados pelo `collector-service` são transitórios. Eles são enviados para o `policy-engine-service` via API Gateway e não são persistidos em um banco de dados dedicado pelo collector ou engine.
*   **Alertas/Resultados de Análise:** Os alertas gerados pelo `policy-engine-service` são retornados ao `api-gateway-service` e, subsequentemente, ao frontend. Não há persistência de alertas no backend neste MVP.

**Limitações do MVP Alpha:**
*   Não há persistência dos dados coletados nem dos alertas gerados. Cada análise é feita sob demanda.
*   O `notification-service` não está implementado.
*   Cobertura de provedores limitada à AWS (S3, EC2, IAM).

## Comunicação entre Microsserviços (MVP Alpha)

*   **Frontend <-> API Gateway:** HTTP/REST.
*   **API Gateway <-> Auth Service:** HTTP/REST.
*   **API Gateway <-> Collector Service:** HTTP/REST (para endpoints de proxy direto e para coleta nos fluxos de orquestração).
*   **API Gateway <-> Policy Engine Service:** HTTP/REST (API Gateway envia dados coletados para o Policy Engine nos fluxos de orquestração).

A comunicação é predominantemente síncrona. Filas de mensagens (RabbitMQ, SQS) para desacoplamento e processamento assíncrono são consideradas para evoluções futuras, especialmente para a coleta de dados e o envio de notificações.

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
        D[Collector Service (AWS) - Porta 8001]
        E[Policy Engine Service - Porta 8002]
        G((Notification Service - Planejado))
    end

    subgraph "Bancos de Dados & Externos"
        DB1[(PostgreSQL - AuthDB)]
        AWSAPI[AWS APIs]
        GoogleOAuth[Google OAuth2 API]
    end

    A <-->|Chamadas API /api/v1/*| B;

    B <-->|Login, Callback| C;
    C --> GoogleOAuth;
    C --- DB1;

    B -->|/collect/* (Proxy)| D;
    B -->|/analyze/* (Coleta)| D;
    D --> AWSAPI;

    B -->|/analyze/* (Análise)| E;
    D -- Dados Coletados (via B) --> E;

    E -- Alertas Gerados (via B) --> A;
    E -.->|Alertas (Futuro)| G;
    G -.->|Email, Webhook (Futuro)| ExternalSystems[Sistemas Externos];

```
*Os dados coletados e alertas não são persistidos no backend neste MVP Alpha.*

## Considerações de Escalabilidade e Evolução

*   **Containerização:** Docker será usado para empacotar cada serviço, facilitando o deploy e a orquestração com Kubernetes no futuro.
*   **CI/CD:** Pipelines básicos no GitHub Actions para build e teste.
*   **Filas de Mensagens:** A introdução de um message broker (RabbitMQ, Kafka, AWS SQS) será crucial para escalar o processamento de dados e alertas.
*   **Bancos de Dados Dedicados:** Conforme a carga aumenta, cada serviço pode ter seu próprio banco de dados otimizado.

Este design inicial provê uma fundação sólida para o MVP e permite expansão futura.
