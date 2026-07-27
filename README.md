# Controle de Saude — Alexa Skill

Skill de Alexa que registra medições de glicemia e pressão arterial numa planilha do Google Sheets.

## Estrutura do repositório

```
.
├── lambda/                          # backend da skill
│   ├── lambda_function.py
│   ├── languages/pt-BR.json
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── tests/
└── skill-package/                   # pacote da skill (ASK)
    ├── interactionModels/custom/pt-BR.json
    └── skill.json
```

## Pré-requisitos

- [mise](https://mise.jdx.dev/) (gerencia a versão do Python e o venv)
- Node.js + [ASK CLI](https://developer.amazon.com/en-US/docs/alexa/smapi/quick-start-alexa-skills-kit-command-line-interface.html) (`npm install -g ask-cli`), se for fazer deploy da skill
- Conta AWS (Lambda) e conta de desenvolvedor Amazon (Alexa)
- Service account do Google Cloud com acesso à Sheets + Drive API

## 1. Instalar dependências Python

```bash
mise install          # instala o Python 3.14.6 e cria o .venv
source .venv/bin/activate
pip install -r lambda/requirements.txt
pip install -r lambda/requirements-dev.txt   # para rodar os testes
```

## 2. Configurar a planilha do Google

1. Crie uma planilha com três abas: `Criterios`, `Diabete`, `Pressao`.
   - `Criterios` precisa das colunas `min`, `max`, `orientacao` (usadas para dar orientação com base no valor da glicemia).
   - `Diabete` e `Pressao` são apenas logs (linhas de data/hora/valor).
2. Crie uma service account no Google Cloud, habilite a **Google Sheets API** e a **Google Drive API**, e gere uma chave JSON.
3. Compartilhe a planilha com o e-mail da service account (permissão de Editor).

## 3. Configurar variáveis de ambiente

A lambda lê estas variáveis em tempo de execução (configure no console/CLI da Lambda, ou exporte localmente para testar):

```bash
export SPREADSHEET_ID="<id-da-planilha>"
export GOOGLE_CREDENTIALS='<conteúdo do JSON da service account>'
```

## 4. Rodar os testes

```bash
source .venv/bin/activate
pytest lambda/tests
```

## 5. Deploy

```bash
ask deploy
```

Isso envia o `skill-package/` (modelo de interação + manifesto) e empacota o `lambda/` como código da função Lambda, conforme o `sourceDir` definido em `skill-package/skill.json`.

Depois do deploy, configure `SPREADSHEET_ID` e `GOOGLE_CREDENTIALS` como variáveis de ambiente na função Lambda (console, `aws lambda update-function-configuration`, ou sua ferramenta de IaC).
