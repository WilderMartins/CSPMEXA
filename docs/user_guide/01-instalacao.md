# Guia Rápido de Instalação

Bem-vindo ao CSPMEXA! Este guia irá ajudá-lo a instalar a aplicação em sua máquina local ou em um servidor. O processo usa Docker, então você não precisa se preocupar em instalar cada parte da aplicação separadamente.

## O que você vai precisar?

*   Um computador ou servidor com **Linux** ou **macOS**.
*   **Docker** e **Docker Compose** instalados.
*   **Git** instalado.

Se você não tiver essas ferramentas, peça ajuda à sua equipe de TI ou siga os guias oficiais de instalação para cada uma delas.

## Passo 1: Baixar o Código

Abra o seu terminal e execute os seguintes comandos para baixar o código da aplicação:

```bash
git clone https://github.com/seu-usuario/cspmexa.git
cd cspmexa
```
*(Substitua a URL pelo endereço correto do repositório do seu projeto)*

## Passo 2: Iniciar o Assistente de Instalação

Nós criamos um assistente para tornar a instalação o mais simples possível. Para iniciá-lo, execute o seguinte comando no seu terminal, dentro da pasta `cspmexa`:

```bash
docker compose up --build
```

Este comando irá construir e iniciar o assistente de instalação. Pode levar alguns minutos na primeira vez.

## Passo 3: Configurar a Aplicação no Navegador

Após o comando terminar, abra o seu navegador de internet (como Chrome ou Firefox) e acesse o seguinte endereço:

`http://localhost:8080`

Se você estiver instalando em um servidor, substitua `localhost` pelo endereço de IP do servidor.

Você será recebido por uma tela de configuração. Preencha os campos conforme necessário. Para a maioria dos casos, os valores padrão são suficientes. O campo mais importante é o de **Credenciais do Google OAuth**, que você precisará obter no Google Cloud Console para permitir o login na plataforma.

## Passo 4: Concluir a Instalação

Após preencher o formulário, clique em **"Iniciar Instalação"**. O assistente irá:

1.  Gerar todos os arquivos de configuração e chaves de segurança necessários.
2.  Iniciar todos os serviços da aplicação em segundo plano.
3.  Configurar o banco de dados.

Ao final, você será redirecionado para uma página de sucesso com o link para acessar a aplicação.

É isso! A sua instância do CSPMEXA está pronta para ser usada.
