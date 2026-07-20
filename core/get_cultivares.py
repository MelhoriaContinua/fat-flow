import os
import sys
import time
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def _get_data_dir():
    """Diretorio 'data' correto tanto em desenvolvimento quanto no executavel."""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'data')


def _load_env_from_plaintext():
    """Fallback para execucao standalone (python core/get_cultivares.py):
    carrega as variaveis do data/.env em texto puro para o os.environ."""
    env_path = os.path.join(_get_data_dir(), '.env')
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                key = key.strip()
                if key not in os.environ:
                    os.environ[key] = value.strip()
    except FileNotFoundError:
        pass


def _normalize_cultivares_payload(payload):
    """
    Normaliza diferentes formatos de resposta:
    - lista de dicionários
    - dict com chave 'cultivares' ou 'data'
    Retorna sempre uma lista de dicts.
    """
    if payload is None:
        return []

    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        # formatos comuns
        for key in ("cultivares", "data", "items", "resultado"):
            if key in payload and isinstance(payload[key], list):
                return payload[key]
        # às vezes já vem direto como um único registro
        if all(k in payload for k in ("CODIGO", "DESCRICAO")):
            return [payload]

    return []


def fetch_all_cultivares_por_cultura(base_url: str, token: str, culturas_json: dict, pause_sec: float = 0.2) -> pd.DataFrame:
    """
    Percorre todas as culturas e busca suas cultivares no endpoint:
      {base_url}webservice/api/busca/cultivares/{id_cultura}/
    Monta um DataFrame consolidado.
    """
    headers = {"X-Token": token}

    # sessão com retries para ficar resiliente (429/5xx)
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"])
    )
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))

    linhas = []

    culturas = culturas_json.get("culturas", [])
    for c in culturas:
        cultura_id = str(c.get("CODIGO", "")).strip()
        cultura_desc = str(c.get("DESCRICAO", "")).strip()
        if not cultura_id:
            continue

        url_cultivares = f"{base_url}webservice/api/busca/cultivares/{cultura_id}/"
        try:
            resp = session.get(url_cultivares, headers=headers, timeout=30)
            resp.raise_for_status()
            payload = resp.json()
            cultivares = _normalize_cultivares_payload(payload)

            for item in cultivares:
                cultivar_cod = str(item.get("CODIGO", "")).strip()
                cultivar_des = str(item.get("DESCRICAO", "")).strip()
                linhas.append({
                    "CULTURA_CODIGO": cultura_id,
                    "CULTURA_DESCRICAO": cultura_desc,
                    "CULTIVAR_CODIGO": cultivar_cod,
                    "CULTIVAR_DESCRICAO": cultivar_des
                })

            print(f"[OK] Cultura {cultura_id} - {cultura_desc}: {len(cultivares)} cultivares")

        except requests.exceptions.RequestException as e:
            print(f"[ERRO] Cultura {cultura_id} - {cultura_desc}: {e}")

        # pequeno intervalo para evitar rate limit
        time.sleep(pause_sec)

    df = pd.DataFrame(linhas, columns=[
        "CULTURA_CODIGO",
        "CULTURA_DESCRICAO",
        "CULTIVAR_CODIGO",
        "CULTIVAR_DESCRICAO"
    ])

    # garantir string e tratar NaN
    df["CULTIVAR_DESCRICAO"] = df["CULTIVAR_DESCRICAO"].fillna("").astype(str)

    df = df.sort_values(
        by="CULTIVAR_DESCRICAO",
        key=lambda s: s.str.len(),   # ordena pela extensão do texto
        ascending=False,
        kind="stable"
    ).reset_index(drop=True)

    return df


def run_atualizacao(x_token: str = None, url_guia_fase: str = None) -> str:
    """
    Atualiza data/Relacionamento_Culturas_Cultivares.xlsx a partir da API Guia Fase.

    Le as credenciais do ambiente (os.environ) quando nao passadas por parametro,
    de modo a funcionar tanto no app (env ja descriptografado) quanto standalone.
    Retorna o caminho do arquivo gerado.
    """
    x_token = x_token or os.getenv("X-TOKEN")
    url_guia_fase = url_guia_fase or os.getenv("URL_GUIA_FASE")

    # remove aspas eventuais
    if x_token:
        x_token = x_token.strip('"')
    if url_guia_fase:
        url_guia_fase = url_guia_fase.strip('"')

    if not (x_token and url_guia_fase):
        raise RuntimeError(
            "X-TOKEN e/ou URL_GUIA_FASE nao encontrados no ambiente. "
            "Verifique o data/.env ou as credenciais carregadas."
        )

    headers = {"X-Token": x_token}

    # 1) culturas (obrigatorio)
    resp_culturas = requests.get(url_guia_fase + "webservice/api/busca/culturas", headers=headers, timeout=30)
    resp_culturas.raise_for_status()
    json_culturas = resp_culturas.json()

    # 2) safras (opcional)
    json_safras = {}
    try:
        resp_safras = requests.get(url_guia_fase + "webservice/api/busca/safras", headers=headers, timeout=30)
        resp_safras.raise_for_status()
        json_safras = resp_safras.json()
    except requests.exceptions.RequestException as e:
        print(f"[AVISO] Falha ao buscar safras: {e}")

    # 3) relacao cultura x cultivar
    df_relacao = fetch_all_cultivares_por_cultura(url_guia_fase, x_token, json_culturas, pause_sec=0.2)
    df_culturas = pd.DataFrame(json_culturas.get("culturas", []))
    df_safras = pd.DataFrame(json_safras.get("safras", [])) if isinstance(json_safras, dict) else pd.DataFrame()

    output_path = os.path.join(_get_data_dir(), "Relacionamento_Culturas_Cultivares.xlsx")

    mode = "a" if os.path.exists(output_path) else "w"
    writer_kwargs = dict(engine="openpyxl", mode=mode)
    if mode == "a":
        writer_kwargs["if_sheet_exists"] = "replace"

    with pd.ExcelWriter(output_path, **writer_kwargs) as writer:
        df_relacao.to_excel(writer, index=False, sheet_name="Relacao_Culturas_Cultivares")
        if not df_culturas.empty:
            df_culturas.to_excel(writer, index=False, sheet_name="Culturas")
        if not df_safras.empty:
            df_safras.to_excel(writer, index=False, sheet_name="Safras")

    print(f"Arquivo gerado: {output_path}")
    return output_path


if __name__ == "__main__":
    # Execucao standalone: carrega o .env em texto puro antes de rodar.
    _load_env_from_plaintext()
    run_atualizacao()
