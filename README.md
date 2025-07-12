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

## Instalação Rápida

A instalação do CSPMEXA foi projetada para ser simples e rápida, mesmo para usuários sem experiência técnica, graças ao nosso assistente de instalação.

Para instruções detalhadas e passo a passo, por favor, consulte o nosso guia de instalação:

➡️ **[Guia de Instalação (INSTALL.md)](./INSTALL.md)**

O guia irá orientá-lo através do processo de:
1.  Preparar seu servidor com os pré-requisitos (Docker).
2.  Baixar o projeto.
3.  Executar o assistente de instalação web que configurará tudo para você.

### Para Desenvolvedores

Se você é um desenvolvedor e deseja entender a fundo a arquitetura ou contribuir com o projeto, a documentação técnica e os `.env.example` dentro de cada serviço continuam disponíveis como referência. O ponto de entrada para a orquestração de todos os serviços é o arquivo `docker-compose.yml`.

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
