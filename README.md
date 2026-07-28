# Controle de Saúde — Alexa Skill

Skill de Alexa que registra medições de glicemia (diabete) e pressão arterial numa planilha do Google Sheets, para compartilhar com o médico depois.

## Estrutura do repositório

```
.
├── lambda/                          # backend da skill
│   ├── lambda_function.py
│   ├── languages/pt-BR.json
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── config.py.example            # modelo de config local (não versionado)
│   └── tests/
└── skill-package/                   # pacote da skill (ASK)
    ├── interactionModels/custom/pt-BR.json
    └── skill.json
```

## Pré-requisitos

- [mise](https://mise.jdx.dev/) (gerencia a versão do Python e o venv)
- Conta de desenvolvedor Amazon (Alexa) — https://developer.amazon.com
- Conta AWS (console) — https://console.aws.amazon.com
- Conta Google Cloud (para a service account que acessa o Sheets)

Todo o setup abaixo é feito pelo **console** (Alexa Developer Console + console AWS), sem CLI.

---

## 1. Instalar dependências Python

```bash
mise install          # instala o Python 3.14.6 e cria o .venv
source .venv/bin/activate
pip install -r lambda/requirements.txt
pip install -r lambda/requirements-dev.txt   # para rodar os testes
```

---

## 2. Criar credenciais do lado do Google

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/) e crie um projeto novo (ou use um existente).
2. Em **APIs e serviços → Biblioteca**, habilite:
   - **Google Sheets API**
   - **Google Drive API**
3. Em **APIs e serviços → Credenciais → Criar credenciais → Conta de serviço**:
   - Dê um nome (ex: `controle-saude-skill`).
   - Não precisa conceder papéis do projeto (o acesso à planilha é dado por compartilhamento direto, no passo 4).
   - Conclua a criação da conta de serviço.
4. Abra a conta de serviço criada → aba **Chaves → Adicionar chave → Criar nova chave → JSON**. Isso baixa um arquivo `.json` — guarde com cuidado, ele não é reemitido.

O conteúdo desse JSON é o valor de `GOOGLE_CREDENTIALS` usado pela lambda.

---

## 3. Criar e configurar a planilha

1. Crie uma planilha no Google Sheets com três abas: `Diabete`, `Pressao`, `Criterios`.
2. **`Diabete`** e **`Pressao`** são apenas logs — a skill só faz `append_row`, não precisam de cabeçalho fixo (mas ajuda ter `data | hora | valor` e `data | hora | sistolica | diastolica` na primeira linha).
3. **`Criterios`** precisa das colunas `min`, `max`, `orientacao` (nomes exatos, primeira linha = cabeçalho). É a tabela de dose de insulina regular que o médico prescreveu, consultada após cada registro de glicemia. Exemplo:

   | min | max | orientacao |
   |-----|-----|------------|
   | 201 | 250 | Aplicar 2 unidades de insulina regular |
   | 251 | 300 | Aplicar 3 unidades de insulina regular |
   | 301 | 350 | Aplicar 4 unidades de insulina regular |
   | 351 | 400 | Aplicar 5 unidades de insulina regular |
   | 401 | 9999 | Aplicar 6 unidades de insulina regular |

   Valores fora de qualquer faixa (ex: ≤200) fazem a skill só confirmar o número, sem orientação. Ajuste as faixas/doses conforme prescrição médica atual.

4. Compartilhe a planilha com o `client_email` que está dentro do JSON da service account (passo 2.4), com permissão de **Editor**.
5. Copie o ID da planilha (o trecho da URL entre `/d/` e `/edit`) — é o `SPREADSHEET_ID`.

---

## 4. Configurar credenciais (local e produção)

```bash
cp lambda/config.py.example lambda/config.py
```

Edite `lambda/config.py` e preencha `SPREADSHEET_ID` e `GOOGLE_CREDENTIALS` com os valores dos passos 2 e 3. Esse arquivo está no `.gitignore` — nunca commitar no git.

Esse mesmo `config.py` (com as credenciais reais) é usado tanto pra rodar os testes localmente quanto pra deploy (passo 7) — o `lambda_function.py` tenta importar `config` primeiro e só cai pras variáveis de ambiente `SPREADSHEET_ID`/`GOOGLE_CREDENTIALS` se o import falhar.

---

## 5. Rodar os testes

```bash
source .venv/bin/activate
pytest lambda/tests
```

---

## 6. Empacotar o projeto pra importar

O `skill-package/skill.json` já aponta `sourceDir: "lambda"` — esse é o formato que o **Import Skill** do Alexa Developer Console espera (mesma estrutura de projeto do ASK CLI, sem precisar do CLI).

Na raiz do projeto, com `lambda/config.py` já preenchido (passo 4) e as dependências instaladas dentro de `lambda/` (pra irem junto no zip, já que a Lambda não roda `pip install`):

```bash
pip install -r lambda/requirements.txt -t lambda/
```

Depois zipe o conteúdo da raiz do projeto (`skill-package/` e `lambda/` devem ficar na raiz do zip, não dentro de uma subpasta):

```bash
zip -r ../controle-de-saude.zip skill-package lambda -x "lambda/tests/*" "lambda/__pycache__/*" "lambda/.pytest_cache/*"
```

---

## 7. Importar a skill (cria skill + Lambda juntas)

1. Acesse o [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask) → na lista de skills, use a opção **Import Skill**.
2. Faça upload do `controle-de-saude.zip` gerado no passo 6.
3. O console lê o `skill-package/skill.json` e o `skill-package/interactionModels`, cria a skill (nome, invocation name `diario de saude`, intents `RegistrarGlicemia`/`RegistrarPressao`), **e também provisiona a função Lambda automaticamente** a partir de `lambda/` — sem precisar abrir o console AWS Lambda separadamente.
4. Aguarde o import terminar e o modelo de interação ser construído (Build Model).

Como as credenciais já foram embutidas em `lambda/config.py` (passo 4) antes de zipar, não é preciso configurar variáveis de ambiente depois do import — a Lambda já sobe com `SPREADSHEET_ID`/`GOOGLE_CREDENTIALS` resolvidos via `config.py`.

Pra atualizar o código depois de uma mudança, repita os passos 6 e 7 (re-importar/re-fazer upload do zip atualizado na mesma skill).

---

## 8. Testar

- No [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask), abra a skill → aba **Test**, habilite testes em modo "Development" e use o simulador com frases como:
  - "abrir diário de saúde"
  - "registrar diabete 220" → deve responder com a orientação de insulina da aba `Criterios`
  - "registrar pressão 12 por 8"
- Ou em um dispositivo Alexa vinculado à mesma conta de desenvolvedor: "Alexa, abrir diário de saúde".
- Confira os logs em CloudWatch (Lambda → Monitor → Ver logs no CloudWatch) se algo não responder como esperado — a skill loga cada request/response e erros não tratados.

---

## Referência rápida das intents

| Intent | Slots | Exemplo de frase |
|---|---|---|
| `RegistrarGlicemia` | `valor` (número) | "registrar diabete 220" |
| `RegistrarPressao` | `sistolica`, `diastolica` (números) | "registrar pressão 12 por 8" |

Frases completas de treino: `skill-package/interactionModels/custom/pt-BR.json`.
