import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk, ImageDraw, ImageFont
import xml.etree.ElementTree as ET
import os
import sys
import threading
import queue
from scrap_oobj import OobjScraper
import pandas as pd
import json
import requests
import base64
from datetime import datetime
import tkinter.messagebox as messagebox
from dotenv import load_dotenv
import subprocess
import uuid
import base64
import hashlib
from cryptography.fernet import Fernet

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

def show_login_dialog():
    """Cria e exibe uma janela de login modal e estilizada."""
    valid_login = os.getenv("APP_LOGIN")
    valid_password = os.getenv("APP_PASSWORD")

    login_window = ttk.Toplevel(title="FatFlow")
    login_window.iconbitmap(os.path.join(get_base_path(), 'img', 'icon_desktop.ico')) 
    login_window.geometry("300x280")
    
    login_window.resizable(False, False)
    login_window.grab_set()

    # Centralizar a janela
    login_window.place_window_center()

    result = {"authenticated": False}

    def authenticate():
        login = entry_login.get().strip()
        password = entry_password.get()

        if login == valid_login and password == valid_password:
            result["authenticated"] = True
            login_window.destroy()
        else:
            messagebox.showerror("Erro de Login", "Login ou senha incorretos!", parent=login_window)
            entry_password.delete(0, "end")

    def on_cancel():
        result["authenticated"] = False
        login_window.destroy()

    # --- Interface da Janela ---
    try:
        img = Image.open(os.path.join(get_base_path(), 'img', 'icon_white.png'))
        img = img.resize((60, 75), Image.Resampling.LANCZOS)
        logo_image = ImageTk.PhotoImage(img)
        logo_label = ttk.Label(login_window, image=logo_image)
        logo_label.image = logo_image  # Keep a reference!
        logo_label.pack(pady=20)
    except Exception as e:
        print(f"Erro ao carregar logo no login: {e}")

    main_frame = ttk.Frame(login_window, padding=(20, 20, 20, 10))
    main_frame.pack(fill="both", expand=True)
    main_frame.grid_columnconfigure(1, weight=1)

    # Campo de Login
    ttk.Label(main_frame, text="Login:").grid(row=1, column=0, sticky="w", padx=(0, 10))
    entry_login = ttk.Entry(main_frame)
    entry_login.grid(row=1, column=1, sticky="ew", pady=(0, 10))
    entry_login.focus()

    # Campo de Senha
    ttk.Label(main_frame, text="Senha:").grid(row=2, column=0, sticky="w", padx=(0, 10))
    entry_password = ttk.Entry(main_frame, show="*")
    entry_password.grid(row=2, column=1, sticky="ew", pady=(0, 20))

    # Botões
    button_frame = ttk.Frame(main_frame)
    button_frame.grid(row=3, column=0, columnspan=2, sticky="e")

    cancel_button = ttk.Button(button_frame, text="Cancelar", command=on_cancel, bootstyle="secondary")
    cancel_button.pack(side="right", padx=(5, 0))

    login_button = ttk.Button(button_frame, text="Entrar", command=authenticate, bootstyle="success")
    login_button.pack(side="right")

    # Bindings
    login_window.bind("<Return>", lambda event: authenticate())
    login_window.protocol("WM_DELETE_WINDOW", on_cancel)

    login_window.style.theme_use("darkly")

    login_window.wait_window()
    return result["authenticated"]

class App(ttk.Window):
    def __init__(self):
        super().__init__()
        self.scraper = None
        self.style.theme_use("darkly")

        # --- Configuração da Janela Principal ---
        self.title("FatFlow")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        try:
            self.icon = ImageTk.PhotoImage(file=os.path.join(get_base_path(), 'img', 'icon_black.png'))
            self.tk.call('wm', 'iconphoto', self._w, self.icon)
        except Exception as e:
            print(f"Erro ao carregar ícone: {e}")
        
        width= 1366
        height= 690
        self.geometry("1370x690-0+0")
        
        self.minsize(1000, 690)

        # --- Layout Responsivo ---
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Criação dos Widgets ---
        self.create_header()
        self.load_initial_data()
        self.create_content_frame()
        self.update_table_colors()
        self.create_footer()

    def load_initial_data(self):
        """Carrega dados iniciais de planilhas para preencher comboboxes."""
        try:
            # Carregar Safras
            df_safras = pd.read_excel(os.path.join(get_base_path(), "data", "Relacionamento_Culturas_Cultivares.xlsx"), sheet_name="Safras")
            self.safras_map = dict(zip(df_safras['DESCRICAO'], df_safras['CODIGO']))
            self.safra_list = list(self.safras_map.keys())

            # Carregar Destinatários
            df_destinatarios = pd.read_excel(os.path.join(get_base_path(), "data", "Relacionamento_Culturas_Cultivares.xlsx"), sheet_name="Destinatário", dtype={'CNPJ': str})
            self.destinatarios_map = {}
            for _, row in df_destinatarios.iterrows():
                self.destinatarios_map[row['Cidade']] = {
                    'renasem': row['Renasem'],
                    'cnpj': row['CNPJ'],
                    'codigo_cidade': row['Código Cidade']
                }
            self.destinatario_list = list(self.destinatarios_map.keys())

            # Carregar Culturas (Categorias)
            df_culturas = pd.read_excel(os.path.join(get_base_path(), "data", "Relacionamento_Culturas_Cultivares.xlsx"), sheet_name="Culturas")
            self.culturas_map = dict(zip(df_culturas['DESCRICAO'], df_culturas['CODIGO']))
            self.cultura_list = list(self.culturas_map.keys())

            # Carregar Relação Culturas x Cultivares
            self.cultivares_df = pd.read_excel(os.path.join(get_base_path(), "data", "Relacionamento_Culturas_Cultivares.xlsx"), sheet_name="Relacao_Culturas_Cultivares")
            self.cultura_cultivar_map = {}
            for _, row in self.cultivares_df.iterrows():
                cultura_codigo = row['CULTURA_CODIGO']
                if cultura_codigo not in self.cultura_cultivar_map:
                    self.cultura_cultivar_map[cultura_codigo] = []
                self.cultura_cultivar_map[cultura_codigo].append(row['CULTIVAR_DESCRICAO'])

        except Exception as e:
            messagebox.showerror("Erro ao Carregar Dados", f"Não foi possível carregar os dados da planilha 'Relacionamento_Culturas_Cultivares.xlsx'.\n\nErro: {e}")
            self.safras_map = {}
            self.safra_list = ["Erro ao carregar"]
            self.destinatarios_map = {}
            self.destinatario_list = ["Erro ao carregar"]
            self.culturas_map = {}
            self.cultura_list = ["Erro ao carregar"]
            self.cultura_cultivar_map = {}

    def create_header(self):
        """Cria o cabeçalho da aplicação com o logo e o menu de temas."""
        self.header_frame = ttk.Frame(self, padding=(15, 10))
        self.header_frame.grid(row=0, column=0, sticky='ew')
        self.header_frame.grid_columnconfigure(1, weight=1)

    def change_theme(self, theme_name):
        """Altera o tema da aplicação."""
        self.style.theme_use(theme_name)
        self.header_frame.destroy()
        self.create_header()
        self.content_frame.destroy()
        self.create_content_frame()
        self.update_table_colors()
        self.footer_frame.destroy()
        self.create_footer()

    def update_table_colors(self):
        """Updates the alternating row colors for the tables based on the current theme."""
        if self.style.theme.type == 'dark':
            odd_color = '#252525'
            even_color = '#303030'
        else:
            odd_color = '#f0f0f0'
            even_color = '#e0e0e0'

        self.header_tree.tag_configure('oddrow', background=odd_color)
        self.header_tree.tag_configure('evenrow', background=even_color)
        self.items_tree.tag_configure('oddrow', background=odd_color)
        self.items_tree.tag_configure('evenrow', background=even_color)
        self.tree_itens.tag_configure('oddrow', background=odd_color)
        self.tree_itens.tag_configure('evenrow', background=even_color)
        self.pdf_tree.tag_configure('selected_pdf', background=self.style.colors.success, foreground=self.style.colors.selectfg)

        # Set row height for pdf_tree
        style = ttk.Style()
        style.configure("pdf.Treeview", rowheight=30)
        self.pdf_tree.configure(style="pdf.Treeview")

    def create_placeholder_logo(self):
        """Cria um logo placeholder com as iniciais 'CSC'."""
        try:
            width, height = 150, 50
            img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            primary_color = self.style.colors.primary
            secondary_color = self.style.colors.secondary
            draw.rectangle([0, 0, width / 2, height], fill=primary_color)
            draw.rectangle([width / 2, 0, width, height], fill=secondary_color)
            try:
                font = ImageFont.truetype("segoeui.ttf", 32, encoding='unic')
            except IOError:
                font = ImageFont.load_default()
            draw.text((width/2, height/2), "CSC", fill=self.style.colors.selectfg, font=font, anchor="mm", stroke_width=1, stroke_fill=self.style.colors.selectbg)
            return ImageTk.PhotoImage(img)
        except Exception:
            return tk.PhotoImage(width=120, height=40)

    def create_content_frame(self):
        """Cria a área principal de conteúdo com as abas."""
        self.content_frame = ttk.Frame(self, padding=(40, 20))
        self.content_frame.grid(row=1, column=0, sticky='nsew')
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        notebook = ttk.Notebook(self.content_frame)
        notebook.grid(row=0, column=0, sticky='nsew')

        self.tab1 = self.create_tab1(notebook)
        self.tab2 = self.create_tab2(notebook)
        self.tab3 = self.create_tab3(notebook)

        notebook.add(self.tab1, text='Check do Carregamento')
        notebook.add(self.tab2, text='NF & Guia Fase')
        notebook.add(self.tab3, text='Enviar para SoftSul')

        self.update_local_nf_list()

    def create_tab1(self, parent):
        """Cria a aba 'Check do Carregamento'."""
        tab = ttk.Frame(parent, padding=10)
        tab.grid_columnconfigure(0, weight=1)

        search_frame = ttk.Frame(tab)
        search_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        search_frame.grid_columnconfigure(5, weight=1)

        ttk.Label(search_frame, text="Safra:").grid(row=0, column=0, sticky='w', padx=(0, 5))
        self.safra_carregamento_entry = ttk.Entry(search_frame)
        self.safra_carregamento_entry.grid(row=0, column=1, sticky='w')

        ttk.Label(search_frame, text="Carga Web:").grid(row=0, column=2, sticky='w', padx=(15, 5))
        self.carga_web_entry = ttk.Entry(search_frame)
        self.carga_web_entry.grid(row=0, column=3, sticky='w')

        ttk.Label(search_frame, text="Numero ZHCD:").grid(row=0, column=4, sticky='w', padx=(15, 5))
        self.zhcd_entry = ttk.Entry(search_frame)
        self.zhcd_entry.grid(row=0, column=5, sticky='w')

        buscar_button = ttk.Button(search_frame, text="Buscar", command=self.buscar_carregamento, bootstyle="success-outline")
        buscar_button.grid(row=0, column=6, padx=15)

        header_table_frame = ttk.LabelFrame(tab, text="Cabeçalho do Carregamento", padding=5)
        header_table_frame.grid(row=1, column=0, sticky='nsew', pady=(0, 5))
        header_table_frame.grid_columnconfigure(0, weight=1)
        header_table_frame.grid_rowconfigure(0, weight=1)

        self.header_tree = ttk.Treeview(header_table_frame, columns=("Campo", "Valor"), show='headings', height=6)
        self.header_tree.heading("Campo", text="Campo")
        self.header_tree.heading("Valor", text="Valor")
        self.header_tree.column("Campo", width=150)
        self.header_tree.grid(row=0, column=0, sticky='nsew')

        items_table_frame = ttk.LabelFrame(tab, text="Itens do Carregamento", padding=10)
        items_table_frame.grid(row=2, column=0, sticky='nsew')
        items_table_frame.grid_columnconfigure(0, weight=1)
        items_table_frame.grid_rowconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        cols = ("ID Pedido SAP", "Cód. Semente", "Cultivar", "Lote", "Sacas", "Peso", "Valor")
        self.items_tree = ttk.Treeview(items_table_frame, columns=cols, show='headings')
        for col in cols:
            self.items_tree.heading(col, text=col)
            self.items_tree.column(col, width=50, anchor='center')
        self.items_tree.grid(row=0, column=0, sticky='nsew')

        scrollbar = ttk.Scrollbar(items_table_frame, orient='vertical', command=self.items_tree.yview, bootstyle="success-round")
        self.items_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky='ns')

        subtotals_frame = ttk.Frame(tab)
        subtotals_frame.grid(row=3, column=0, sticky='ew', pady=(10, 0))
        subtotals_frame.grid_columnconfigure((0, 1, 2), weight=1)

        sacas_card = ttk.LabelFrame(subtotals_frame, text="Total Sacas")
        sacas_card.grid(row=0, column=0, padx=10, pady=3, sticky="ew")
        self.sacas_subtotal_label = ttk.Label(sacas_card, text="0", font=('Segoe UI', 12, 'bold'))
        self.sacas_subtotal_label.pack(pady=5)

        peso_card = ttk.LabelFrame(subtotals_frame, text="Total Peso")
        peso_card.grid(row=0, column=1, padx=10, pady=3, sticky="ew")
        self.peso_subtotal_label = ttk.Label(peso_card, text="0,00", font=('Segoe UI', 12, 'bold'))
        self.peso_subtotal_label.pack(pady=5)

        valor_card = ttk.LabelFrame(subtotals_frame, text="Total Valor")
        valor_card.grid(row=0, column=2, padx=10, pady=3, sticky="ew")
        self.valor_subtotal_label = ttk.Label(valor_card, text="0,00", font=('Segoe UI', 12, 'bold'))
        self.valor_subtotal_label.pack(pady=5)

        return tab

    def create_tab2(self, parent):
        """Cria a aba 'NF & Guia Fase' com layout de duas colunas."""
        tab = ttk.Frame(parent, padding=(0, 25))
        tab.grid_columnconfigure(1, weight=1) 
        tab.grid_rowconfigure(0, weight=1)

        left_frame = ttk.Frame(tab)
        left_frame.grid(row=0, column=0, sticky='ns', padx=(20, 30))

        local_nf_frame = ttk.LabelFrame(left_frame, text="1. Carregar NF Local", padding=(15, 10))
        local_nf_frame.grid(row=0, column=0, sticky='ew', pady=(0, 20))
        local_nf_frame.grid_columnconfigure(0, weight=1)

        self.local_nf_combo = ttk.Combobox(local_nf_frame, state='readonly', bootstyle="success")
        self.local_nf_combo.grid(row=0, column=0, sticky='ew', padx=(0, 10))

        load_button = ttk.Button(local_nf_frame, text="Carregar", command=self.load_selected_local_nf, bootstyle="success-outline")
        load_button.grid(row=0, column=1, sticky='e')

        batch_download_frame = ttk.LabelFrame(left_frame, text="2. Baixar Novas NFs (uma por linha)", padding=(15, 10))
        batch_download_frame.grid(row=1, column=0, sticky='ew', pady=(0, 20))
        batch_download_frame.grid_columnconfigure(0, weight=1)

        self.nfe_keys_text = tk.Text(batch_download_frame, height=5, width=40, wrap='none')
        self.nfe_keys_text.grid(row=0, column=0, columnspan=2, sticky='ew')

        x_scrollbar_text = ttk.Scrollbar(batch_download_frame, orient='horizontal', command=self.nfe_keys_text.xview)
        x_scrollbar_text.grid(row=1, column=0, columnspan=2, sticky='ew')
        self.nfe_keys_text['xscrollcommand'] = x_scrollbar_text.set

        self.download_button = ttk.Button(batch_download_frame, text="Baixar NFs", command=self.download_batch_nfs, bootstyle="success-outline", state="disabled")
        self.download_button.grid(row=2, column=0, columnspan=2, pady=(10, 0))

        header_form_frame = ttk.LabelFrame(left_frame, text="3. Dados da Guia", padding=(15, 10))
        header_form_frame.grid(row=2, column=0, sticky='ew')
        header_form_frame.grid_columnconfigure(1, weight=1)

        self.fields_tab2 = {}
        field_labels = {
            "natureza_operacao": "Natureza Operação:", "grupo_cultura": "Grupo Cultura:",
            "safra": "Safra:", "destinatario": "Destinatário:"
        }

        for i, (key, label) in enumerate(field_labels.items()):
            ttk.Label(header_form_frame, text=label).grid(row=i, column=0, sticky='w', padx=5, pady=5)
            if key == "natureza_operacao":
                widget = ttk.Combobox(header_form_frame, state='readonly', values=["Revenda", "Produtor Final"], bootstyle="success")
                widget.set("Revenda")
            elif key == "grupo_cultura":
                widget = ttk.Combobox(header_form_frame, state='readonly', values=["Sementes", "Mudas"], bootstyle="success")
                widget.set("Sementes")
            elif key == "safra":
                widget = ttk.Combobox(header_form_frame, state='readonly', values=self.safra_list, bootstyle="success")
                widget.set("2025/2026 - SOJA")
            elif key == "destinatario":
                widget = ttk.Combobox(header_form_frame, state='readonly', values=self.destinatario_list, bootstyle="success")
            else:
                widget = ttk.Entry(header_form_frame)
            widget.grid(row=i, column=1, sticky='ew', padx=5, pady=6)
            self.fields_tab2[key] = widget

        self.qas_mode = tk.BooleanVar()
        qas_check = ttk.Checkbutton(header_form_frame, text="Modo QAS", variable=self.qas_mode, bootstyle="success-round-toggle")
        qas_check.grid(row=i + 1, column=0, columnspan=2, sticky='w', padx=5, pady=10)

        right_frame = ttk.LabelFrame(tab, text="4. Itens da Guia", padding=(20, 15))
        right_frame.grid(row=0, column=1, sticky='nsew', padx=(0, 20))
        right_frame.grid_rowconfigure(1, weight=1) # Row for the tree_itens
        right_frame.grid_columnconfigure(0, weight=1)

        # Frame for top info (NF info and refresh button)
        top_info_frame = ttk.Frame(right_frame)
        top_info_frame.grid(row=0, column=0, sticky='ew', columnspan=2, pady=(0, 10))
        top_info_frame.grid_columnconfigure(0, weight=1)

        destinatario_frame = ttk.Frame(top_info_frame)
        destinatario_frame.pack(side='left')
        ttk.Label(destinatario_frame, text="Destinatário da NF-e:", font=('Segoe UI', 9, 'bold')).pack(side='left')
        self.nfe_destinatario_label = ttk.Label(destinatario_frame, text="Nenhuma NF carregada", font=('Segoe UI', 9), bootstyle="info")
        self.nfe_destinatario_label.pack(side='left', padx=5)

        refresh_cultivar_button = ttk.Button(top_info_frame, text="Atualizar Dados Guia Fase", command=self._refresh_cultivar_data, bootstyle="success-outline")
        refresh_cultivar_button.pack(side='right', padx=(0,5))

        cols = ("Nome do Produto", "Cód. Produto", "Cód. Cultivar", "Nome Cultivar", "Cód. Categoria", "Lote", "Peso Bruto")
        self.tree_itens = ttk.Treeview(right_frame, columns=cols, show='headings')

        # Define as colunas que serão exibidas e a ORDEM
        self.tree_itens['displaycolumns'] = ("Nome do Produto", "Cód. Produto", "Nome Cultivar", "Lote", "Peso Bruto", "Cód. Categoria", "Cód. Cultivar")

        for col in cols:
            # Define o texto do cabeçalho
            col_text = col
            if col == "Cód. Categoria":
                col_text = "ID Cultura"
            elif col == "Cód. Cultivar":
                col_text = "ID Cultivar"
            
            self.tree_itens.heading(col, text=col_text, anchor='center')

            # Define a largura e alinhamento
            if col == "Nome do Produto":
                self.tree_itens.column(col, width=300, anchor='w', stretch=True)
            elif col == "Nome Cultivar":
                self.tree_itens.column(col, width=200, anchor='center', stretch=True)
            else:
                self.tree_itens.column(col, width=100, anchor='center', stretch=False)

        self.tree_itens.grid(row=1, column=0, columnspan=2, sticky='nsew')
        self.tree_itens.bind("<Double-1>", self.open_edit_item_window)

        y_scrollbar = ttk.Scrollbar(right_frame, orient='vertical', command=self.tree_itens.yview)
        y_scrollbar.grid(row=1, column=1, sticky='ns')
        self.tree_itens.configure(yscrollcommand=y_scrollbar.set)

        x_scrollbar = ttk.Scrollbar(right_frame, orient='horizontal', command=self.tree_itens.xview)
        x_scrollbar.grid(row=2, column=0, columnspan=2, sticky='ew')
        self.tree_itens.configure(xscrollcommand=x_scrollbar.set)

        item_buttons_frame = ttk.Frame(right_frame)
        item_buttons_frame.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(15,0))
        item_buttons_frame.grid_columnconfigure(0, weight=1)

        self.peso_bruto_subtotal_label = ttk.Label(item_buttons_frame, text="Total Peso Bruto: 0,00", font=('Segoe UI', 10, 'bold'))
        self.peso_bruto_subtotal_label.grid(row=0, column=0, sticky='w')

        ttk.Button(item_buttons_frame, text="Adicionar Item", command=self.add_item, bootstyle="success-outline").grid(row=0, column=1, padx=5, sticky='e')
        ttk.Button(item_buttons_frame, text="Remover Selecionado", command=self.remove_item, bootstyle="danger-outline").grid(row=0, column=2, padx=5, sticky='e')

        emitir_button = ttk.Button(item_buttons_frame, text="Emitir Guia", command=self.emitir_guia, bootstyle="success")
        emitir_button.grid(row=0, column=3, sticky='e', padx=5)

        return tab

    def buscar_carregamento(self):
        """Busca os dados do carregamento na API da SoftSul."""
        safra = self.safra_carregamento_entry.get()
        if not safra:
            messagebox.showerror("Erro", "Por favor, preencha o campo safra.")
            return

        numeroprog_web = self.carga_web_entry.get()
        sap_carga_id = self.zhcd_entry.get()

        if not numeroprog_web and not sap_carga_id:
            messagebox.showerror("Erro", "Por favor, preencha pelo menos um dos campos de busca.")
            return

        self.show_loading_indicator("Buscando dados do carregamento...")
        self.search_thread = threading.Thread(target=self._buscar_carregamento_thread, args=(safra, numeroprog_web, sap_carga_id))
        self.search_thread.start()
        self.after(100, self.check_search_thread)

    def _buscar_carregamento_thread(self, safra, numeroprog_web, sap_carga_id):
        """Executa a busca na API em uma thread separada."""
        try:
            params = {'safra': safra}
            if numeroprog_web:
                params['numeroprog_web'] = numeroprog_web
            if sap_carga_id:
                params['sap_carga_id'] = sap_carga_id

            url = f'https://vig.softsul.agr.br/api/sap/crm/carregamentos'
            headers = {'Authorization': 'Basic c2FwLmludGVncmFjYW9AZW1haWwuY29tOiQkc2FwSU5URUdSQUNBTyMj'}
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json().get('data', [])
            
            self.after(0, self.populate_carregamento_tables, data)

        except requests.exceptions.RequestException as e:
            error_message = f"Falha na comunicação com a API: {e}"
            if e.response is not None:
                try:
                    error_message += f"\n\nDetalhes: {e.response.json()}"
                except json.JSONDecodeError:
                    error_message += f"\n\nDetalhes: {e.response.text}"
            self.after(0, self.hide_loading_indicator)
            messagebox.showerror("Erro de Rede", error_message)
        except Exception as e:
            self.after(0, self.hide_loading_indicator)
            messagebox.showerror("Erro na Busca", f"Ocorreu um erro durante a busca do carregamento: {e}")

    def check_search_thread(self):
        """Verifica se a thread de busca terminou."""
        if self.search_thread.is_alive():
            self.after(100, self.check_search_thread)
        else:
            self.hide_loading_indicator()

    def populate_carregamento_tables(self, data):
        """Preenche as tabelas de cabeçalho e itens com os dados do carregamento."""
        for item in self.header_tree.get_children():
            self.header_tree.delete(item)
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)

        if not data:
            messagebox.showinfo("Informação", "Nenhum carregamento encontrado para os filtros informados.")
            return

        first_item = data[0]
        header_data = {
            "Ordem de Carregamento": first_item.get('ordemcarregamento'),
            "Cliente": first_item.get('cliente'),
            "Placa do Caminhão": first_item.get('placacaminhao'),
            "Observação": first_item.get('observacao'),
            "Transportador": first_item.get('transportador_nome'),
            "CNPJ Transportador": first_item.get('transportador_cgc_cpf')
        }
        for i, (campo, valor) in enumerate(header_data.items()):
            tag = 'oddrow' if i % 2 else 'evenrow'
            self.header_tree.insert('', 'end', values=(campo, valor), tags=(tag,))

        grouped_items = {}
        for carregamento in data:
            for item in carregamento.get('itens', []):
                lote = item.get('numerolote')
                if lote in grouped_items:
                    grouped_items[lote]['sacas'] += int(item.get('sacas', 0))
                    grouped_items[lote]['peso'] += float(item.get('peso', 0.0))
                    grouped_items[lote]['valor'] += float(item.get('valor', 0.0))
                else:
                    grouped_items[lote] = {
                        'sap_pedido_id': item.get('sap_pedido_id'),
                        'codigosemente': item.get('codigosemente'),
                        'cultivar_descricao': item.get('cultivar_descricao'),
                        'numerolote': lote,
                        'sacas': int(item.get('sacas', 0)),
                        'peso': float(item.get('peso', 0.0)),
                        'valor': float(item.get('valor', 0.0))
                    }

        total_sacas = 0
        total_peso = 0.0
        total_valor = 0.0
        for i, (lote, item) in enumerate(grouped_items.items()):
            tag = 'oddrow' if i % 2 else 'evenrow'
            self.items_tree.insert('', 'end', values=(
                item['sap_pedido_id'],
                item['codigosemente'],
                item['cultivar_descricao'],
                item['numerolote'],
                item['sacas'],
                f"{item['peso']:.2f}",
                f"{item['valor']:.2f}"
            ), tags=(tag,))
            total_sacas += item['sacas']
            total_peso += item['peso']
            total_valor += item['valor']

        self.sacas_subtotal_label.config(text=f"{total_sacas:,}".replace(",", "."))
        self.peso_subtotal_label.config(text=f"{total_peso:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        self.valor_subtotal_label.config(text=f"{total_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    def create_tab3(self, parent):
        """Cria a aba 'Enviar para SoftSul'."""
        tab = ttk.Frame(parent, padding=10)
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1) # Two columns
        tab.grid_rowconfigure(0, weight=1)

        # Left Frame for PDF selection and Carga Web
        left_frame = ttk.Frame(tab)
        left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        left_frame.grid_rowconfigure(1, weight=1) # Row for the file list
        left_frame.grid_columnconfigure(0, weight=1)

        # Top frame for Carga Web input
        top_frame = ttk.Frame(left_frame)
        top_frame.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        top_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(top_frame, text="Carga Web:").grid(row=0, column=0, sticky='w', padx=(0, 5))
        self.carga_web_softsul_entry = ttk.Entry(top_frame)
        self.carga_web_softsul_entry.grid(row=0, column=1, sticky='ew', padx=(0, 10))

        # Frame for PDF file selection
        pdf_selection_frame = ttk.LabelFrame(left_frame, text="Selecionar PDFs para Enviar", padding=10)
        pdf_selection_frame.grid(row=1, column=0, sticky='nsew', pady=(0, 10))
        pdf_selection_frame.grid_columnconfigure(0, weight=1)
        pdf_selection_frame.grid_rowconfigure(0, weight=1)

        self.pdf_tree = ttk.Treeview(pdf_selection_frame, columns=("Selecionar", "Nome do Arquivo", "Tipo"), show='headings')
        self.pdf_tree.heading("Selecionar", text="Sel.", anchor='center')
        self.pdf_tree.heading("Nome do Arquivo", text="Nome do Arquivo")
        self.pdf_tree.heading("Tipo", text="Tipo")

        self.pdf_tree.column("Selecionar", width=70, anchor='center', stretch=False)
        self.pdf_tree.column("Nome do Arquivo", width=400, anchor='w', stretch=True)
        self.pdf_tree.column("Tipo", width=100, anchor='center', stretch=False)

        self.pdf_tree.grid(row=0, column=0, sticky='nsew')

        pdf_scrollbar_y = ttk.Scrollbar(pdf_selection_frame, orient='vertical', command=self.pdf_tree.yview, bootstyle="success-round")
        pdf_scrollbar_y.grid(row=0, column=1, sticky='ns')
        self.pdf_tree.configure(yscrollcommand=pdf_scrollbar_y.set)

        # pdf_scrollbar_x = ttk.Scrollbar(pdf_selection_frame, orient='horizontal', command=self.pdf_tree.xview, bootstyle="success-round")
        # pdf_scrollbar_x.grid(row=1, column=0, sticky='ew')
        # self.pdf_tree.configure(xscrollcommand=pdf_scrollbar_x.set)

        self.pdf_tree.bind("<ButtonRelease-1>", self.on_pdf_tree_click)

        # Buttons frame
        buttons_frame = ttk.Frame(left_frame)
        buttons_frame.grid(row=2, column=0, sticky='ew', pady=(10, 0))
        buttons_frame.grid_columnconfigure(0, weight=1)
        buttons_frame.grid_columnconfigure(1, weight=1)

        refresh_button = ttk.Button(buttons_frame, text="Atualizar Lista de PDFs", command=self.update_pdf_list_tab3, bootstyle="info-outline")
        refresh_button.grid(row=0, column=0, sticky='w', padx=(0, 5))

        send_button = ttk.Button(buttons_frame, text="Enviar para SoftSul", command=self.send_to_softsul, bootstyle="success")
        send_button.grid(row=0, column=1, sticky='e', padx=(5, 0))

        # Right Frame for Log
        log_frame = ttk.LabelFrame(tab, text="Log de Envio", padding=10)
        log_frame.grid(row=0, column=1, sticky='nsew', padx=(10, 0))
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

        self.softsul_log_text = tk.Text(log_frame, height=8, state='disabled', wrap='word', font=('TkFixedFont', 9))
        self.softsul_log_text.grid(row=0, column=0, sticky='nsew')

        log_scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=self.softsul_log_text.yview, bootstyle="success-round")
        log_scrollbar.grid(row=0, column=1, sticky='ns')
        self.softsul_log_text['yscrollcommand'] = log_scrollbar.set

        self.update_pdf_list_tab3() # Populate the list initially

        return tab

    def create_footer(self):
        """Cria o rodapé da aplicação."""
        self.footer_frame = ttk.Frame(self, padding=(10, 5))
        self.footer_frame.grid(row=2, column=0, sticky='ew')
        self.footer_frame.grid_columnconfigure(1, weight=1)

        try:
            if self.style.theme.type == 'dark':
                icon_path = os.path.join(get_base_path(), 'img', 'icon_white.png')
            else:
                icon_path = os.path.join(get_base_path(), 'img', 'icon_black.png')
            img = Image.open(icon_path)
            base_height = 30
            if img.height > base_height:
                h_percent = (base_height / float(img.size[1]))
                w_size = int((float(img.size[0]) * float(h_percent)))
                img = img.resize((w_size, base_height), Image.Resampling.LANCZOS)
            self.logo_image = ImageTk.PhotoImage(img)
        except Exception as e:
            self.logo_image = self.create_placeholder_logo()

        logo_label = ttk.Label(self.footer_frame, image=self.logo_image)
        logo_label.grid(row=0, column=0, sticky='w', padx=10)

        footer_label = ttk.Label(self.footer_frame, text="Powered by Melhoria Contínua", bootstyle="secondary")
        footer_label.grid(row=0, column=1, sticky='e', padx=10)

        theme_menu = ttk.Menu(self, tearoff=0)
        theme_menu.add_command(label="Modo Escuro (Solar)", command=lambda: self.change_theme("solar"))
        theme_menu.add_command(label="Modo Escuro (Darkly)", command=lambda: self.change_theme("darkly"))
        theme_menu.add_command(label="Modo Claro (Flatly)", command=lambda: self.change_theme("flatly"))

        theme_button = ttk.Menubutton(self.footer_frame, text="Tema", menu=theme_menu, bootstyle=("light-outline" if self.style.theme.type == 'light' else "secondary-outline"))
        theme_button.grid(row=0, column=2, sticky='e', padx=10)

    def log_softsul(self, message):
        """Adiciona uma mensagem à área de log da aba SoftSul."""
        self.softsul_log_text.config(state='normal')
        self.softsul_log_text.insert(tk.END, f"> {message}\n")
        self.softsul_log_text.config(state='disabled')
        self.softsul_log_text.see(tk.END)

    def emitir_guia(self):
        """Verifica o modo (PROD/QAS) e chama a thread de emissão correspondente."""
        if self.qas_mode.get():
            self.emitir_guia_qas()
        else:
            self.emitir_guia_prod()

    def emitir_guia_prod(self):
        """Coleta os dados, monta o JSON e emite a guia para o ambiente de PRODUÇÃO."""
        try:
            selected_natureza = self.fields_tab2["natureza_operacao"].get()
            natureza_operacao = 2 if selected_natureza == "Revenda" else 1

            selected_cultura = self.fields_tab2["grupo_cultura"].get()
            grupo_cultura = 2 if selected_cultura == "Sementes" else 8

            selected_safra = self.fields_tab2["safra"].get()
            codigo_safra = self.safras_map.get(selected_safra)

            selected_destinatario = self.fields_tab2["destinatario"].get()
            destinatario_data = self.destinatarios_map.get(selected_destinatario)

            if not all([selected_natureza, selected_cultura, selected_safra, selected_destinatario]):
                messagebox.showerror("Erro de Validação", "Por favor, preencha todos os campos da guia.")
                return

            selected_nf_file = self.local_nf_combo.get()
            if not selected_nf_file or not selected_nf_file.endswith(".xml"):
                messagebox.showerror("Erro de Validação", "Nenhuma NF-e foi carregada. Selecione uma NF na lista '1. Carregar NF Local' e clique em 'Carregar'.")
                return

            xml_path = os.path.join(get_base_path(), "outputs", selected_nf_file)
            nfe_data = self.extract_nfe_data_from_xml(xml_path)
            if not nfe_data:
                return

            itens = []
            for item_id in self.tree_itens.get_children():
                item_values = self.tree_itens.item(item_id, 'values')
                try:
                    itens.append({
                        "codigo_cultivar": int(item_values[2]),
                        "codigo_categoria": int(item_values[4]),
                        "lote": str(item_values[5]),
                        "quantidade": float(item_values[6])
                    })
                except (ValueError, IndexError) as e:
                    messagebox.showerror("Erro nos Itens", f"O item '{item_values[0]}' contém dados inválidos e não pode ser processado.\n\nDetalhes: {e}")
                    return
            
            if not itens:
                messagebox.showerror("Erro de Validação", "A guia deve conter pelo menos um item.")
                return

            json_payload = {
                "cpf_cnpj": "03306578006108",
                "cidade_ibge_origem": "5222005",
                "natureza_operacao": natureza_operacao,
                "grupo_cultura": grupo_cultura,
                "codigo_propiedade_estabelecimento": "15001",
                "codigo_safra": codigo_safra,
                "telefone": "62998696491",
                "destinatario": {
                    "cpf_cnpj": destinatario_data['cnpj'],
                    "nome": "Araguaia S.A.",
                    "renasem": destinatario_data['renasem'],
                    "cidade_ibge": str(destinatario_data['codigo_cidade'])
                },
                "nfe": nfe_data,
                "itens": itens
            }

            self.show_loading_indicator("Emitindo Guia Fase (PRODUÇÃO)...")
            self.emission_thread = threading.Thread(target=self._emitir_guia_thread_prod, args=(json_payload,))
            self.emission_thread.start()
            self.after(100, self.check_emission_thread)

        except Exception as e:
            self.hide_loading_indicator()
            messagebox.showerror("Erro Inesperado (PROD)", f"Ocorreu um erro inesperado ao preparar a emissão:\n{e}")

    def emitir_guia_qas(self):
        """Pede os dados da NFe, monta o JSON com dados fixos de QAS e emite a guia."""
        try:
            nfe_data = self.prompt_for_nfe_data()
            if not nfe_data or not all(nfe_data.values()):
                messagebox.showinfo("Cancelado", "A emissão da guia foi cancelada porque os dados da NF-e não foram preenchidos.")
                return

            json_payload = {
                "cpf_cnpj": "99297574149",
                "cidade_ibge_origem": "5103403",
                "natureza_operacao": 1,
                "grupo_cultura": 2,
                "codigo_propiedade_estabelecimento": "870",
                "codigo_safra": 4,
                "telefone": "65998974552",
                "destinatario": {
                    "cpf_cnpj": "10425282000122",
                    "nome": "Bom Futuro Agricola",
                    "renasem": "123456",
                    "cidade_ibge": "5100409"
                },
                "nfe": nfe_data,
                "itens": [
                    {
                        "codigo_cultivar": 30114,
                        "codigo_categoria": 6,
                        "lote": "55",
                        "quantidade": 1
                    }
                ]
            }

            self.show_loading_indicator("Emitindo Guia Fase (QAS)...")
            self.emission_thread = threading.Thread(target=self._emitir_guia_thread_qas, args=(json_payload,))
            self.emission_thread.start()
            self.after(100, self.check_emission_thread)

        except Exception as e:
            self.hide_loading_indicator()
            messagebox.showerror("Erro Inesperado (QAS)", f"Ocorreu um erro inesperado ao preparar a emissão em QAS:\n{e}")

    def _emitir_guia_thread_qas(self, payload):
        """Executa a emissão e o download em uma thread para o ambiente de QAS."""
        try:
            url_emitir = 'http://162.214.76.169/webservice/api/guia/regime/emitir'
            headers = {
                'X-Token': os.getenv("X-TOKEN"),
                'Content-Type': 'application/json'
            }
            response_emitir = requests.post(url_emitir, headers=headers, json=payload)
            response_emitir.raise_for_status()
            
            guia_numero = response_emitir.json().get('codigo_guia')
            if not guia_numero:
                raise Exception("A API de emissão (QAS) não retornou o número da guia.")

            self.after(0, self.update_loading_message, "Baixando PDF da Guia (QAS)...")
            url_baixar = f'http://162.214.76.169/webservice/api/busca/guia/{guia_numero}'
            response_baixar = requests.get(url_baixar, headers=headers, json={"tipo": "pdf"})
            response_baixar.raise_for_status()

            pdf_base64 = response_baixar.json().get('b64Pdf')
            if not pdf_base64:
                raise Exception("A API de busca da guia (QAS) não retornou o conteúdo do PDF.")
            
            pdf_decoded = base64.b64decode(pdf_base64)

            nfe_numero = payload.get('nfe', {}).get('numero', 'sem_numero')
            output_path = os.path.join(get_base_path(), "outputs", f"Guia Fase_{nfe_numero}.pdf")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(pdf_decoded)
            
            self.after(0, self.hide_loading_indicator)
            messagebox.showinfo("Sucesso (QAS)", f"Guia Fase emitida e salva com sucesso em:\n{os.path.abspath(output_path)}")

        except requests.exceptions.RequestException as e:
            error_message = f"Falha na comunicação com a API de QAS: {e}"
            if e.response is not None:
                try:
                    error_message += f"\n\nDetalhes: {e.response.json()}"
                except json.JSONDecodeError:
                    error_message += f"\n\nDetalhes: {e.response.text}"
            self.after(0, self.hide_loading_indicator)
            messagebox.showerror("Erro de Rede (QAS)", error_message)
        except Exception as e:
            self.after(0, self.hide_loading_indicator)
            messagebox.showerror("Erro na Emissão (QAS)", f"Ocorreu um erro durante a emissão da guia em QAS: {e}")

    def _emitir_guia_thread_prod(self, payload):
        """Executa a emissão e o download em uma thread para o ambiente de PRODUÇÃO."""
        try:
            url_emitir = 'http://162.214.76.169/webservice/api/guia/regime/emitir'
            headers = {
                'X-Token': os.getenv("X-TOKEN-PROD"),
                'Content-Type': 'application/json'
            }
            response_emitir = requests.post(url_emitir, headers=headers, json=payload)
            response_emitir.raise_for_status()
            
            guia_numero = response_emitir.json().get('codigo_guia')
            if not guia_numero:
                raise Exception("A API de emissão não retornou o número da guia.")

            self.after(0, self.update_loading_message, "Baixando PDF da Guia...")
            url_baixar = f'http://162.214.76.169/webservice/api/busca/guia/{guia_numero}'
            response_baixar = requests.get(url_baixar, headers=headers, json={"tipo": "pdf"})
            response_baixar.raise_for_status()

            pdf_base64 = response_baixar.json().get('b64Pdf')
            if not pdf_base64:
                raise Exception("A API de busca da guia não retornou o conteúdo do PDF.")
            
            pdf_decoded = base64.b64decode(pdf_base64)

            nfe_numero = payload.get('nfe', {}).get('numero', 'sem_numero')
            output_path = os.path.join(get_base_path(), "outputs", f"Guia Fase_{nfe_numero}.pdf")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(pdf_decoded)
            
            self.after(0, self.hide_loading_indicator)
            messagebox.showinfo("Sucesso", f"Guia Fase emitida e salva com sucesso em:\n{os.path.abspath(output_path)}")

        except requests.exceptions.RequestException as e:
            error_message = f"Falha na comunicação com a API: {e}"
            if e.response is not None:
                try:
                    error_message += f"\n\nDetalhes: {e.response.json()}"
                except json.JSONDecodeError:
                    error_message += f"\n\nDetalhes: {e.response.text}"
            self.after(0, self.hide_loading_indicator)
            messagebox.showerror("Erro de Rede", error_message)
        except Exception as e:
            self.after(0, self.hide_loading_indicator)
            messagebox.showerror("Erro na Emissão", f"Ocorreu um erro durante a emissão da guia: {e}")

    def check_emission_thread(self):
        """Verifica se a thread de emissão terminou."""
        if self.emission_thread.is_alive():
            self.after(100, self.check_emission_thread)
        else:
            self.hide_loading_indicator()

    def _refresh_cultivar_data(self):
        """Executa o script get_cultivares.py e recarrega os dados de cultivares."""
        self.show_loading_indicator("Atualizando dados de cultivares... Isso pode levar alguns segundos.")
        refresh_thread = threading.Thread(target=self._run_get_cultivares_script)
        refresh_thread.start()
        self.after(100, self._check_refresh_thread, refresh_thread)

    def _run_get_cultivares_script(self):
        """Atualiza a base de cultivares em processo (funciona tambem no executavel).

        Executa get_cultivares.run_atualizacao(), que le X-TOKEN e URL_GUIA_FASE
        do ambiente ja descriptografado por decrypt_and_load_env().
        """
        try:
            import get_cultivares
            get_cultivares.run_atualizacao()

            # Apos a atualizacao, recarrega os dados na interface.
            self.after(0, self.load_initial_data)
            self.after(0, messagebox.showinfo, "Sucesso", "Dados de cultivares atualizados com sucesso!")
        except Exception as e:
            self.after(0, messagebox.showerror, "Erro", f"Ocorreu um erro ao atualizar os dados de cultivares: {e}")

    def _check_refresh_thread(self, thread):
        """Verifica se a thread de atualização terminou."""
        if thread.is_alive():
            self.after(100, self._check_refresh_thread, thread)
        else:
            self.hide_loading_indicator()

    def update_loading_message(self, message):
        """Atualiza a mensagem na janela de carregamento."""
        if hasattr(self, 'loading_window') and self.loading_window.winfo_exists():
            for widget in self.loading_window.winfo_children():
                if isinstance(widget, ttk.Label):
                    widget.config(text=message)
                    break

    def extract_nfe_data_from_xml(self, filepath):
        """Extrai número, série e data de um arquivo XML de NF-e."""
        try:
            if not os.path.exists(filepath):
                messagebox.showerror("Erro", f"O arquivo XML {filepath} não foi encontrado.")
                return None

            tree = ET.parse(filepath)
            root = tree.getroot()
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            
            ide = root.find('.//nfe:ide', ns)
            serie = ide.find('nfe:serie', ns).text
            numero = ide.find('nfe:nNF', ns).text
            data_emissao_str = ide.find('nfe:dhEmi', ns).text
            data = data_emissao_str.split('T')[0]

            return {"serie": serie, "numero": numero, "data": data}
        except Exception as e:
            messagebox.showerror("Erro ao Ler XML", f"Não foi possível extrair os dados da NF-e do arquivo XML.\n\nErro: {e}")
            return None

    def enviar_softsul(self):
        """Função para o botão 'Enviar ao SoftSul'."""
        nf = self.nf_path_softsul.get()
        guia = self.guia_path_softsul.get()
        if not nf or not guia:
            messagebox.showerror("Erro", "Por favor, selecione uma NF para vincular os arquivos antes de enviar.")
            self.log_softsul("ERRO: Tentativa de envio sem arquivos vinculados.")
            return
        
        self.log_softsul("="*60)
        self.log_softsul(f"Iniciando envio para SoftSul...")
        self.log_softsul(f"NF: {os.path.basename(nf)}")
        self.log_softsul(f"Guia: {os.path.basename(guia)}")
        self.log_softsul("Envio concluído com sucesso!")
        self.log_softsul("="*60)
        messagebox.showinfo("Sucesso", "Arquivos enviados para SoftSul com sucesso!")

    def add_item(self):
        """Adiciona uma nova linha editável à tabela de itens."""
        default_values = (
            "Novo Produto",
            "",
            0,
            "",
            0,
            "",
            0.0
        )
        new_item_id = self.tree_itens.insert('', 'end', values=default_values)
        self.update_peso_bruto_subtotal()
        self.tree_itens.selection_set(new_item_id)
        self.tree_itens.focus(new_item_id)
        self.open_edit_item_window(None)

    def remove_item(self):
        """Remove o item selecionado da tabela."""
        selected_item = self.tree_itens.selection()
        if not selected_item:
            messagebox.showwarning("Remover Item", "Por favor, selecione um item para remover.")
            return
        if messagebox.askyesno("Confirmar Remoção", "Tem certeza que deseja remover o item selecionado?"):
            self.tree_itens.delete(selected_item)
            self.update_peso_bruto_subtotal()

    def open_edit_item_window(self, event):
        """Abre uma janela para editar o item selecionado."""
        selected_item_id = self.tree_itens.focus()
        if not selected_item_id:
            return

        item_data = self.tree_itens.item(selected_item_id, 'values')

        edit_window = ttk.Toplevel(self)
        edit_window.title("Editar Item")
        edit_window.geometry("500x350")
        edit_window.transient(self)
        edit_window.grab_set()

        content_frame = ttk.Frame(edit_window, padding=20)
        content_frame.pack(expand=True, fill='both')
        content_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(content_frame, text="Cultura (Categoria):").grid(row=0, column=0, sticky='w', pady=5)
        cultura_combo = ttk.Combobox(content_frame, state='readonly', values=self.cultura_list, bootstyle="success")
        cultura_combo.grid(row=0, column=1, sticky='ew', padx=10)

        ttk.Label(content_frame, text="Lote:").grid(row=1, column=0, sticky='w', pady=5)
        lote_entry = ttk.Entry(content_frame)
        lote_entry.grid(row=1, column=1, sticky='ew', padx=10)

        ttk.Label(content_frame, text="Peso Bruto:").grid(row=2, column=0, sticky='w', pady=5)
        peso_bruto_entry = ttk.Entry(content_frame)
        peso_bruto_entry.grid(row=2, column=1, sticky='ew', padx=10)

        ttk.Label(content_frame, text="Filtrar Cultivar:").grid(row=3, column=0, sticky='w', pady=5)
        cultivar_filter_entry = ttk.Entry(content_frame)
        cultivar_filter_entry.grid(row=3, column=1, sticky='ew', padx=10)

        cultivar_tree_frame = ttk.Frame(content_frame)
        cultivar_tree_frame.grid(row=4, column=0, columnspan=2, sticky='nsew', pady=(10, 0))
        cultivar_tree_frame.grid_columnconfigure(0, weight=1)
        cultivar_tree_frame.grid_rowconfigure(0, weight=1)

        cultivar_tree = ttk.Treeview(cultivar_tree_frame, columns=("Cód. Cultivar", "Nome Cultivar"), show='headings', height=5)
        cultivar_tree.heading("Cód. Cultivar", text="Cód. Cultivar")
        cultivar_tree.heading("Nome Cultivar", text="Nome Cultivar")
        cultivar_tree.column("Cód. Cultivar", width=100, anchor='center')
        cultivar_tree.column("Nome Cultivar", width=300, anchor='w')
        cultivar_tree.grid(row=0, column=0, sticky='nsew')

        cultivar_scrollbar = ttk.Scrollbar(cultivar_tree_frame, orient='vertical', command=cultivar_tree.yview)
        cultivar_tree.configure(yscrollcommand=cultivar_scrollbar.set)
        cultivar_scrollbar.grid(row=0, column=1, sticky='ns')

        selected_cultivar_label = ttk.Label(content_frame, text="Cultivar Selecionada: ")
        selected_cultivar_label.grid(row=5, column=0, columnspan=2, sticky='w', pady=5)

        selected_cultivar_code = tk.StringVar()
        selected_cultivar_name = tk.StringVar()

        def update_cultivar_tree(*args):
            cultivar_tree.delete(*cultivar_tree.get_children())
            selected_cultura_nome = cultura_combo.get()
            selected_cultura_codigo = self.culturas_map.get(selected_cultura_nome)
            filter_text = cultivar_filter_entry.get().upper()

            if selected_cultura_codigo:
                cultivar_options = self.cultivares_df[self.cultivares_df['CULTURA_CODIGO'] == selected_cultura_codigo]
                if not cultivar_options.empty:
                    for _, row in cultivar_options.iterrows():
                        if filter_text in str(row['CULTIVAR_DESCRICAO']).upper() or filter_text in str(row['CULTIVAR_CODIGO']):
                            cultivar_tree.insert("", "end", values=(row['CULTIVAR_CODIGO'], row['CULTIVAR_DESCRICAO']))

        def on_cultivar_select(event):
            selected_item = cultivar_tree.selection()
            if selected_item:
                item = cultivar_tree.item(selected_item)
                selected_cultivar_code.set(item['values'][0])
                selected_cultivar_name.set(item['values'][1])
                selected_cultivar_label.config(text=f"Cultivar Selecionada: {item['values'][1]} (Cód: {item['values'][0]})")

        cultura_combo.bind("<<ComboboxSelected>>", update_cultivar_tree)
        cultivar_filter_entry.bind("<KeyRelease>", update_cultivar_tree)
        cultivar_tree.bind("<<TreeviewSelect>>", on_cultivar_select)

        current_cultura_codigo = int(item_data[4])
        for nome, codigo in self.culturas_map.items():
            if codigo == current_cultura_codigo:
                cultura_combo.set(nome)
                break
        
        update_cultivar_tree()

        lote_entry.insert(0, str(item_data[5]))
        peso_bruto_entry.insert(0, str(item_data[6]))

        def save_changes():
            new_cultura_nome = cultura_combo.get()
            new_cultura_codigo = self.culturas_map.get(new_cultura_nome)
            
            new_cultivar_descricao = selected_cultivar_name.get()
            new_cultivar_codigo = selected_cultivar_code.get()

            if not new_cultivar_descricao or not new_cultivar_codigo:
                messagebox.showerror("Erro", "Por favor, selecione uma cultivar da lista.")
                return

            new_lote = lote_entry.get()
            new_peso_bruto = float(peso_bruto_entry.get())

            self.tree_itens.item(selected_item_id, values=(
                item_data[0], item_data[1], 
                new_cultivar_codigo, new_cultivar_descricao, 
                new_cultura_codigo, 
                new_lote, new_peso_bruto
            ))
            self.update_peso_bruto_subtotal()
            edit_window.destroy()

        save_button = ttk.Button(content_frame, text="Salvar", command=save_changes, bootstyle="success")
        save_button.grid(row=7, column=0, columnspan=2, pady=20)

    def prompt_for_nfe_data(self):
        """Abre um diálogo para o usuário inserir o número da NFe manualmente."""
        dialog = ttk.Toplevel(self)
        dialog.title("Número da NF-e (QAS)")
        dialog.geometry("300x150")
        dialog.transient(self)
        dialog.grab_set()

        content_frame = ttk.Frame(dialog, padding=20)
        content_frame.pack(expand=True, fill='both')

        nfe_data = {}

        ttk.Label(content_frame, text="Número:").grid(row=0, column=0, sticky='w', pady=5)
        numero_entry = ttk.Entry(content_frame)
        numero_entry.grid(row=0, column=1, sticky='ew', padx=10)
        numero_entry.focus()

        def on_ok():
            nfe_data['numero'] = numero_entry.get()
            nfe_data['serie'] = "87"
            nfe_data['data'] = datetime.now().strftime('%Y-%m-%d')
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        ok_button = ttk.Button(content_frame, text="OK", command=on_ok, bootstyle="success")
        ok_button.grid(row=1, column=0, pady=20)

        cancel_button = ttk.Button(content_frame, text="Cancelar", command=on_cancel, bootstyle="secondary")
        cancel_button.grid(row=1, column=1, pady=20)

        self.wait_window(dialog)
        return nfe_data

    def load_xml_data(self, filepath):
        """Carrega e exibe os dados do arquivo XML selecionado e popula a tabela de itens."""
        if not os.path.exists(filepath):
            messagebox.showerror("Erro", f"O arquivo {filepath} não foi encontrado.")
            return

        self.show_loading_indicator("Carregando dados do XML...")
        self.result_queue = queue.Queue()
        self.thread = threading.Thread(target=self._load_xml_data_thread, args=(filepath,))
        self.thread.start()
        self.after(100, self.check_thread)

    def check_thread(self):
        """Verifica se a thread terminou e atualiza a UI."""
        try:
            result = self.result_queue.get(0)
            self.hide_loading_indicator()
            if isinstance(result, Exception):
                messagebox.showerror("Erro de Leitura", f"Não foi possível ler o arquivo: {result}")
            else:
                destinatario_nome = result.get('destinatario_nome', 'Não encontrado')
                destinatario_mun = result.get('destinatario_mun', '')
                display_text = f"{destinatario_nome} - {destinatario_mun}" if destinatario_mun else destinatario_nome
                self.nfe_destinatario_label.config(text=display_text)

                itens_agrupados = result.get('itens', {})
                for item in self.tree_itens.get_children():
                    self.tree_itens.delete(item)
                for i, item in enumerate(itens_agrupados.values()):
                    tag = 'oddrow' if i % 2 else 'evenrow'
                    self.tree_itens.insert('', 'end', values=(
                        item['xProd'],
                        item['cProd'], 
                        item['cod_cultivar'],
                        item['cultivar_descricao'],
                        item['cod_cultura'],
                        item['lote'], 
                        item['peso_bruto']
                    ), tags=(tag,))
                self.update_peso_bruto_subtotal()
        except queue.Empty:
            self.after(100, self.check_thread)

    def _load_xml_data_thread(self, selected_file):
        try:
            if self.cultivares_df is None:
                raise Exception("O DataFrame de cultivares não foi carregado corretamente.")

            tree = ET.parse(selected_file)
            root = tree.getroot()
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            
            itens_agrupados = {}
            
            for det in root.findall('.//nfe:det', ns):
                prod = det.find('.//nfe:prod', ns)
                cProd = prod.find('nfe:cProd', ns).text
                vUnCom_text = prod.find('nfe:vUnCom', ns).text
                xProd = prod.find('nfe:xProd', ns).text

                peso_bruto = float(vUnCom_text)

                lote = "Não Informado"
                peso_bruto = 0.0
                infAdProd = det.find('nfe:infAdProd', ns)
                
                if infAdProd is not None and infAdProd.text:
                    infAdProd_text = infAdProd.text
                    
                    if "LT:" in infAdProd_text:
                        lote_start = infAdProd_text.find("LT:") + 3
                        lote_end = infAdProd_text.find(" ", lote_start)
                        if lote_end == -1:
                            lote = infAdProd_text[lote_start:].strip()
                        else:
                            lote = infAdProd_text[lote_start:lote_end].strip()
                            
                    if "Peso LT:" in infAdProd_text:
                        peso_lt_start = infAdProd_text.find("Peso LT:") + len("Peso LT:")
                        peso_lt_end = infAdProd_text.find("/", peso_lt_start)
                        if peso_lt_end == -1:
                            peso_lt_end = len(infAdProd_text)
                        peso_lt_str = infAdProd_text[peso_lt_start:peso_lt_end].strip().replace('.', '').replace(',', '.')
                        try:
                            peso_bruto = float(peso_lt_str)
                        except ValueError:
                            peso_bruto = 0.0
                
                if peso_bruto == 0.0:
                    vUnCom_text = prod.find('nfe:vUnCom', ns).text
                    try:
                        peso_bruto = float(vUnCom_text)
                    except ValueError:
                        peso_bruto = 0.0

                if lote == "Não Informado" and "LT:" in xProd:
                    lote_start = xProd.find("LT:") + 3
                    lote_end = xProd.find(" ", lote_start)
                    if lote_end == -1:
                        lote = xProd[lote_start:].strip()
                    else:
                        lote = xProd[lote_start:lote_end].strip()
                
                cod_cultivar, cod_cultura, cultivar_descricao = self.buscar_codigos_cultivar(xProd, self.cultivares_df)
                
                chave_agrupamento = f"{cProd}_{lote}"
                
                if chave_agrupamento in itens_agrupados:
                    itens_agrupados[chave_agrupamento]['peso_bruto'] += peso_bruto
                else:
                    itens_agrupados[chave_agrupamento] = {
                        'xProd': xProd,
                        'cProd': cProd,
                        'lote': lote,
                        'peso_bruto': peso_bruto,
                        'cod_cultivar': cod_cultivar,
                        'cod_cultura': cod_cultura,
                        'cultivar_descricao': cultivar_descricao
                    }
            
            dest_nome = "Não encontrado"
            dest_mun = ""
            dest = root.find('.//nfe:dest', ns)
            if dest is not None:
                xNome_tag = dest.find('nfe:xNome', ns)
                if xNome_tag is not None:
                    dest_nome = xNome_tag.text
                
                enderDest = dest.find('nfe:enderDest', ns)
                if enderDest is not None:
                    xMun_tag = enderDest.find('nfe:xMun', ns)
                    if xMun_tag is not None:
                        dest_mun = xMun_tag.text

            result_data = {
                'itens': itens_agrupados,
                'destinatario_nome': dest_nome,
                'destinatario_mun': dest_mun
            }
            self.result_queue.put(result_data)

        except Exception as e:
            self.result_queue.put(e)

    def show_loading_indicator(self, message="Carregando dados, por favor aguarde..."):
        """Mostra um indicador de carregamento."""
        self.loading_window = ttk.Toplevel(self)
        self.loading_window.transient(self)
        self.loading_window.grab_set()
        self.loading_window.title("Carregando...")
        self.loading_window.geometry("400x120")
        
        label = ttk.Label(self.loading_window, text=message, wraplength=380) # Added wraplength
        label.pack(expand=True, pady=20)
        
        self.loading_window.update()

    def hide_loading_indicator(self):
        """Esconde o indicador de carregamento."""
        if hasattr(self, 'loading_window') and self.loading_window.winfo_exists():
            self.loading_window.destroy()

    def normalizar_texto(self, texto):
        """Remove espaços, converte para maiúscula e remove caracteres especiais para comparação."""
        if not texto:
            return ""
        texto_normalizado = texto.replace(" ", "").upper()
        caracteres_remover = ["(", ")", "-", ".", ",", "/", "_"]
        for char in caracteres_remover:
            texto_normalizado = texto_normalizado.replace(char, "")
        return texto_normalizado

    def buscar_codigos_cultivar(self, nome_produto, cultivares_df):
        """Busca os códigos de cultivar e cultura baseado no nome do produto."""
        try:
            nome_normalizado = self.normalizar_texto(nome_produto)
            
            for _, row in cultivares_df.iterrows():
                cultivar_descricao = str(row['CULTIVAR_DESCRICAO'])
                cultivar_normalizada = self.normalizar_texto(cultivar_descricao)
                
                if cultivar_normalizada and cultivar_normalizada in nome_normalizado:
                    return int(row['CULTIVAR_CODIGO']), int(row['CULTURA_CODIGO']), cultivar_descricao
            
            return 0, 0, ""
        except Exception as e:
            print(f"Erro ao buscar códigos de cultivar: {e}")
            return 0, 0, ""

    def update_nf_list_softsul(self):
        """Atualiza a lista de NFs na aba 'Enviar para SoftSul'."""
        try:
            nf_files = ["NF 85576", "NF 20901"]
            if nf_files:
                self.nf_combo_softsul['values'] = nf_files
                self.nf_combo_softsul.set(f"Selecione uma NF ({len(nf_files)} disponíveis)")
            else:
                self.nf_combo_softsul['values'] = ["Nenhuma NF encontrada"]
                self.nf_combo_softsul.set("Nenhuma NF encontrada")
        except Exception as e:
            self.nf_combo_softsul['values'] = ["Erro ao buscar NFs"]
            self.nf_combo_softsul.set("Erro ao buscar NFs")
            self.log_softsul(f"Erro ao buscar NFs: {e}")

    def link_files_softsul(self, event=None):
        """Vincula os arquivos XML e PDF baseados na NF selecionada."""
        selected_nf = self.nf_combo_softsul.get()
        if not selected_nf or not selected_nf.startswith("NF"):
            return
        
        nf_number = selected_nf.split(" ")[1]
        
        if nf_number == "85576":
            xml_filename = "51250903306578001998550010000855761146437899.xml"
        elif nf_number == "20901":
            xml_filename = "52250903306578006108550010000209011645903058.xml"
        else:
            xml_filename = ""

        pdf_filename = xml_filename.replace('.xml', '.pdf') if xml_filename else ""

        if os.path.exists(xml_filename) and os.path.exists(pdf_filename):
            self.nf_path_softsul.set(os.path.abspath(xml_filename))
            self.guia_path_softsul.set(os.path.abspath(pdf_filename))
            self.log_softsul(f"NF '{selected_nf}' selecionada.")
            self.log_softsul(f"XML vinculado: {os.path.basename(xml_filename)}")
            self.log_softsul(f"PDF vinculado: {os.path.basename(pdf_filename)}")
        elif not os.path.exists(xml_filename):
            self.nf_path_softsul.set("")
            self.guia_path_softsul.set("")
            self.log_softsul(f"ERRO: Arquivo XML para a NF '{selected_nf}' não encontrado.")
            messagebox.showerror("Arquivo não encontrado", f"Não foi possível encontrar o arquivo XML para a NF {nf_number}.")
        else:
            self.nf_path_softsul.set(os.path.abspath(xml_filename))
            self.guia_path_softsul.set("")
            self.log_softsul(f"NF '{selected_nf}' selecionada.")
            self.log_softsul(f"XML vinculado: {os.path.basename(xml_filename)}")
            self.log_softsul(f"AVISO: Arquivo PDF para a NF '{selected_nf}' não encontrado.")
            messagebox.showwarning("Arquivo não encontrado", f"O arquivo XML foi encontrado, mas não foi possível encontrar o arquivo PDF correspondente para a NF {nf_number}.")

    def update_peso_bruto_subtotal(self):
        """Calcula e atualiza o subtotal do Peso Bruto."""
        total_peso_bruto = 0.0
        for item_id in self.tree_itens.get_children():
            item_values = self.tree_itens.item(item_id, 'values')
            try:
                total_peso_bruto += float(item_values[6])
            except (ValueError, IndexError):
                pass
        self.peso_bruto_subtotal_label.config(text=f"Total Peso Bruto: {total_peso_bruto:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    def on_closing(self):
        """Handler para fechar a aplicação de forma segura."""
        if messagebox.askokcancel("Sair", "Deseja sair do FatFlow?"):
            if self.scraper:
                print("Fechando o scraper...")
                threading.Thread(target=self.scraper.close).start()
            self.destroy()    

    def update_local_nf_list(self):
        """Verifica a pasta 'outputs' e atualiza o combobox com as NFs encontradas."""
        try:
            output_path = os.path.join(get_base_path(), "outputs")
            if not os.path.exists(output_path):
                os.makedirs(output_path)
            
            nf_files = [f for f in os.listdir(output_path) if f.startswith("NF_") and f.endswith(".xml")]
            
            if nf_files:
                self.local_nf_combo['values'] = nf_files
                self.local_nf_combo.set(f"{len(nf_files)} NFs encontradas. Selecione uma.")
            else:
                self.local_nf_combo['values'] = []
                self.local_nf_combo.set("Nenhuma NF local encontrada.")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível listar as NFs locais: {e}")

    def update_pdf_list_tab3(self):
        """Verifica a pasta 'outputs' e atualiza a Treeview com os PDFs encontrados."""
        try:
            output_path = os.path.join(get_base_path(), "outputs")
            if not os.path.exists(output_path):
                os.makedirs(output_path)
            
            pdf_files = [f for f in os.listdir(output_path) if f.endswith(".pdf")]
            
            # Clear existing items
            self.pdf_tree.delete(*self.pdf_tree.get_children())

            self.pdf_selection_state = {}
            self.tipo_options = ["mdfe", "guia-fase", "mapa", "cte", "nfe", "canhoto", "roteiro", "ckl"]

            if pdf_files:
                for pdf_file in pdf_files:
                    if not pdf_file:
                        continue
                    file_path = os.path.join(output_path, pdf_file)
                    initial_tipo = "nfe"
                    if "guia fase" in pdf_file.lower():
                        initial_tipo = "guia-fase"
                    self.pdf_tree.insert('', 'end', iid=file_path, values=("", pdf_file, initial_tipo))
                    self.pdf_selection_state[file_path] = {'selected': False, 'tipo': initial_tipo}
            else:
                self.pdf_tree.insert('', 'end', values=("", "Nenhum PDF encontrado.", ""))
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível listar os PDFs: {e}")
            self.softsul_log_text.config(state='normal')
            self.softsul_log_text.insert(tk.END, f"ERRO: {e}\n")
            self.softsul_log_text.config(state='disabled')

    def on_pdf_tree_click(self, event):
        """Lida com cliques na Treeview de PDFs para seleção e edição de tipo."""
        item_id = self.pdf_tree.identify_row(event.y)
        if not item_id or item_id not in self.pdf_selection_state: # Check if it's a valid item and not the placeholder
            return

        column = self.pdf_tree.identify_column(event.x)
        current_values = self.pdf_tree.item(item_id, 'values')

        if column == '#1':  # Clicked on the checkbox column
            current_state = self.pdf_selection_state[item_id]['selected']
            new_state = not current_state
            self.pdf_selection_state[item_id]['selected'] = new_state
            checkbox_text = "X" if new_state else ""
            self.pdf_tree.item(item_id, values=(checkbox_text, current_values[1], current_values[2]))
            if new_state:
                self.pdf_tree.item(item_id, tags=('selected_pdf',))
            else:
                self.pdf_tree.item(item_id, tags=('',))
        elif column == '#3': # Clicked on the 'Tipo' column
            x, y, width, height = self.pdf_tree.bbox(item_id, column)
            
            # Create a temporary combobox for editing
            combo = ttk.Combobox(self.pdf_tree, values=self.tipo_options, state="readonly", bootstyle="success")
            combo.set(current_values[2])
            combo.place(x=x, y=y, width=width, height=height)
            combo.focus_set()

            def on_combobox_selected(event):
                new_tipo = combo.get()
                self.pdf_selection_state[item_id]['tipo'] = new_tipo
                self.pdf_tree.item(item_id, values=(current_values[0], current_values[1], new_tipo))
                combo.destroy()
                self.pdf_tree.update_idletasks()

            def on_focus_out(event):
                combo.destroy()
                self.pdf_tree.update_idletasks()

            combo.bind("<<ComboboxSelected>>", on_combobox_selected)
            combo.bind("<FocusOut>", on_focus_out)

    def send_to_softsul(self):
        """Envia os PDFs selecionados para a API da SoftSul."""
        carga_web = self.carga_web_softsul_entry.get().strip()
        if not carga_web:
            messagebox.showerror("Erro", "Por favor, preencha o campo 'Carga Web'.")
            self.log_softsul("ERRO: Campo 'Carga Web' vazio.")
            return

        selected_pdfs = []
        for file_path, state in self.pdf_selection_state.items():
            if state['selected']:
                selected_pdfs.append({'path': file_path, 'tipo': state['tipo']})
        
        if not selected_pdfs:
            messagebox.showwarning("Aviso", "Nenhum arquivo PDF selecionado para envio.")
            self.log_softsul("AVISO: Nenhum PDF selecionado.")
            return

        self.log_softsul("="*60)
        self.log_softsul(f"Iniciando envio de {len(selected_pdfs)} PDF(s) para SoftSul (Carga Web: {carga_web})...")
        self.show_loading_indicator("Enviando PDFs para SoftSul...")

        self.send_thread = threading.Thread(target=self._send_to_softsul_thread, args=(carga_web, selected_pdfs))
        self.send_thread.start()
        self.after(100, self.check_send_thread)

    def _send_to_softsul_thread(self, carga_web, selected_pdfs):
        """Executa o envio dos PDFs em uma thread separada."""
        try:
            # Load credentials from encrypted .env file
            decrypt_and_load_env()
            
            username_ss = os.getenv("USERNAME_SS")
            pass_ss = os.getenv("PASS_SS")
            
            if not username_ss or not pass_ss:
                raise Exception("Credenciais SoftSul (USERNAME_SS, PASS_SS) não encontradas no arquivo .env ou vazias.")

            auth_string = f"{username_ss}:{pass_ss}"
            encoded_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Basic {encoded_auth}'
            }

            payload_items = []
            for i, pdf_info in enumerate(selected_pdfs):
                self.after(0, self.update_loading_message, f"Processando PDF {i+1}/{len(selected_pdfs)}: {os.path.basename(pdf_info['path'])}")
                with open(pdf_info['path'], 'rb') as pdf_file:
                    encoded_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
                
                payload_items.append({
                    "extensao": "pdf",
                    "base64": encoded_pdf,
                    "tipo": pdf_info['tipo'],
                    "nome": os.path.basename(pdf_info['path'])
                })
            
            url = f'https://vig.softsul.agr.br/api/v1/sementes/cargas/{carga_web}/arquivos'
            response = requests.post(url, headers=headers, json=payload_items)
            response.raise_for_status() # Raise an exception for HTTP errors

            response_json = response.json()
            self.after(0, self.hide_loading_indicator)
            self.after(0, messagebox.showinfo, "Sucesso", response_json.get("message", "PDF(s) enviado(s) para SoftSul com sucesso!"))
            
            self.log_softsul("Envio concluído com sucesso!")
            self.log_softsul(f"Mensagem da API: {response_json.get('message', 'N/A')}")
            if "data" in response_json and isinstance(response_json["data"], list):
                for item in response_json["data"]:
                    self.log_softsul(f"  - Arquivo: {item.get('nome', 'N/A')}, ID: {item.get('id', 'N/A')}, Link: {item.get('link', 'N/A')}")
            self.log_softsul("="*60)

        except requests.exceptions.RequestException as e:
            error_message = f"Falha na comunicação com a API da SoftSul: {e}"
            if e.response is not None:
                try:
                    error_message += f"\n\nDetalhes: {e.response.json()}"
                except json.JSONDecodeError:
                    error_message += f"\n\nDetalhes: {e.response.text}"
            self.after(0, self.hide_loading_indicator)
            self.after(0, messagebox.showerror, "Erro de Rede", error_message)
            self.log_softsul(f"ERRO de Rede: {error_message}")
        except Exception as e:
            self.after(0, self.hide_loading_indicator)
            self.after(0, messagebox.showerror, "Erro no Envio", f"Ocorreu um erro durante o envio dos PDFs: {e}")
            self.log_softsul(f"ERRO no Envio: {e}")

    def check_send_thread(self):
        """Verifica se a thread de envio terminou."""
        if self.send_thread.is_alive():
            self.after(100, self.check_send_thread)
        else:
            self.hide_loading_indicator()

    def load_selected_local_nf(self):
        """Carrega os dados do XML selecionado no combobox."""
        selected_file = self.local_nf_combo.get()
        if not selected_file or not selected_file.endswith(".xml"):
            messagebox.showwarning("Aviso", "Por favor, selecione um arquivo NF válido da lista.")
            return
        
        filepath = os.path.join(get_base_path(), "outputs", selected_file)
        self.load_xml_data(filepath)

    def download_batch_nfs(self):
        """Inicia o processo de download para múltiplas NFs inseridas no Text widget."""
        keys_str = self.nfe_keys_text.get("1.0", tk.END).strip()
        if not keys_str:
            messagebox.showwarning("Aviso", "Por favor, insira uma ou mais chaves de NF-e para baixar.")
            return
            
        nfe_keys = [key.replace(" ", "").strip() for key in keys_str.splitlines() if key.strip()]
        
        if not nfe_keys:
            messagebox.showwarning("Aviso", "Nenhuma chave de NF-e válida foi inserida.")
            return

        self.show_loading_indicator(f"Iniciando download de {len(nfe_keys)} NF(s)...")
        download_thread = threading.Thread(target=self._download_batch_nf_thread, args=(nfe_keys,))
        download_thread.start()

    def _download_batch_nf_thread(self, nfe_keys):
        """Executa o download de uma lista de chaves de NF-e em sequência."""
        try:
            if self.scraper is None or not self.scraper.is_ready:
                raise Exception("O scraper não está inicializado ou pronto.")

            total = len(nfe_keys)
            for i, key in enumerate(nfe_keys):
                self.after(0, self.update_loading_message, f"Baixando NF {i+1}/{total}:\n{key}")
                if len(key) != 44 or not key.isdigit():
                    print(f"Chave inválida pulada: {key}")
                    continue
                self.scraper.download_nfe(key)
            
            self.after(0, self.hide_loading_indicator)
            self.after(0, messagebox.showinfo, "Download Concluído", f"{total} NF(s) processada(s) com sucesso.")
            self.after(0, self.update_local_nf_list)

        except Exception as e:
            self.after(0, self.hide_loading_indicator)
            self.after(0, messagebox.showerror, "Erro no Download", f"Ocorreu um erro durante o download em lote: {e}")

    def initialize_scraper(self):
        """Inicia o scraper em uma thread separada para não bloquear a UI."""
        self.show_loading_indicator("Carregando o aplicativo... Por favor, aguarde.")
        scraper_thread = threading.Thread(target=self._initialize_scraper_thread)
        scraper_thread.start()

    def _initialize_scraper_thread(self):
        """
        Método executado na thread para criar e preparar o scraper.
        Habilita o botão de download ao finalizar.
        """
        try:
            self.scraper = OobjScraper(app=self, headless=True)
            self.scraper.prepare_for_downloads()
            self.after(0, self.hide_loading_indicator)
            self.after(0, lambda: self.download_button.config(state="normal"))
            self.after(0, messagebox.showinfo, "Carregamento Concluído", "O app está pronto.")
        except Exception as e:
            self.after(0, self.hide_loading_indicator)
            self.after(0, messagebox.showerror, "Erro ao carregar a OOBJ", f"Não foi possível inicializar a OOBJ: {e}")

def main():
    """Função principal que executa o sistema com autenticação"""
    # Carrega as credenciais (X-TOKEN, X-TOKEN-PROD, OOBJ, SoftSul) a partir do
    # arquivo criptografado antes de qualquer chamada às APIs.
    try:
        decrypt_and_load_env()
    except Exception as e:
        messagebox.showerror("Erro de configuração", f"Não foi possível carregar as credenciais:\n{e}")
        return

    app = App()
    app.withdraw()
    
    authenticated = show_login_dialog()
    
    if authenticated:
        app.deiconify()
        app.initialize_scraper()
        app.mainloop()
    else:
        app.destroy()
        print("Login cancelado ou falhou.")

if __name__ == "__main__":
    main()
