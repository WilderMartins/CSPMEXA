# Guia de Instalação Simplificado do CSPMEXA (via Docker Compose)

**Nota:** Este guia descreve o método de instalação mais simples, usando Docker Compose. É ideal para ambientes de desenvolvimento, testes ou implantações de pequena escala em uma única máquina. Para implantações de produção escaláveis e de alta disponibilidade, consulte o nosso **[Guia de Implantação em Kubernetes](./kubernetes/README.md)**.

---

Bem-vindo ao guia de instalação do CSPMEXA! Este guia foi projetado para ser o mais simples possível, permitindo que qualquer pessoa, mesmo sem conhecimento técnico profundo, possa instalar e configurar o sistema.

## Passo 1: Pré-requisitos

Antes de começar, você precisa de um servidor (ou máquina local) com um sistema operacional Linux e o Docker instalado.

### 1.1 - Instalando o Docker

Se você ainda não tem o Docker, pode instalá-lo seguindo o guia oficial para o seu sistema operacional. Para **Ubuntu/Debian**, você pode usar os seguintes comandos:

```bash
# Atualiza a lista de pacotes e instala dependências
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

# Adiciona a chave GPG oficial do Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Configura o repositório do Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

# Instala o Docker Engine, CLI, Containerd e o plugin do Docker Compose
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 1.2 - Permissões do Docker (Recomendado)

Para evitar ter que digitar `sudo` toda vez que usar o Docker, adicione seu usuário ao grupo `docker`:

```bash
sudo usermod -aG docker ${USER}
```

**Importante:** Após rodar este comando, você precisa **fazer logout e login novamente** no servidor para que a alteração tenha efeito.

## Passo 2: Baixando e Iniciando o Instalador

Com os pré-requisitos atendidos, o resto do processo é feito pelo nosso assistente de instalação web.

```bash
# 1. Clone o repositório do projeto
git clone https://github.com/CSPFatec/cspmexa.git
cd cspmexa

# 2. Inicie o assistente de instalação
docker compose up --build installer
```

Este comando irá construir e iniciar apenas o serviço de instalação.

## Passo 3: Usando o Assistente de Instalação Web

Após o comando terminar, abra seu navegador de internet e acesse o seguinte endereço:

`http://SEU_ENDERECO_DE_IP:8080`

(Substitua `SEU_ENDERECO_DE_IP` pelo endereço de IP do seu servidor).

O assistente irá guiá-lo em três etapas:

### Etapa 1: Verificação de Pré-requisitos
O assistente verificará automaticamente se o Docker está instalado, em execução e se você tem as permissões corretas. Se houver algum problema, ele fornecerá instruções sobre como corrigi-lo.

### Etapa 2: Configuração do Ambiente
Você será apresentado a um formulário para configurar todos os aspectos do seu ambiente, incluindo:
-   Configurações de banco de dados.
-   Credenciais para o Google OAuth.
-   (Opcional) Credenciais para os provedores de nuvem que você deseja monitorar (AWS, Azure, etc.).

O assistente irá gerar automaticamente todos os arquivos de configuração necessários (`.env`) e as chaves de segurança.

### Etapa 3: Acompanhamento da Instalação
Após enviar a configuração, você será redirecionado para uma página de status detalhada. Nesta página, você poderá ver o status de cada serviço individualmente (ex: "iniciando", "em execução", "com falha") e visualizar os logs de cada serviço para diagnosticar problemas facilmente.

Quando todos os serviços essenciais estiverem em execução, a instalação estará concluída!

E é isso! Seu sistema CSPMEXA estará instalado e pronto para uso.
