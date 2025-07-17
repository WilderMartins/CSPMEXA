# Guia de Instalação Simplificado do CSPMEXA (via Docker Compose)

**Nota:** Este guia descreve o método de instalação mais simples, usando Docker Compose. É ideal para ambientes de desenvolvimento, testes ou implantações de pequena escala em uma única máquina. Para implantações de produção escaláveis e de alta disponibilidade, consulte o nosso **[Guia de Implantação em Kubernetes](./kubernetes/README.md)**.

---

Bem-vindo ao guia de instalação do CSPMEXA! Este guia foi projetado para ser o mais simples possível, permitindo que qualquer pessoa, mesmo sem conhecimento técnico profundo, possa instalar e configurar o sistema.

## Passo 1: Preparando o Servidor

Antes de começar, você precisa de um servidor (ou máquina local) com um sistema operacional Linux. Os comandos abaixo são para **Ubuntu/Debian**. Se você usa outro sistema, os comandos podem variar um pouco.

### 1.1 - Instalando o Docker

O Docker é a tecnologia que usamos para rodar o CSPMEXA de forma isolada e segura. Para instalá-lo, abra o terminal do seu servidor e copie e cole os comandos abaixo, um de cada vez.

```bash
# Atualiza a lista de pacotes do seu servidor
sudo apt-get update

# Instala pacotes necessários para permitir que o 'apt' use um repositório sobre HTTPS
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

# Atualiza a lista de pacotes novamente, agora com o Docker
sudo apt-get update

# Instala o Docker Engine, CLI, Containerd e o plugin do Docker Compose
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Para garantir que o Docker foi instalado corretamente, rode o comando:
```bash
sudo docker --version
```
Você deverá ver a versão do Docker que foi instalada.

### 1.2 - Adicionando seu usuário ao grupo do Docker (Opcional, mas recomendado)

Para evitar ter que digitar `sudo` toda vez que usar o Docker, adicione seu usuário ao grupo `docker`:

```bash
sudo usermod -aG docker ${USER}
```

**Importante:** Após rodar este comando, você precisa **fazer logout e login novamente** no servidor para que a alteração tenha efeito.

## Passo 2: Baixando o CSPMEXA

Agora que o Docker está pronto, vamos baixar o código do CSPMEXA.

```bash
# Clone o repositório do projeto para o seu servidor
git clone https://github.com/seu-usuario/seu-repositorio.git cspmexa
# NOTA: Substitua a URL acima pela URL correta do repositório do projeto.

# Entre na pasta do projeto
cd cspmexa
```

## Passo 3: Iniciando o Assistente de Instalação

A parte complicada já passou! Agora, vamos usar nosso assistente de instalação para configurar tudo de forma fácil e rápida.

Rode o seguinte comando para iniciar o assistente:

```bash
# Este comando irá construir e iniciar o serviço de instalação.
# Por padrão, apenas o assistente será iniciado.
# Pode levar alguns minutos na primeira vez.
# É recomendado executar este comando com sudo para evitar problemas de permissão com o Docker.
sudo docker compose up --build
```

Após o comando terminar, abra seu navegador de internet e acesse o seguinte endereço:

`http://SEU_ENDERECO_DE_IP:8080`

**Nota sobre permissões:** Se você encontrar erros de "permission denied" ao executar o comando `docker compose`, pode ser necessário adicionar seu usuário ao grupo do Docker. Você pode fazer isso com o seguinte comando:

```bash
sudo usermod -aG docker ${USER}
```

Lembre-se de fazer logout e login novamente para que as alterações entrem em vigor. Se o problema persistir, executar o comando com `sudo` deve resolver o problema.

(Substitua `SEU_ENDERECO_DE_IP` pelo endereço de IP do seu servidor).

Você será recebido pelo nosso assistente de instalação passo a passo. Siga as instruções na tela para:
1.  Configurar o banco de dados.
2.  Definir as configurações gerais do sistema.
3.  (Opcional) Adicionar credenciais para seus provedores de nuvem.

O assistente irá gerar todas as chaves e arquivos de configuração necessários automaticamente. Ao final do processo, ele irá iniciar todos os serviços do CSPMEXA para você.

E é isso! Seu sistema CSPMEXA estará instalado e pronto para uso.
