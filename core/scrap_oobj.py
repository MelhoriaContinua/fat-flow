import os
import sys
import time
import zipfile
import glob
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import uuid
import base64
import hashlib
from cryptography.fernet import Fernet
from selenium.webdriver.common.keys import Keys

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def _get_fixed_key():
    """Obtem a chave Fernet do .env.encrypted, sem deixa-la no codigo-fonte.

    Ordem de busca: variavel de ambiente do SO (FATFLOW_KEY) -> arquivo
    data/fatflow.key (embutido no executavel no build) -> linha FIXED_KEY do
    data/.env (ambiente de desenvolvimento).
    """
    env_key = os.environ.get("FATFLOW_KEY")
    if env_key:
        return env_key.strip().encode('utf-8')

    candidates = []
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        candidates.append(os.path.join(meipass, 'data'))
    candidates.append(os.path.join(get_base_path(), 'data'))

    for base in candidates:
        key_file = os.path.join(base, 'fatflow.key')
        if os.path.exists(key_file):
            with open(key_file, 'r', encoding='utf-8') as f:
                value = f.read().strip()
            if value:
                return value.encode('utf-8')

    for base in candidates:
        env_file = os.path.join(base, '.env')
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('FIXED_KEY') and '=' in line:
                        value = line.split('=', 1)[1].strip()
                        if value:
                            return value.encode('utf-8')

    raise RuntimeError(
        "Chave de criptografia (FIXED_KEY) nao encontrada. Defina FIXED_KEY no "
        "data/.env (dev), a variavel de ambiente FATFLOW_KEY, ou gere o build."
    )


def _find_encrypted_env():
    """Procura o .env.encrypted dentro do exe (_MEIPASS) ou ao lado dele / no projeto (dev)."""
    candidates = []
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        candidates.append(os.path.join(meipass, 'data', '.env.encrypted'))
    candidates.append(os.path.join(get_base_path(), 'data', '.env.encrypted'))
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        "Arquivo .env.encrypted nao encontrado. Procurado em:\n  - " + "\n  - ".join(candidates)
    )


def decrypt_and_load_env():
    """
    Decrypts the .env.encrypted file and loads the variables into the environment.
    """
    encrypted_env_file = _find_encrypted_env()

    try:
        fernet = Fernet(_get_fixed_key())

        with open(encrypted_env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue

                key_part, encrypted_value = line.split('=', 1)
                
                decrypted_value = fernet.decrypt(encrypted_value.encode('utf-8')).decode('utf-8')
                
                os.environ[key_part.strip()] = decrypted_value.strip()

    except Exception as e:
        raise Exception(f"An error occurred during decryption of the .env file: {e}")

class OobjScraper:
    def __init__(self, app=None, download_path="outputs", headless=True):
        self.app = app
        self.download_path = os.path.abspath(os.path.join(get_base_path(), download_path))
        self.driver = self._setup_driver(headless)
        self.wait = WebDriverWait(self.driver, 15)
        self.is_ready = False
        self._login()

    def prepare_for_downloads(self):
        """Navega para a página de busca e deixa o scraper pronto."""
        print("Navegando para a página de emissão de NFe...")
        url_busca = "http://nfe.araguaia.com.br/monitor/#!/emissao/nfe"
        self.driver.get(url_busca)
        # Aguarda um elemento conhecido na página para garantir que ela carregou
        self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='inputchaveAcessoPesqSimpl']")))
        time.sleep(0.5)

        # Clica no botão do calendário pelo ID (mais confiável)
        self.wait.until(EC.element_to_be_clickable(
            (By.ID, "buttonAbrirCalendario")
        )).click()
        time.sleep(0.3)
        campo = self.wait.until(EC.presence_of_element_located((By.ID, "dataEmissaoPesqSimpl")))

        # Clica no botão "Limpar" que aparece no datepicker
        self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[normalize-space()='Limpar']")
        )).click()
        time.sleep(0.2)

        # Dispara eventos para o Angular reconhecer a mudança
        self.driver.execute_script("""
            var el = arguments[0];
            el.value = '';
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        """, campo)

        # #Selecioa o período de 30 dias
        # self.wait.until(EC.element_to_be_clickable((By.XPATH, "//li[contains(text(), '30 Dias')]"))).click()
        # # time.sleep(0.5)
        
        self.is_ready = True
        print("✅ Scraper pronto na página de download.")

    def _setup_driver(self, headless):
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)
            print(f"📁 Diretório de download criado: {self.download_path}")

        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--window-size=1920,1080")

        # Anti-detecção e configurações comuns
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")

        # Configurações de download
        prefs = {
            "download.default_directory": self.download_path,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "safebrowsing.disable_download_protection": True,
            "profile.default_content_setting_values.automatic_downloads": 1,
            "plugins.always_open_pdf_externally": True,
        }
        chrome_options.add_experimental_option("prefs", prefs)

        print("🔧 Instalando/Atualizando o WebDriver do Chrome...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Scripts anti-detecção
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Habilita downloads em modo headless/normal
        driver.execute_cdp_cmd('Page.setDownloadBehavior', {
            'behavior': 'allow',
            'downloadPath': self.download_path
        })

        print(f"✅ Chrome configurado para downloads em: {self.download_path}")
        return driver

    def _login(self):
        decrypt_and_load_env()
        login = os.getenv("LOGIN_OOBJ")
        senha = os.getenv("SENHA_OOBJ")

        if not login or not senha:
            raise ValueError("As variáveis de ambiente LOGIN_OOBJ e SENHA_OOBJ não foram encontradas.")

        print("Acessando o site http://nfe.araguaia.com.br/monitor/#!/login...")
        self.driver.get("http://nfe.araguaia.com.br/monitor/#!/login")

        self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='usuarioOuEmail']"))).send_keys(login)
        self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='password']"))).send_keys(senha)
        # Localiza o botão de login sem depender do XPath absoluto (que quebra facilmente).
        # <button type="submit" class="btn btn-primary entrar" ng-click="vm.login()">Entrar</button>
        self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class,'entrar') or normalize-space()='Entrar']"))).click()

        print("Login realizado com sucesso! Aguardando o carregamento da página...")
        # Aguardar um elemento da página principal para confirmar o login
        self.wait.until(EC.presence_of_element_located((By.ID, 'main-content')))
        print("Página principal carregada.")


    def download_nfe(self, chave):
        if not self.is_ready:
            raise Exception("O scraper não está pronto. Chame 'prepare_for_downloads()' primeiro.")

        nfe_number = chave[25:34]
        # VERIFICAÇÃO DE ARQUIVO EXISTENTE
        existing_files = glob.glob(os.path.join(self.download_path, f"NF_{nfe_number}_*.xml"))
        if existing_files:
            print(f"⚠️ AVISO: A NFe com número {nfe_number} (chave: {chave}) já foi baixada. Pulando o download.")
            # Atualiza a lista na GUI de qualquer maneira para garantir que está visível
            if self.app:
                self.app.after(0, self.app.update_local_nf_list)
            return # Pula para a próxima chave

        print(f"--- Iniciando processo de download para a chave: {chave} ---")
        try:
            # Obter lista de arquivos ANTES do download
            files_before = set(glob.glob(os.path.join(self.download_path, '*')))
            campo_chave = self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='inputchaveAcessoPesqSimpl']")))
            campo_chave.clear()
            campo_chave.send_keys(chave)
            time.sleep(0.5)

            self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='btnSearchPesquisar']/span[1]/span"))).click()
            time.sleep(1)

            self.wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "table-responsive")))
            
            checkbox = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.ui-grid-selection-row-header-buttons")))
            checkbox.click()
            print("✅ Checkbox da NFe selecionado.")

            # Clica nos botões de download
            self._force_click_download_buttons(chave, "xml")
            self._force_click_download_buttons(chave, "pdf")

            # Aguarda e processa os dois arquivos
            self._wait_for_downloads_and_rename(chave, files_before)

            print(f"SUCESSO: Processo de download da chave {chave} concluído.")

        except Exception as e:
            print(f"ERRO ao processar a chave {chave}: {e}")
            screenshot_path = os.path.join(self.download_path, f"error_{chave}.png")
            self.driver.save_screenshot(screenshot_path)
            print(f"📷 Screenshot do erro salvo em: {screenshot_path}")
            raise

    def _force_click_download_buttons(self, chave, file_type):
        print(f"Iniciando download do {file_type.upper()}...")
        
        if file_type.lower() == "xml":
            btn_xpath = "//*[@id='btnActionBaixarXML']"
            confirm_btn_xpath = "//*[@id='baixarXmlBtnbaixarXml']"
        elif file_type.lower() == "pdf":
            btn_xpath = "//*[@id='dfeActionBaixarDadfe']"
            confirm_btn_xpath = "//*[@id='dadfeBtnBaixarPdf']"
        else:
            raise ValueError("Tipo de arquivo deve ser 'xml' ou 'pdf'")

        try:
            btn_download = self.wait.until(EC.element_to_be_clickable((By.XPATH, btn_xpath)))
            self.driver.execute_script("arguments[0].click();", btn_download)
            print(f"✅ Botão de download {file_type.upper()} clicado.")
            
            time.sleep(1) # Espera o modal de confirmação aparecer
            
            btn_confirmar = self.wait.until(EC.element_to_be_clickable((By.XPATH, confirm_btn_xpath)))
            self.driver.execute_script("arguments[0].click();", btn_confirmar)
            print(f"✅ Botão de confirmação {file_type.upper()} clicado.")
            
        except Exception as e:
            print(f"ERRO no clique do botão de download do {file_type.upper()}: {e}")
            raise

    def _wait_for_downloads_and_rename(self, chave, files_before, timeout=60):
        print(f"Aguardando a finalização do download dos arquivos para a chave {chave}... (timeout: {timeout}s)")
        nfe_number = chave[25:34]
        
        zip_file = None
        pdf_file = None
        xml_file = None

        time_waited = 0
        while time_waited < timeout:
            current_files = set(glob.glob(os.path.join(self.download_path, '*')))
            new_files = current_files - files_before
            
            new_files = {f for f in new_files if not f.endswith(('.crdownload', '.tmp'))}

            if not pdf_file:
                pdf_file = next((f for f in new_files if f.endswith('.pdf')), None)
            
            if not zip_file and not xml_file: # Only search for zip or xml if we haven't found one
                zip_file = next((f for f in new_files if f.endswith('.zip')), None)
                if not zip_file: # If no zip, look for the specific xml
                    xml_file = next((f for f in new_files if f.endswith('.xml') and 'procNFe' in os.path.basename(f)), None)

            if pdf_file and (zip_file or xml_file):
                if zip_file:
                    print("✅ Arquivos .zip e .pdf detectados.")
                else:
                    print("✅ Arquivos .xml e .pdf detectados.")
                break
            
            time.sleep(1)
            time_waited += 1

        if not pdf_file or (not zip_file and not xml_file):
            raise Exception(f"ERRO: Tempo de download excedido para a chave {chave}. Arquivos esperados não encontrados.")

        # Processa e renomeia os arquivos
        self._process_and_rename_files(nfe_number, pdf_path=pdf_file, zip_path=zip_file, xml_path=xml_file)

    def _process_and_rename_files(self, nfe_number, pdf_path, zip_path=None, xml_path=None):
        try:
            extracted_xml_path = None
            if zip_path:
                # Extrai o XML do ZIP
                print(f"📦 Processando arquivo .zip: {os.path.basename(zip_path)}")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    xml_files_in_zip = [f for f in zip_ref.namelist() if f.endswith('.xml') and 'procEvento' not in f]
                    if not xml_files_in_zip:
                        raise Exception("Nenhum XML principal encontrado no arquivo .zip")
                    
                    xml_filename_in_zip = xml_files_in_zip[0]
                    zip_ref.extract(xml_filename_in_zip, self.download_path)
                    extracted_xml_path = os.path.join(self.download_path, xml_filename_in_zip)
                # Remove o zip original
                os.remove(zip_path)
            elif xml_path:
                print(f"📦 Processando arquivo .xml direto: {os.path.basename(xml_path)}")
                extracted_xml_path = xml_path
            else:
                raise Exception("Nenhum arquivo XML (zip ou xml direto) foi fornecido.")


            # Lê o XML para obter o nome do cliente
            print(f"📖 Lendo XML: {os.path.basename(extracted_xml_path)}")
            tree = ET.parse(extracted_xml_path)
            root = tree.getroot()
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            customer_name_element = root.find('.//nfe:dest/nfe:xNome', ns)
            
            if customer_name_element is None:
                print("⚠️ Aviso: Tag <xNome> não encontrada no XML. Usando nome padrão.")
                customer_name = "ClienteNaoIdentificado"
            else:
                customer_name = customer_name_element.text.strip()
                customer_name = "".join(c for c in customer_name if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')

            # Define os novos nomes de arquivo
            new_xml_filename = f"NF_{nfe_number}_{customer_name}.xml"
            new_pdf_filename = f"NF_{nfe_number}_{customer_name}.pdf"
            new_xml_filepath = os.path.join(self.download_path, new_xml_filename)
            new_pdf_filepath = os.path.join(self.download_path, new_pdf_filename)

            # Renomeia o XML
            if os.path.exists(new_xml_filepath):
                os.remove(new_xml_filepath)
            os.rename(extracted_xml_path, new_xml_filepath)
            print(f"✅ XML renomeado para: {new_xml_filename}")

            # Renomeia o PDF
            if os.path.exists(new_pdf_filepath):
                os.remove(new_pdf_filepath)
            os.rename(pdf_path, new_pdf_filepath)
            print(f"✅ PDF renomeado para: {new_pdf_filename}")

            # Atualiza a lista de NFs na GUI, se aplicável
            if self.app:
                self.app.after(0, self.app.update_local_nf_list)

        except ET.ParseError as e:
            print(f"❌ ERRO de parsing no XML: {e}")
            error_xml_path = os.path.join(self.download_path, f"ERRO_XML_NF_{nfe_number}.xml")
            if extracted_xml_path and os.path.exists(extracted_xml_path):
                os.rename(extracted_xml_path, error_xml_path)
            if zip_path and os.path.exists(zip_path):
                os.remove(zip_path)
        except Exception as e:
            print(f"❌ ERRO inesperado ao processar arquivos para NF {nfe_number}: {e}")
            # Remove os arquivos para não tentar de novo
            if zip_path and os.path.exists(zip_path):
                os.remove(zip_path)
            if xml_path and os.path.exists(xml_path):
                os.remove(xml_path)
            raise

    def close(self):
        if self.driver:
            print("Fechando o navegador...")
            self.driver.quit()

def main(chave_para_baixar):
    """Função principal para testar o scraper de forma isolada."""
    scraper = None
    try:
        # Inicia o scraper (headless=True para automação em background)
        scraper = OobjScraper(headless=True)
        scraper.prepare_for_downloads() # Prepara o scraper
        scraper.download_nfe(chave_para_baixar)
        print("Processo de teste finalizado com sucesso.")

    except Exception as e:
        print(f"Ocorreu um erro geral no processo de teste: {e}")
    
    finally:
        if scraper:
            scraper.close()
            print("Navegador fechado.")

if __name__ == "__main__":
    # Chave de exemplo para teste
    main("52250903306578006108550010000209011645903058")