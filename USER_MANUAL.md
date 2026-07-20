# Manual de Uso — FatFlow

## Introdução

O FatFlow simplifica a emissão de **Guias de Utilização de Sementes e Mudas (Guia Fase)**. Com ele você baixa notas fiscais, preenche os dados da guia e emite o documento com poucos cliques — além de consultar carregamentos e enviar documentos ao SoftSul.

## Instalação

Basta executar o arquivo `FatFlow.exe`, na pasta principal do programa. Não é necessária nenhuma instalação adicional.

> O `FatFlow.exe` depende das pastas `core`, `data`, `img` e `outputs` que o acompanham. Mantenha todas juntas na mesma pasta.

## Login

Ao abrir o programa, uma tela de login é exibida.

- **Login e senha:** solicite ao departamento de Melhoria Contínua.

## Funcionalidades

A aplicação é organizada em **3 abas**.

### Aba 1 — Check do Carregamento

Consulte as informações de um carregamento. Preencha um dos campos de busca (**Safra**, **Carga Web** ou **número ZHCD**) e clique em **Buscar**. O programa exibe o cabeçalho do carregamento, os itens agrupados por lote e os subtotais (sacas, peso e valor). É uma tela de **consulta** (somente leitura).

### Aba 2 — NF & Guia Fase

Aba principal, dividida em quatro blocos:

1. **Carregar NF Local** — selecione uma NF-e (XML) já baixada na lista e clique em **Carregar**. Os itens preenchem a tabela automaticamente.
2. **Baixar Novas NFs** — cole uma ou mais chaves de 44 dígitos das NF-e e clique em **Baixar NFs**. O programa baixa o XML e o PDF de cada nota. *(Aguarde a inicialização — o botão fica disponível quando o sistema estiver pronto.)*
3. **Dados da Guia** — preencha Natureza da Operação, Grupo de Cultura, Safra e Destinatário. Use o botão **Atualizar Dados Guia Fase** para atualizar as listas quando necessário. O campo **Modo QAS** deve ficar **desmarcado** para emissões reais (ele serve apenas para testes de homologação).
4. **Itens da Guia** — revise/edite os itens (duplo clique para editar; botões para adicionar ou remover). Ao concluir, clique em **Emitir Guia**. O PDF gerado é salvo na pasta `outputs`.

### Aba 3 — Enviar para SoftSul

Informe a **Carga Web**, clique em **Atualizar Lista de PDFs** e marque os documentos que deseja enviar. Para cada PDF, selecione o **Tipo** (por exemplo: nfe, guia-fase, mdfe, cte, mapa, canhoto, roteiro, ckl). Clique em **Enviar para SoftSul** — o resultado aparece na área de **Log de Envio**.

## Temas (aparência)

No rodapé há um menu de **Tema** com três opções:

- **Modo Escuro (Solar)**
- **Modo Escuro (Darkly)** *(padrão)*
- **Modo Claro (Flatly)**

## Resolução de problemas

- **Erro de login:** confira se o login e a senha estão corretos.
- **Erro ao baixar NF-e:** verifique se a chave tem 44 dígitos e se há conexão com a internet. Aguarde a inicialização do sistema antes de baixar.
- **Erro ao emitir a guia:** confira se todos os campos foram preenchidos e se o **Modo QAS** está desmarcado (para emissões reais).
- **Erro ao enviar ao SoftSul:** confirme o número da Carga Web e se os tipos dos documentos foram selecionados.

## Suporte

Em caso de dúvidas ou problemas, entre em contato com a equipe de **Melhoria Contínua**.
