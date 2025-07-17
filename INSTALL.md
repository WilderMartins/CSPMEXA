# Guia de Instalação do CSPMEXA (via Docker Compose)

**Nota:** Este guia descreve o método de instalação usando Docker Compose, ideal para ambientes de desenvolvimento, testes ou implantações de pequena escala. Para implantações de produção, consulte o nosso **[Guia de Implantação em Kubernetes](./kubernetes/README.md)**.

---

Bem-vindo ao guia de instalação do CSPMEXA!

## Passo 1: Pré-requisitos

Antes de começar, você precisa de um servidor (ou máquina local) com um sistema operacional Linux e as seguintes ferramentas instaladas:

*   **Docker e Docker Compose**: Usados para orquestrar os contêineres da aplicação.
*   **Git**: Para clonar o repositório do projeto.

### 1.1 - Instalando o Docker e Docker Compose

Se você ainda não tem o Docker instalado, siga o [guia oficial do Docker](https://docs.docker.com/engine/install/) para o seu sistema operacional. A instalação geralmente inclui o `docker-compose`.

Para garantir que o Docker foi instalado corretamente, rode os comandos:
```bash
docker --version
docker-compose --version
```
Você deverá ver as versões instaladas.

### 1.2 - Adicionando seu usuário ao grupo do Docker (Opcional, mas recomendado)

Para evitar ter que digitar `sudo` toda vez que usar o Docker, adicione seu usuário ao grupo `docker`:

```bash
sudo usermod -aG docker ${USER}
```

**Importante:** Após rodar este comando, você precisa **fazer logout e login novamente** para que a alteração tenha efeito.

## Passo 2: Baixando e Configurando o CSPMEXA

Agora que os pré-requisitos estão prontos, vamos baixar e configurar a aplicação.

### 2.1 - Clonar o Repositório

```bash
git clone https://github.com/seu-usuario/seu-repositorio.git cspmexa
# NOTA: Substitua a URL acima pela URL correta do repositório.
cd cspmexa
```

### 2.2 - Executar o Script de Inicialização

Nós fornecemos um script para facilitar a configuração e inicialização da aplicação.

Rode o seguinte comando na raiz do projeto:
```bash
bash init.sh
```

O que este script fará:

1.  **Verificará se o Docker está em execução.**
2.  **Criará o arquivo `.env`**: Se o arquivo `.env` não existir, ele será criado a partir do `.env.example`.
3.  **Iniciará o Vault**: O script iniciará o Vault e um serviço de setup que irá:
    *   Criar os segredos iniciais.
    *   Configurar as políticas de segurança.
    *   Gerar credenciais de acesso seguras (AppRole) para cada microsserviço.

### 2.3 - Configurar as Credenciais (Ação Manual Necessária)

Após a etapa anterior, o script irá pausar e exibir uma mensagem importante. **Você precisa configurar as credenciais de acesso ao Vault.**

1.  **Abra um novo terminal** e execute o seguinte comando para ver as credenciais que foram geradas:
    ```bash
    docker-compose logs vault-setup
    ```
2.  Você verá um output similar a este:
    ```
    --------------------------------------------------
    Credenciais AppRole geradas. Adicione ao seu .env:

    # Credenciais para o auth_service
    AUTH_SERVICE_VAULT_ROLE_ID=...
    AUTH_SERVICE_VAULT_SECRET_ID=...

    # Credenciais para o collector_service
    COLLECTOR_SERVICE_VAULT_ROLE_ID=...
    COLLECTOR_SERVICE_VAULT_SECRET_ID=...
    ...
    --------------------------------------------------
    ```
3.  **Copie** estas variáveis e **cole-as** no final do seu arquivo `.env`.
4.  **Volte para o terminal** onde o `init.sh` está pausado e pressione **[Enter]** para continuar.

## Passo 3: Iniciar a Aplicação

Depois de configurar o `.env` e pressionar [Enter], o script `init.sh` iniciará todos os outros serviços da aplicação em modo detached (em segundo plano).

Você pode acompanhar os logs de todos os serviços com o comando:
```bash
docker-compose logs -f
```

A aplicação estará acessível no seu navegador em `http://localhost` ou `http://IP_DO_SEU_SERVIDOR`.

E é isso! Seu sistema CSPMEXA está instalado e pronto para uso.

## Gerenciando os Serviços

*   **Para parar todos os serviços:**
    ```bash
    docker-compose down
    ```
*   **Para iniciar os serviços novamente (após a primeira inicialização):**
    ```bash
    docker-compose up -d app
    ```
