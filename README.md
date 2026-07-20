# FatFlow

Aplicação **desktop (Windows)** que automatiza o processo de faturamento de sementes, com foco na emissão da **Guia de Utilização de Sementes e Mudas (Guia Fase)**.

Reúne, em uma única interface, tarefas que antes exigiam acessar vários sistemas manualmente:

- 📥 Baixar notas fiscais (NF-e) do portal **OOBJ**
- 🔎 Consultar carregamentos no **SoftSul**
- 📄 Emitir a **Guia Fase** na API oficial
- 📎 Enviar documentos (PDFs) de volta ao **SoftSul**

A interface é feita em `tkinter` + `ttkbootstrap` e distribuída como um único executável (`FatFlow.exe`) gerado com PyInstaller.

## Interface

O app é organizado em 3 abas:

| Aba | Função |
|-----|--------|
| **Check do Carregamento** | Consulta (somente leitura) de carregamentos no SoftSul. |
| **NF & Guia Fase** | Fluxo principal: baixar/carregar NF-e, preencher dados e emitir a Guia Fase. |
| **Enviar para SoftSul** | Envio de PDFs da pasta `outputs` para uma Carga Web no SoftSul. |

## Começando (desenvolvimento)

```sh
# 1. Instale as dependências
pip install -r requirements.txt

# 2. Configure as credenciais
#    Copie o modelo e preencha os valores reais (sem aspas)
copy .env.example data\.env       # Windows
# cp .env.example data/.env        # Git Bash / Linux

# 3. Gere o arquivo de credenciais criptografado (necessário para rodar)
python core/encrypt_env.py

# 4. Execute o app
python core/app_gui.py
```

> O login da tela inicial usa as variáveis `APP_LOGIN` / `APP_PASSWORD` definidas no `data/.env`.

## Build do executável

```sh
pyinstaller FatFlow.spec
```

O `FatFlow.spec` criptografa o `data/.env` automaticamente e embute as credenciais no executável. O `FatFlow.exe` é gerado na pasta `dist`. Detalhes em [DEVELOPER_MANUAL.md](DEVELOPER_MANUAL.md).

## Estrutura

```
core/    Código-fonte (GUI, scraping, integrações)
data/    Credenciais e planilhas (NÃO versionado)
img/     Ícones e logo
outputs/ NF-e e guias geradas (runtime)
```

## Segurança

As credenciais **nunca** ficam no repositório. Elas vivem apenas no `data/.env` (local, ignorado pelo Git) e são embutidas de forma criptografada no executável durante o build. O único arquivo de configuração versionado é o `.env.example` (modelo, sem segredos).

Consulte a seção **Segurança das credenciais** do [Manual do Desenvolvedor](DEVELOPER_MANUAL.md).

## Documentação

- 📘 [Manual do Usuário](USER_MANUAL.md) — como usar o app no dia a dia.
- 🛠️ [Manual do Desenvolvedor](DEVELOPER_MANUAL.md) — arquitetura, integrações, variáveis de ambiente, build e dívidas técnicas.

## Tecnologias

`Python` · `tkinter` / `ttkbootstrap` · `pandas` / `openpyxl` · `selenium` · `requests` · `lxml` · `cryptography` · `PyInstaller`
