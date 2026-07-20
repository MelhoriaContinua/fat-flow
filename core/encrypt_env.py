import os
from cryptography.fernet import Fernet

# --- Configuration ---
ENV_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
ENV_FILE = os.path.join(ENV_DIR, '.env')
ENCRYPTED_ENV_FILE = os.path.join(ENV_DIR, '.env.encrypted')
KEY_FILE = os.path.join(ENV_DIR, 'fatflow.key')

# Nome da variavel que guarda a chave Fernet dentro do data/.env.
KEY_VAR = 'FIXED_KEY'


def _read_fixed_key():
    """Le a chave Fernet (FIXED_KEY) diretamente do data/.env."""
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith(KEY_VAR) and '=' in line:
                value = line.split('=', 1)[1].strip()
                if value:
                    return value
    raise ValueError(
        f"A variavel {KEY_VAR} nao foi encontrada no {ENV_FILE}. "
        f"Adicione a chave Fernet (use o .env.example como modelo)."
    )


def encrypt_env_file():
    """
    Criptografa os valores do data/.env e salva em data/.env.encrypted.

    - A chave (FIXED_KEY) NAO e incluida no arquivo criptografado (seria circular).
    - A chave e gravada em data/fatflow.key para ser embutida no executavel pelo build.
    """
    if not os.path.exists(ENV_FILE):
        raise FileNotFoundError(
            f"Arquivo de credenciais nao encontrado: {ENV_FILE}\n"
            f"Crie o data/.env (use o .env.example como modelo) antes de gerar o build."
        )

    try:
        fixed_key = _read_fixed_key()
        fernet = Fernet(fixed_key.encode('utf-8'))

        with open(ENV_FILE, 'r', encoding='utf-8') as f_in, \
                open(ENCRYPTED_ENV_FILE, 'w', encoding='utf-8') as f_out:
            for line in f_in:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    f_out.write(line + '\n')
                    continue

                key_part, value_part = line.split('=', 1)

                # A chave nao entra no arquivo criptografado.
                if key_part.strip() == KEY_VAR:
                    continue

                encrypted_value = fernet.encrypt(value_part.encode('utf-8')).decode('utf-8')
                f_out.write(f"{key_part}={encrypted_value}\n")

        # Grava a chave para ser embutida no executavel (bundle do PyInstaller).
        with open(KEY_FILE, 'w', encoding='utf-8') as f_key:
            f_key.write(fixed_key)

        print("Credenciais criptografadas com sucesso!")
        print(f"Arquivo gerado em: {ENCRYPTED_ENV_FILE}")
        print(f"Chave gravada em:  {KEY_FILE}")
        print("\n---")
        print("O data/.env (texto puro) e a chave permanecem apenas nesta maquina e NAO sao versionados.")
        print("O .env.encrypted e o fatflow.key sao embutidos no executavel pelo build (pyinstaller FatFlow.spec).")

    except Exception as e:
        raise Exception(f"Falha ao criptografar o .env: {e}")


if __name__ == "__main__":
    print("Iniciando criptografia do arquivo .env...\n")
    encrypt_env_file()
