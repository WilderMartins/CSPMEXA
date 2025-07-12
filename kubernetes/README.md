# Implantação do CSPMEXA em Kubernetes

Este guia descreve como implantar a aplicação CSPMEXA em um cluster Kubernetes. Estes manifestos são projetados para um ambiente de produção e fornecem escalabilidade e alta disponibilidade.

## Pré-requisitos

1.  **Cluster Kubernetes:** Você precisa de acesso a um cluster Kubernetes. Pode ser um cluster gerenciado na nuvem (GKE, EKS, AKS) ou um cluster local (Minikube, Kind, k3s).
2.  **`kubectl`:** A ferramenta de linha de comando do Kubernetes deve estar instalada e configurada para se comunicar com seu cluster.
3.  **Registro de Container:** Você precisará de um registro de container (como Docker Hub, Google Container Registry (GCR), Amazon ECR) para hospedar as imagens dos microsserviços do CSPMEXA.
4.  **Ingress Controller:** Um Ingress Controller (como Nginx Ingress Controller ou Traefik) deve estar instalado em seu cluster para gerenciar o tráfego externo.
5.  **(Opcional, Recomendado) `cert-manager`:** Para gerenciamento automático de certificados TLS/SSL com Let's Encrypt.

## Passo 1: Construir e Enviar as Imagens dos Containers

Antes de aplicar os manifestos, você precisa construir a imagem Docker de cada microsserviço e enviá-la para o seu registro de container.

1.  **Faça login no seu registro de container:**
    ```bash
    # Exemplo para Docker Hub
    docker login
    # Exemplo para GCR
    # gcloud auth configure-docker
    ```

2.  **Para cada serviço** (`auth-service`, `notification-service`, `policy-engine-service`, `collector-service`, `api-gateway-service`, `frontend-webapp`):
    *   Navegue até o diretório do serviço (ex: `cd backend/auth-service`).
    *   Construa a imagem, marcando-a com o nome do seu registro:
        ```bash
        # Substitua <seu-registro> com seu nome de usuário do Docker Hub ou o caminho do seu registro
        docker build -t <seu-registro>/auth-service:latest .
        ```
    *   Envie a imagem para o registro:
        ```bash
        docker push <seu-registro>/auth-service:latest
        ```

3.  **Atualize os Manifestos de Deployment:**
    *   Nos arquivos `kubernetes/*.yml`, procure pela linha `image:` em cada `Deployment` e substitua o placeholder `<SEU_REGISTRO_DE_IMAGEM>` pelo caminho real do seu registro.
    *   Exemplo: `image: seu-usuario-docker/auth-service:latest`

## Passo 2: Configurar Segredos

Os manifestos dependem de alguns `Secrets` do Kubernetes para informações sensíveis. Crie-os antes de aplicar os deployments.

1.  **Segredo do Banco de Dados:**
    *   Edite o arquivo `postgres-config.yml` e altere os valores em `stringData` para `postgres-secret` com um usuário e senha fortes. Depois, aplique-o:
        ```bash
        kubectl apply -f kubernetes/postgres-config.yml
        ```

2.  **Segredo do Token do Vault:**
    *   Edite o arquivo `vault.yml` e altere o token em `stringData` para `vault-token-secret`. Em um ambiente real, este deve ser um token gerado com políticas apropriadas, não o token raiz.
        ```bash
        kubectl apply -f kubernetes/vault.yml
        ```

3.  **Segredo TLS para o Ingress:**
    *   Você precisa de um certificado SSL/TLS para o seu domínio. Se estiver usando `cert-manager`, ele criará o segredo `cspmexa-tls-secret` para você.
    *   Se for criar manualmente, use `kubectl` para criar o segredo a partir dos seus arquivos de certificado e chave:
        ```bash
        kubectl create secret tls cspmexa-tls-secret --key /caminho/para/sua/chave.key --cert /caminho/para/seu/certificado.crt
        ```

## Passo 3: Aplicar os Manifestos

Com as imagens e segredos prontos, você pode aplicar todos os manifestos para implantar a aplicação.

1.  **Navegue até a raiz do projeto.**
2.  **Aplique todos os arquivos de configuração do diretório `kubernetes/`:**
    ```bash
    kubectl apply -f kubernetes/
    ```

## Passo 4: Verificar a Implantação

Aguarde alguns minutos para que o Kubernetes baixe as imagens e inicie todos os containers.

1.  **Verifique o status dos Pods:**
    ```bash
    kubectl get pods -w
    ```
    Espere até que todos os pods estejam com o status `Running`.

2.  **Verifique os Serviços:**
    ```bash
    kubectl get services
    ```
    Você verá os serviços internos (`postgres-service`, `auth-service`, etc.) e o serviço do Ingress.

3.  **Verifique o Ingress:**
    ```bash
    kubectl get ingress cspmexa-ingress
    ```
    Verifique se ele recebeu um `ADDRESS` (endereço de IP externo). Pode levar alguns minutos.

## Acessando a Aplicação

Após o Ingress receber um endereço de IP, configure o DNS do seu domínio (`cspmexa.yourdomain.com`) para apontar para este endereço.

Depois que o DNS se propagar, você poderá acessar sua instância do CSPMEXA de forma segura via `https://cspmexa.yourdomain.com`.
