import pandas as pd
import unicodedata

df_zsd144 = pd.read_excel("data\ZSD144.XLSX")
df_cultivares = pd.read_excel("data\Relacionamento_Culturas_Cultivares.xlsx")

def tratamento_cultivar(df, column):
    
    if 'Denominação' in df.columns:
       # Normaliza os caracteres para remover qualquer forma de acentuação ou caracteres não visíveis
        df['Denominação'] = df['Denominação'].apply(lambda x: unicodedata.normalize('NFKD', str(x)).encode('ASCII', 'ignore').decode('ASCII'))
        
        # Agora realiza a substituição de espaços
        df['Denominação'] = df['Denominação'].str.replace(" ","", regex=True)

    # tratamento robusto
    serie = df[column].astype(str)

    # remove tudo depois de "(" se existir
    serie = serie.str.split("(", n=1).str[0]

    # pega só o que vier depois de "SEM", se existir
    serie = serie.str.extract(r"SEM(.*)", expand=False).fillna(serie)

    # limpeza final
    serie = (
        serie.str.strip()                      # remove espaços no início/fim
             .str.replace(" ", "", regex=False)  # remove espaços internos
    )
    
    if 'Marca/Família' in df.columns and 'Denominação' in df.columns:
        df['Marca/Família'] = df['Marca/Família'].fillna(df['Denominação'])  # completa valores NaN
        df['Marca/Família'] = df['Marca/Família'].replace("", pd.NA)         # trata strings vazias
        df['Marca/Família'] = df['Marca/Família'].fillna(df['Denominação'])  # substitui vazios também

    df[column] = serie
    return df


def limpar_zsd144(df):
    df = df.copy()
    df['Lote'] = df['Lote'].fillna("").astype(str).str.strip()
    df = df[df['Lote'] != ""].reset_index(drop=True)
    return df


def obter_codigo_cultivar(df_zsd144, df_cultivares):
    df_zsd144_unico = df_zsd144
    
    df_cult = df_cultivares.copy()
    df_cult = df_cult.sort_values(
        by="CULTIVAR_DESCRICAO", 
        key=lambda col: col.str.len(),   # mede o comprimento da string
        ascending=False                  # do maior para o menor
    )
    
    def encontrar_cultivar(denom):
        linha = 1
        for cultivar in df_cult["CULTIVAR_DESCRICAO"]:
            linha += 1
            if pd.notna(denom) and cultivar in denom:
                return cultivar
        return ""

    # aplica no DataFrame de denominações
    df_zsd144_unico["CULTIVAR_DESCRICAO"] = df_zsd144_unico["Denominação"].apply(encontrar_cultivar)
    
    # faz merge para trazer CULTURA_CODIGO e CULTIVAR_CODIGO
    df_zsd144_unico = df_zsd144_unico.merge(
        df_cult[["CULTIVAR_DESCRICAO", "CULTURA_CODIGO", "CULTIVAR_CODIGO"]],
        on="CULTIVAR_DESCRICAO",
        how="left"
    )
    
    return df_zsd144_unico, df_cult

def orquestrar_dados(df_zsd144, df_cultivares):
    df_cultivares_tratada = tratamento_cultivar(df_cultivares, 'CULTIVAR_DESCRICAO')
    
    df_zsd144_tratada = tratamento_cultivar(df_zsd144, 'Marca/Família')
    df_zsd144_tratada = limpar_zsd144(df_zsd144)
    
    return df_zsd144_tratada, df_cultivares_tratada

df_zsd144, df_cultivares = orquestrar_dados(df_zsd144, df_cultivares)

df_zsd144_tratada, df_cultivares_tratada = obter_codigo_cultivar(df_zsd144, df_cultivares)

df_zsd144.to_excel("ZSD144_CódigoCultivares.xlsx")

print(df_zsd144['Marca/Família'])
print(df_cultivares['CULTIVAR_DESCRICAO'])
