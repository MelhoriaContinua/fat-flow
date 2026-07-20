# Documentação para Desenvolvedor — FatFlow

## 1. Visão geral

O FatFlow é uma aplicação **desktop (Windows)** que automatiza o processo de faturamento de sementes, com foco na emissão da **Guia de Utilização de Sementes e Mudas (Guia Fase)**. Ele reúne, em uma única interface, tarefas que antes exigiam acessar vários sistemas manualmente:

- baixar notas fiscais (NF-e) do portal OOBJ;
- consultar carregamentos no SoftSul;
- emitir a Guia Fase na API oficial;
- anexar documentos (PDFs) de volta ao SoftSul.

A interface é feita em `tkinter` com o tema `ttkbootstrap`, e é distribuída como um único executável (`FatFlow.exe`) gerado com PyInstaller.

## 2. Arquitetura

Arquitetura **monolítica**: a GUI concentra o fluxo e chama módulos auxiliares. A interface é organizada em **3 abas** (`ttk.Notebook`):

| Aba | Nome na interface | O que faz |
|-----|-------------------|-----------|
| 1 | **Check do Carregamento** | Consulta (somente leitura) um carregamento no SoftSul por Safra, Carga Web ou nº ZHCD, exibindo itens e subtotais. |
| 2 | **NF & Guia Fase** | Fluxo principal: carregar/baixar NF-e, preencher dados e **emitir a Guia Fase**. |
| 3 | **Enviar para SoftSul** | Seleciona PDFs da pasta `outputs` e os envia (base64) para uma Carga Web no SoftSul. |

### Módulos (`core/`)

| Arquivo | Responsabilidade |
|---------|------------------|
| `app_gui.py` | Toda a interface gráfica (3 abas), login, temas e orquestração do fluxo. |
| `scrap_oobj.py` | Classe `OobjScraper`: automação web (Selenium/Chrome) do portal OOBJ para baixar XML + PDF das NF-e. |
| `get_cultivares.py` | Atualiza a base de cultivares consultando a API Guia Fase. Executado **em processo** (`run_atualizacao()`) pelo botão "Atualizar Dados Guia Fase". |
| `encrypt_env.py` | Utilitário de **build**: criptografa `data/.env` → `data/.env.encrypted` e gera `data/fatflow.key`. |
| `data_processing.py` | Script **standalone** (não importado pela GUI) que cruza `ZSD144.XLSX` com a base de cultivares. Uso pontual/manual. |

## 3. Estrutura de pastas e arquivos

```
FatFlow/
├── core/                     # Código-fonte
│   ├── app_gui.py            # GUI e fluxo principal
│   ├── scrap_oobj.py         # Automação Selenium (OOBJ)
│   ├── get_cultivares.py     # Atualização da base de cultivares (API)
│   ├── encrypt_env.py        # Criptografia do .env (usado no build)
│   └── data_processing.py    # Script auxiliar (standalone)
├── data/                     # Dados e credenciais — NÃO versionado (ver seção 6)
│   ├── .env                  # Credenciais em texto puro (local)
│   ├── .env.encrypted        # Credenciais criptografadas (gerado)
│   ├── fatflow.key           # Chave Fernet (gerada no build)
│   ├── Relacionamento_Culturas_Cultivares.xlsx
│   └── ZSD144.XLSX
├── img/                      # Ícones e logo (icon_black/white.png, icon_desktop.ico/png, logo.png)
├── outputs/                  # NF-e (XML/PDF) baixadas e guias geradas (runtime)
├── .env.example              # Modelo de credenciais (sem segredos) — versionado
├── .gitignore
├── FatFlow.spec              # Configuração do PyInstaller
├── requirements.txt
├── USER_MANUAL.md
└── DEVELOPER_MANUAL.md       # Este arquivo
```

## 4. Integrações externas

| Integração | Onde | O que faz |
|------------|------|-----------|
| **OOBJ** (`nfe.araguaia.com.br`) | `scrap_oobj.py` | Login e download de XML + PDF das NF-e via Selenium/ChromeDriver (headless). |
| **API Guia Fase** (`162.214.76.169`) | `app_gui.py`, `get_cultivares.py` | Emissão de guias (`/webservice/api/guia/regime/emitir`), download do PDF e busca de culturas/cultivares/safras. |
| **API SoftSul** (`vig.softsul.agr.br`) | `app_gui.py` | Consulta de carregamentos e envio de PDFs (base64) para a Carga Web. |

> **Nota:** existe também `OOBJ REQUEST/download_nf.py`, uma abordagem alternativa de download via API (com `.token_cache.json`). Ela **não** é usada pela GUI atual (que importa apenas `scrap_oobj`).

## 5. Variáveis de ambiente

Todas as credenciais ficam no `data/.env` (formato `CHAVE = valor`, **sem aspas**):

| Variável | Uso |
|----------|-----|
| `FIXED_KEY` | Chave Fernet que (de)criptografa o `.env.encrypted`. |
| `APP_LOGIN` / `APP_PASSWORD` | Login da tela inicial do app. |
| `LOGIN_OOBJ` / `SENHA_OOBJ` | Credenciais do portal OOBJ (usadas pelo Selenium). |
| `X-TOKEN` | Token da API Guia Fase — ambiente **QAS/homologação**. |
| `X-TOKEN-PROD` | Token da API Guia Fase — ambiente de **produção**. |
| `URL_GUIA_FASE` | URL base da API Guia Fase (usada por `get_cultivares.py`). |
| `USERNAME_SS` / `PASS_SS` | Credenciais da API SoftSul (envio de arquivos). |
| `FATFLOW_KEY` *(opcional, do SO)* | Sobrescreve a `FIXED_KEY` via variável de ambiente do sistema. Não fica no `.env`. |

## 6. Segurança das credenciais

- **Fonte única:** `data/.env` (texto puro) — apenas local, nunca versionado. Contém todas as credenciais **e** a `FIXED_KEY`.
- **Runtime:** o app lê `data/.env.encrypted`. A chave é resolvida por `_get_fixed_key()` nesta ordem: variável `FATFLOW_KEY` → arquivo `data/fatflow.key` (embutido no `.exe`) → linha `FIXED_KEY` do `data/.env`. **Nenhuma chave ou credencial fica no código-fonte.**
- **Repositório:** o `.gitignore` bloqueia `.env`, `.env.encrypted`, `.env_backup`, `fatflow.key` e toda a pasta `data/`. Apenas o `.env.example` (modelo sem segredos) é versionado.
- **Atenção:** no executável distribuído, a `fatflow.key` é embutida junto do `.env.encrypted` — quem extrair o `.exe` consegue descriptografar. A criptografia protege o **repositório**, não o binário. Para reforçar a produção, defina a `FATFLOW_KEY` como variável de ambiente na máquina do usuário (assim a chave não precisa ser embutida) e **rotacione** credenciais já expostas.

## 7. Fluxo de dados por funcionalidade

**Emitir Guia Fase (aba "NF & Guia Fase"):**
1. O usuário carrega uma NF-e local (XML da pasta `outputs`) ou informa chaves de 44 dígitos para baixar via OOBJ (`scrap_oobj.py`).
2. O XML é lido e os itens preenchem a tabela; planilhas de `data/` populam os campos de seleção (culturas, safras, destinatários).
3. O checkbox **"Modo QAS"** define o ambiente:
   - **Produção** (padrão): monta o payload a partir dos dados reais da NF-e/itens e usa o token `X-TOKEN-PROD`.
   - **QAS/homologação**: usa um payload de teste fixo e o token `X-TOKEN`.
4. A API Guia Fase retorna o PDF, salvo em `outputs/`.

**Check do Carregamento (aba 1):** consulta a API SoftSul e exibe cabeçalho, itens por lote e subtotais (somente leitura).

**Enviar para SoftSul (aba 3):** seleciona PDFs de `outputs`, define o "Tipo" de cada um e envia em base64 para a Carga Web informada.

**Atualizar base de cultivares:** o botão "Atualizar Dados Guia Fase" chama `get_cultivares.run_atualizacao()` (em processo, usando as credenciais já carregadas no ambiente), que consulta a API Guia Fase e regrava `Relacionamento_Culturas_Cultivares.xlsx`.

## 8. Tecnologias

| Biblioteca | Uso |
|------------|-----|
| `ttkbootstrap` / `tkinter` | Interface gráfica e temas. |
| `pandas` / `openpyxl` | Leitura e manipulação das planilhas Excel. |
| `selenium` / `webdriver_manager` | Automação do navegador (download de NF-e no OOBJ). |
| `requests` | Chamadas HTTP às APIs Guia Fase e SoftSul. |
| `lxml` | Parsing de XML de NF-e. |
| `Pillow` | Manipulação/exibição de imagens na interface. |
| `cryptography` | Criptografia Fernet do arquivo de credenciais. |
| `python-dotenv` | Suporte a variáveis de ambiente. |
| `pyinstaller` | Geração do executável. |

## 9. Como rodar o projeto localmente

1. **Instale as dependências:**
   ```sh
   pip install -r requirements.txt
   ```
2. **Configure as credenciais:**
   - Copie `.env.example` para `data/.env` e preencha os valores (sem aspas):
     ```
     FIXED_KEY = chave-fernet   # gere: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
     APP_LOGIN = login-do-app
     APP_PASSWORD = senha-do-app
     URL_GUIA_FASE = url-da-api-guia-fase
     X-TOKEN = token-guia-fase-qas
     X-TOKEN-PROD = token-guia-fase-producao
     LOGIN_OOBJ = login-oobj
     SENHA_OOBJ = senha-oobj
     USERNAME_SS = usuario-softsul
     PASS_SS = senha-softsul
     ```
   - `data/.env` **não é versionado** — fica apenas na sua máquina.
   - Gere o arquivo criptografado (necessário para o app rodar):
     ```sh
     python core/encrypt_env.py
     ```
     Isso cria `data/.env.encrypted` e `data/fatflow.key`.
3. **Execute a aplicação:**
   ```sh
   python core/app_gui.py
   ```
4. **Login:** use os valores de `APP_LOGIN` / `APP_PASSWORD` definidos no `data/.env`.

## 10. Distribuição (build do executável)

1. Garanta que `data/.env` existe e está preenchido (inclusive `FIXED_KEY`).
2. Gere o executável:
   ```sh
   pyinstaller FatFlow.spec
   ```
   O `FatFlow.spec` executa a criptografia automaticamente: gera `data/.env.encrypted` e `data/fatflow.key` a partir do `data/.env` e os **embute no executável**. O `.env` em texto puro **nunca** é empacotado. Se o `data/.env` não existir (ou não tiver `FIXED_KEY`), o build falha com erro explícito.
3. O `FatFlow.exe` é criado na pasta `dist`.
4. Distribua o `FatFlow.exe` junto das pastas `core`, `data`, `img` e `outputs` (o app depende delas em runtime).

## 11. Testes

O projeto **não possui suíte de testes automatizados**. A validação é feita manualmente a cada alteração.

## 12. Pontos de atenção / dívidas técnicas

- **`get_cultivares.py`** agora roda **em processo** (`run_atualizacao()`), lendo `X-TOKEN`/`URL_GUIA_FASE` do ambiente já descriptografado — funciona no `.exe`. Em execução standalone (`python core/get_cultivares.py`), ele carrega o `data/.env` em texto puro via fallback.
- **`data_processing.py`** é um script standalone com caminhos relativos frágeis (dependentes do diretório atual) e não é chamado pela GUI.
- Há trechos de **código legado** em `app_gui.py` (ex.: `enviar_softsul`, `link_files_softsul`) com valores de NF hardcoded que não estão ligados à interface atual.
- O **payload do "Modo QAS"** é fixo (dados de teste), servindo apenas para validação em homologação.
