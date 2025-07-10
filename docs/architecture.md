# Arquitetura de Microsserviços (MVP)

Este documento descreve a arquitetura de microsserviços de alto nível para o MVP do CSPMEXA.

## Visão Geral

A arquitetura é projetada para ser modular, escalável e permitir o desenvolvimento iterativo. O foco inicial é em funcionalidades essenciais para o monitoramento da AWS.

## Microsserviços Propostos

1.  **`auth-service` (Serviço de Autenticação e Autorização):**
    *   **Responsabilidades:**
        *   Login de usuários (OAuth 2.0 com Google para o MVP).
        *   Emissão e validação de tokens JWT.
        *   RBAC (Admin, Usuário - MVP).
        *   Gerenciamento de MFA (TOTP).
        *   Trilhas de auditoria de autenticação.
    *   **Tecnologia (Backend):** Python com FastAPI, Pydantic, PostgreSQL.
    *   **Comunicação:** REST API.
    *   **Porta Dev Padrão:** `8000`

2.  **`collector-service` (Serviço de Coleta de Dados):**
    *   **Responsabilidades:**
        *   Conexão com APIs de provedores de nuvem (AWS para o MVP - S3, EC2, IAM).
        *   Coleta de metadados de configuração.
        *   Envio de dados para processamento/armazenamento.
    *   **Tecnologia (Backend):** Python com FastAPI, Boto3.
    *   **Comunicação:** Invocado via REST API ou agendado. Publica dados (ex: via fila de mensagens ou API para o Policy Engine).
    *   **Porta Dev Padrão:** `8001`

3.  **`policy-engine-service` (Serviço do Motor de Políticas):**
    *   **Responsabilidades:**
        *   Receber dados de configuração.
        *   Aplicar regras/políticas (ex: S3 público, Security Groups abertos).
        *   Identificar violações e gerar alertas.
    *   **Tecnologia (Backend):** Python com FastAPI.
    *   **Comunicação:** Consome dados (via fila ou API). Publica alertas.
    *   **Porta Dev Padrão:** `8002`

4.  **`api-gateway-service` (Serviço de API Gateway):**
    *   **Responsabilidades:**
        *   Ponto de entrada único para o frontend.
        *   Roteamento para microsserviços.
        *   Autenticação/Autorização de requisições (validação de JWT).
        *   Documentação da API (OpenAPI/Swagger).
    *   **Tecnologia (Backend):** Python com FastAPI.
    *   **Comunicação:** REST/HTTP com frontend e outros serviços.
    *   **Porta Dev Padrão:** `8050`

5.  **`webapp-frontend` (Aplicação Frontend):**
    *   **Responsabilidades:**
        *   Interface do usuário (Login, Dashboards, Alertas).
        *   Interação com `api-gateway-service`.
    *   **Tecnologia:** React com TypeScript (Vite).
    *   **Comunicação:** HTTP (REST) com `api-gateway-service`.
    *   **Porta Dev Padrão:** `3000` (servidor de desenvolvimento Vite)

6.  **`notification-service` (Serviço de Notificações) - Simplificado no MVP:**
    *   **Responsabilidades:**
        *   Receber alertas.
        *   Enviar notificações (E-mail via AWS SES para o MVP).
    *   **Tecnologia (Backend):** Python com FastAPI.
    *   **Comunicação:** Consome alertas (via fila ou API).
    *   **Porta Dev Padrão:** (Não implementado no MVP inicial, mas seria ex: `8003`)

## Escolhas de Banco de Dados (MVP)

*   **`auth-service`:** PostgreSQL (usuários, credenciais, tokens, MFA).
*   **Dados de Configuração da Nuvem (Coletados):** Para o MVP, inicialmente podemos usar JSONs armazenados em um bucket S3 (ou similar) para simplicidade, processados em batch pelo `policy-engine-service`. Uma evolução natural seria MongoDB ou similar para flexibilidade.
*   **Alertas/Resultados de Análise:** Podem ser armazenados no PostgreSQL inicialmente, ou junto aos dados de configuração se um NoSQL for usado.

## Comunicação entre Microsserviços (MVP)

*   **Síncrona:** REST APIs (HTTP/JSON) para a maioria das interações diretas.
*   **Assíncrona:** Para o MVP, chamadas diretas de API entre serviços como `collector-service` -> `policy-engine-service`. Filas de mensagens (RabbitMQ, SQS) são um objetivo para desacoplamento futuro.

## Diagrama Conceitual (MVP)

```mermaid
graph TD
    A[Frontend (React/TS)] <--> B(API Gateway Service);
    B --> C{Auth Service};
    B --> D[Collector Service];
    D -- Dados Coletados --> E((Data Store MVP - S3/JSON));
    E --> F[Policy Engine Service];
    B --> F;
    F -- Alertas --> G{Notification Service};
    C --- DB1[(PostgreSQL - Usuários)];
    G --- SES[AWS SES];
```

*(Nota: O diagrama acima usa sintaxe Mermaid. Pode ser renderizado em visualizadores compatíveis.)*

## Considerações de Escalabilidade e Evolução

*   **Containerização:** Docker será usado para empacotar cada serviço, facilitando o deploy e a orquestração com Kubernetes no futuro.
*   **CI/CD:** Pipelines básicos no GitHub Actions para build e teste.
*   **Filas de Mensagens:** A introdução de um message broker (RabbitMQ, Kafka, AWS SQS) será crucial para escalar o processamento de dados e alertas.
*   **Bancos de Dados Dedicados:** Conforme a carga aumenta, cada serviço pode ter seu próprio banco de dados otimizado.

Este design inicial provê uma fundação sólida para o MVP e permite expansão futura.
