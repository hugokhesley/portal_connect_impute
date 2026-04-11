"""
=====================================================================
  PORTAL DE IMPUTE — CONNECT GROUP
  Repositório: portal_connect_impute
=====================================================================
  Sistema centralizado de cadastro de pedidos para:
  - Parceiros externos
  - Vendedores próprios
  - Líderes de equipe
  - BKO/Analistas (fila de entrada)
  - Admin (Hugo - visão total)
=====================================================================
"""

import streamlit as st
import pandas as pd
import gspread
import requests
import hashlib
import re
import smtplib
import json
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Connect Group | Portal de Impute",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─────────────────────────────────────────────────────────────────
#  CONFIGURAÇÕES
# ─────────────────────────────────────────────────────────────────

SPREADSHEET_ID  = "1HmtEFf2Akh7NLR2prxDh9S4gmioKYw419B4bkx4yBLg"
ABA_USUARIOS    = "PortalUsuarios"
ABA_PEDIDOS     = "PortalPedidos"

# Emails do BKO para notificação
EMAILS_BKO = [
    "adm@connectgroup.solutions",
    "guthyerre.silva@connectbrasil.tech",
    "bko2@connectbrasil.tech",
]

# Hierarquia de perfis
PERFIS = {
    "admin":    {"label": "Administrador", "icon": "👑"},
    "bko":      {"label": "BKO / Analista", "icon": "📋"},
    "lider":    {"label": "Líder de Equipe", "icon": "👥"},
    "parceiro": {"label": "Parceiro Externo", "icon": "🤝"},
    "vendedor": {"label": "Vendedor",          "icon": "👤"},
}

PRODUTOS = [
    "TIM Empresas Móvel — Pós-Pago",
    "TIM Empresas Móvel — Controle",
    "TIM Empresas Fibra — 100MB",
    "TIM Empresas Fibra — 200MB",
    "TIM Empresas Fibra — 300MB",
    "TIM Empresas Fibra — 500MB",
    "TIM Empresas Fibra — 1GB",
]

TIPO_FATURA = ["Fatura Eletrônica", "Fatura Impressa"]
DIA_VENCIMENTO = [str(d) for d in range(1, 29)]

STATUS_OPCOES = [
    "Aguardando BKO",
    "BKO Assumiu",
    "Em Análise TIM",
    "Pré-venda",
    "Em Tramitação",
    "Aprovado",
    "Ativado",
    "Devolvido",
    "Cancelado",
]

STATUS_CORES = {
    "Aguardando BKO": "#94a3b8",
    "BKO Assumiu":    "#3b82f6",
    "Em Análise TIM": "#8b5cf6",
    "Pré-venda":      "#f59e0b",
    "Em Tramitação":  "#f97316",
    "Aprovado":       "#22c55e",
    "Ativado":        "#15803d",
    "Devolvido":      "#ef4444",
    "Cancelado":      "#dc2626",
}

# ─────────────────────────────────────────────────────────────────
#  ESTILO
# ─────────────────────────────────────────────────────────────────

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .stApp { background-color: #f1f5f9; color: #1e293b; }

  /* Força inputs com fundo branco e texto escuro */
  input[type="text"], input[type="password"], input[type="number"],
  textarea, .stTextInput input, .stTextArea textarea,
  .stNumberInput input, .stSelectbox select,
  div[data-baseweb="input"] input,
  div[data-baseweb="textarea"] textarea {
    background-color: #ffffff !important;
    color: #1e293b !important;
    border: 1px solid #cbd5e1 !important;
  }

  /* Labels dos inputs */
  .stTextInput label, .stTextArea label, .stNumberInput label,
  .stSelectbox label, .stDateInput label {
    color: #374151 !important;
    font-weight: 500 !important;
  }

  /* Selectbox */
  div[data-baseweb="select"] div {
    background-color: #ffffff !important;
    color: #1e293b !important;
  }

  .header-portal {
    background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
    border-radius: 16px; padding: 22px 32px; margin-bottom: 24px;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 4px 24px rgba(15,32,39,0.3);
  }
  .header-title { font-size: 1.4rem; font-weight: 800; color: #fff; margin: 0; }
  .header-sub   { font-size: 0.8rem; color: rgba(255,255,255,0.6); margin: 2px 0 0 0; }
  .header-badge { background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); border-radius: 20px; padding: 5px 14px; font-size: 0.75rem; color: #fff; font-weight: 600; }

  .kpi-card { background: #fff; border-radius: 12px; padding: 18px 22px; border: 1px solid #e2e8f0; box-shadow: 0 1px 6px rgba(0,0,0,0.04); }
  .kpi-label { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 1px; color: #94a3b8; font-weight: 600; margin-bottom: 6px; }
  .kpi-value { font-size: 1.9rem; font-weight: 800; color: #1e293b; line-height: 1; }
  .kpi-sub   { font-size: 0.7rem; color: #64748b; margin-top: 4px; }

  .pedido-card { background: #fff; border-radius: 12px; padding: 16px 20px; border: 1px solid #e2e8f0; margin-bottom: 10px; border-left: 4px solid #3b82f6; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
  .pedido-empresa { font-size: 0.95rem; font-weight: 700; color: #1e293b; }
  .pedido-info    { font-size: 0.76rem; color: #64748b; margin-top: 2px; }
  .status-badge { display: inline-block; padding: 3px 10px; border-radius: 99px; font-size: 0.7rem; font-weight: 600; color: #fff; white-space: nowrap; }

  .section-header { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 10px 16px; margin: 20px 0 14px 0; font-size: 0.8rem; font-weight: 700; color: #334155; text-transform: uppercase; letter-spacing: 0.5px; }
  .ficha-box { background: #fff; border-radius: 12px; padding: 24px; border: 1px solid #e2e8f0; margin-top: 8px; }
  .ficha-section { border-bottom: 1px solid #f1f5f9; margin-bottom: 16px; padding-bottom: 12px; }
  .ficha-title { font-size: 0.78rem; font-weight: 700; color: #3b82f6; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; }
  .ficha-field { display: flex; margin-bottom: 4px; }
  .ficha-key   { font-size: 0.78rem; color: #64748b; width: 180px; flex-shrink: 0; }
  .ficha-val   { font-size: 0.78rem; font-weight: 600; color: #1e293b; }

  .aviso-doc { background: #fefce8; border: 1px solid #fde047; border-radius: 10px; padding: 14px 18px; margin: 16px 0; font-size: 0.82rem; color: #713f12; }

  section[data-testid="stSidebar"] { background: #0f172a !important; }
  .stTabs [data-baseweb="tab-list"] { gap: 4px; }
  .stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
#  GOOGLE SHEETS
# ─────────────────────────────────────────────────────────────────

@st.cache_resource
def get_gc():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    # secrets no formato [gcp_service_account] já retorna dict direto
    creds_info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    return gspread.authorize(creds)


def get_aba(nome: str):
    gc = get_gc()
    planilha = gc.open_by_key(SPREADSHEET_ID)
    try:
        return planilha.worksheet(nome)
    except gspread.WorksheetNotFound:
        if nome == ABA_USUARIOS:
            aba = planilha.add_worksheet(title=nome, rows=200, cols=10)
            aba.update([["login","senha_hash","nome","perfil","vinculo","email","ativo","criado_em"]])
            # Cria admin padrão
            aba.append_row([
                "admin",
                hashlib.sha256("ConnectAdmin@2026".encode()).hexdigest(),
                "Hugo Khesley", "admin", "Connect Group",
                "hugo@connectgroup.solutions", "sim",
                datetime.now().strftime("%d/%m/%Y %H:%M")
            ])
        elif nome == ABA_PEDIDOS:
            aba = planilha.add_worksheet(title=nome, rows=2000, cols=50)
            aba.update([[
                # Identificação
                "id","data_cadastro","cadastrado_por","perfil_cadastrador","vinculo_cadastrador",
                # Cliente
                "cnpj","inscricao_estadual","atividade_economica","razao_social","nome_fantasia",
                "data_fundacao","capital_social","telefone_cliente","email_cliente",
                # Administrador do Contrato
                "adm_nome","adm_sobrenome","adm_cpf","adm_rg","adm_email","adm_telefone",
                # Endereço
                "end_cep","end_numero","end_complemento","end_logradouro","end_bairro","end_estado","end_cidade",
                # Entrega
                "ent_cep","ent_numero","ent_complemento","ent_logradouro","ent_bairro","ent_estado","ent_cidade","ent_ponto_ref","ent_sabado","ent_hora_ini","ent_hora_fim",
                # Faturamento
                "fat_tipo","fat_dia_vencimento","fat_email",
                # Produto
                "produto","qtd_acessos_novos",
                # Acessos Portados (JSON)
                "acessos_portados",
                # Observação TC
                "obs_tc",
                # Status e BKO
                "status","pedido_tim","bko_responsavel","data_bko_assumiu",
                "data_atualizacao","atualizado_por","obs_interna"
            ]])
        return planilha.worksheet(nome)


@st.cache_data(ttl=30, show_spinner=False)
def load_usuarios():
    dados = get_aba(ABA_USUARIOS).get_all_records()
    return pd.DataFrame(dados) if dados else pd.DataFrame()


@st.cache_data(ttl=15, show_spinner=False)
def load_pedidos():
    dados = get_aba(ABA_PEDIDOS).get_all_records()
    return pd.DataFrame(dados) if dados else pd.DataFrame()


def salvar_usuario(login, senha, nome, perfil, vinculo, email):
    aba = get_aba(ABA_USUARIOS)
    aba.append_row([
        login, hashlib.sha256(senha.encode()).hexdigest(),
        nome, perfil, vinculo, email, "sim",
        datetime.now().strftime("%d/%m/%Y %H:%M")
    ])
    st.cache_data.clear()


def gerar_id():
    aba = get_aba(ABA_PEDIDOS)
    todos = aba.get_all_values()
    return f"IMP{str(len(todos)).zfill(5)}"


def salvar_pedido(dados: dict, user: dict) -> str:
    aba   = get_aba(ABA_PEDIDOS)
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    id_p  = gerar_id()
    portados_json = json.dumps(dados.get("acessos_portados", []), ensure_ascii=False)

    aba.append_row([
        id_p, agora,
        user["login"], user["perfil"], user.get("vinculo",""),
        dados.get("cnpj",""),
        dados.get("inscricao_estadual",""),
        dados.get("atividade_economica",""),
        dados.get("razao_social",""),
        dados.get("nome_fantasia",""),
        dados.get("data_fundacao",""),
        dados.get("capital_social",""),
        dados.get("telefone_cliente",""),
        dados.get("email_cliente",""),
        dados.get("adm_nome",""),
        dados.get("adm_sobrenome",""),
        dados.get("adm_cpf",""),
        dados.get("adm_rg",""),
        dados.get("adm_email",""),
        dados.get("adm_telefone",""),
        dados.get("end_cep",""),
        dados.get("end_numero",""),
        dados.get("end_complemento",""),
        dados.get("end_logradouro",""),
        dados.get("end_bairro",""),
        dados.get("end_estado",""),
        dados.get("end_cidade",""),
        dados.get("ent_cep",""),
        dados.get("ent_numero",""),
        dados.get("ent_complemento",""),
        dados.get("ent_logradouro",""),
        dados.get("ent_bairro",""),
        dados.get("ent_estado",""),
        dados.get("ent_cidade",""),
        dados.get("ent_ponto_ref",""),
        dados.get("ent_sabado","Não"),
        dados.get("ent_hora_ini",""),
        dados.get("ent_hora_fim",""),
        dados.get("fat_tipo","Fatura Eletrônica"),
        dados.get("fat_dia_vencimento","25"),
        dados.get("fat_email",""),
        dados.get("produto",""),
        dados.get("qtd_acessos_novos", 0),
        portados_json,
        dados.get("obs_tc",""),
        "Aguardando BKO", "", "", "",
        agora, user["login"], ""
    ])
    st.cache_data.clear()
    return id_p


def bko_assumir(id_pedido: str, bko_login: str):
    aba = get_aba(ABA_PEDIDOS)
    todos = aba.get_all_values()
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    for i, row in enumerate(todos):
        if row and row[0] == id_pedido:
            linha = i + 1
            aba.update_cell(linha, 46, "BKO Assumiu")      # status
            aba.update_cell(linha, 48, bko_login)           # bko_responsavel
            aba.update_cell(linha, 49, agora)               # data_bko_assumiu
            aba.update_cell(linha, 50, agora)               # data_atualizacao
            aba.update_cell(linha, 51, bko_login)           # atualizado_por
            st.cache_data.clear()
            return True
    return False


def atualizar_status_pedido(id_pedido: str, novo_status: str, pedido_tim: str, obs_interna: str, bko_login: str):
    aba = get_aba(ABA_PEDIDOS)
    todos = aba.get_all_values()
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    for i, row in enumerate(todos):
        if row and row[0] == id_pedido:
            linha = i + 1
            aba.update_cell(linha, 46, novo_status)
            aba.update_cell(linha, 47, pedido_tim)
            aba.update_cell(linha, 50, agora)
            aba.update_cell(linha, 51, bko_login)
            if obs_interna:
                aba.update_cell(linha, 52, obs_interna)
            st.cache_data.clear()
            return True
    return False


# ─────────────────────────────────────────────────────────────────
#  APIs EXTERNAS
# ─────────────────────────────────────────────────────────────────

def buscar_cnpj(cnpj: str) -> dict:
    cnpj_limpo = re.sub(r'\D', '', cnpj)
    if len(cnpj_limpo) != 14:
        return {"erro": "CNPJ deve ter 14 dígitos"}
    try:
        r = requests.get(f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}", timeout=10)
        if r.status_code == 200:
            d = r.json()
            end = f"{d.get('logradouro','')} {d.get('numero','')}".strip()
            atividade = ""
            if d.get("cnae_fiscal_descricao"):
                atividade = d["cnae_fiscal_descricao"][:50]
            return {
                "cnpj":                cnpj_limpo,
                "inscricao_estadual":  "",
                "atividade_economica": atividade,
                "razao_social":        d.get("razao_social",""),
                "nome_fantasia":       d.get("nome_fantasia","") or d.get("razao_social",""),
                "data_fundacao":       d.get("data_inicio_atividade",""),
                "capital_social":      f"R$ {d.get('capital_social', 0):,.2f}",
                "telefone":            d.get("ddd_telefone_1",""),
                "email":               d.get("email",""),
                "cep":                 re.sub(r'\D','', d.get("cep","")),
                "numero":              d.get("numero",""),
                "complemento":         d.get("complemento",""),
                "logradouro":          d.get("logradouro",""),
                "bairro":              d.get("bairro",""),
                "estado":              d.get("uf",""),
                "cidade":              d.get("municipio",""),
            }
        return {"erro": f"CNPJ não encontrado"}
    except Exception as e:
        return {"erro": str(e)}


def buscar_cep(cep: str) -> dict:
    cep_limpo = re.sub(r'\D', '', cep)
    if len(cep_limpo) != 8:
        return {"erro": "CEP inválido"}
    try:
        r = requests.get(f"https://brasilapi.com.br/api/cep/v1/{cep_limpo}", timeout=8)
        if r.status_code == 200:
            d = r.json()
            return {
                "logradouro": d.get("street",""),
                "bairro":     d.get("neighborhood",""),
                "cidade":     d.get("city",""),
                "estado":     d.get("state",""),
            }
        return {"erro": "CEP não encontrado"}
    except Exception as e:
        return {"erro": str(e)}


# ─────────────────────────────────────────────────────────────────
#  EMAIL BKO
# ─────────────────────────────────────────────────────────────────

def enviar_email_bko(id_pedido: str, dados: dict, user: dict):
    try:
        cfg = st.secrets["email"]
        portados = dados.get("acessos_portados", [])
        portados_html = ""
        if portados:
            portados_html = "<table style='border-collapse:collapse;width:100%;font-size:12px;margin-top:6px'>"
            portados_html += "<tr style='background:#3b82f6;color:#fff'><th style='padding:6px 10px;text-align:left'>Nome</th><th style='padding:6px 10px'>CPF</th><th style='padding:6px 10px'>GSM</th></tr>"
            for p in portados:
                portados_html += f"<tr><td style='padding:5px 10px;border:1px solid #e2e8f0'>{p.get('nome','')}</td><td style='padding:5px 10px;border:1px solid #e2e8f0'>{p.get('cpf','')}</td><td style='padding:5px 10px;border:1px solid #e2e8f0'>{p.get('gsm','')}</td></tr>"
            portados_html += "</table>"
        else:
            portados_html = "<i style='color:#64748b'>Nenhum acesso portado informado</i>"

        html = f"""
        <html><body style="font-family:Arial,sans-serif;color:#333;max-width:900px">
          <div style="background:linear-gradient(135deg,#0f2027,#2c5364);padding:20px 30px;border-radius:12px;margin-bottom:24px">
            <h2 style="color:#fff;margin:0">📋 Novo Pedido para Impute — {id_pedido}</h2>
            <p style="color:rgba(255,255,255,0.7);margin:6px 0 0">Cadastrado por: <b>{user['nome']}</b> ({PERFIS.get(user['perfil'],{}).get('label','')}) · {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
          </div>

          <div style="background:#fefce8;border:1px solid #fde047;border-radius:10px;padding:16px 20px;margin-bottom:20px">
            <b style="color:#713f12">📎 DOCUMENTAÇÃO NECESSÁRIA</b><br>
            <span style="font-size:13px;color:#92400e">
              O vendedor/parceiro deve enviar os documentos do cliente para este e-mail:<br>
              • Contrato Social / CNPJ<br>
              • RG e CPF do Administrador do Contrato<br>
              • Comprovante de Endereço<br>
              • Documentos dos Sócios (se necessário)
            </span>
          </div>

          <table style="border-collapse:collapse;width:100%;font-size:13px;margin-bottom:16px">
            <tr style="background:#1e3a5f;color:#fff">
              <th colspan="2" style="padding:10px 14px;text-align:left">🏢 DADOS DO CLIENTE</th>
            </tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;width:35%;font-weight:600">CNPJ</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('cnpj','')}</td></tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600">Inscrição Estadual</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('inscricao_estadual','')}</td></tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600">Atividade Econômica</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('atividade_economica','')}</td></tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600">Razão Social</td><td style="padding:7px 14px;border:1px solid #e2e8f0"><b>{dados.get('razao_social','')}</b></td></tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600">Nome Fantasia</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('nome_fantasia','')}</td></tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600">Data de Fundação</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('data_fundacao','')}</td></tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600">Capital Social</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('capital_social','')}</td></tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600">Telefone</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('telefone_cliente','')}</td></tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600">Email</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('email_cliente','')}</td></tr>
          </table>

          <table style="border-collapse:collapse;width:100%;font-size:13px;margin-bottom:16px">
            <tr style="background:#1e3a5f;color:#fff">
              <th colspan="2" style="padding:10px 14px;text-align:left">👤 ADMINISTRADOR DO CONTRATO</th>
            </tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;width:35%;font-weight:600">Nome</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('adm_nome','')} {dados.get('adm_sobrenome','')}</td></tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600">CPF</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('adm_cpf','')}</td></tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600">RG</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('adm_rg','')}</td></tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600">Email</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('adm_email','')}</td></tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600">Telefone</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('adm_telefone','')}</td></tr>
          </table>

          <table style="border-collapse:collapse;width:100%;font-size:13px;margin-bottom:16px">
            <tr style="background:#1e3a5f;color:#fff">
              <th colspan="2" style="padding:10px 14px;text-align:left">📍 ENDEREÇO / ENTREGA</th>
            </tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;width:35%;font-weight:600">Endereço</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('end_logradouro','')} {dados.get('end_numero','')} {dados.get('end_complemento','')}</td></tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600">Bairro / CEP</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('end_bairro','')} · {dados.get('end_cep','')}</td></tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600">Cidade / Estado</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('end_cidade','')} / {dados.get('end_estado','')}</td></tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600">Ponto de Referência</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('ent_ponto_ref','')}</td></tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600">Entrega aos Sábados</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('ent_sabado','Não')} · {dados.get('ent_hora_ini','')} às {dados.get('ent_hora_fim','')}</td></tr>
          </table>

          <table style="border-collapse:collapse;width:100%;font-size:13px;margin-bottom:16px">
            <tr style="background:#1e3a5f;color:#fff">
              <th colspan="2" style="padding:10px 14px;text-align:left">💳 FATURAMENTO / PRODUTO</th>
            </tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;width:35%;font-weight:600">Produto</td><td style="padding:7px 14px;border:1px solid #e2e8f0"><b>{dados.get('produto','')}</b></td></tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600">Acessos Novos</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('qtd_acessos_novos','')}</td></tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600">Tipo Fatura</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('fat_tipo','')}</td></tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600">Dia Vencimento</td><td style="padding:7px 14px;border:1px solid #e2e8f0">Dia {dados.get('fat_dia_vencimento','')}</td></tr>
            <tr><td style="padding:7px 14px;background:#f8fafc;border:1px solid #e2e8f0;font-weight:600">Email Fatura</td><td style="padding:7px 14px;border:1px solid #e2e8f0">{dados.get('fat_email','')}</td></tr>
          </table>

          <div style="margin-bottom:16px">
            <div style="background:#1e3a5f;color:#fff;padding:10px 14px;border-radius:6px 6px 0 0;font-size:13px;font-weight:700">📱 ACESSOS PORTADOS</div>
            <div style="border:1px solid #e2e8f0;border-radius:0 0 6px 6px;padding:12px 14px">{portados_html}</div>
          </div>

          {'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px 16px;font-size:13px"><b>📝 Obs. Termo de Contratação:</b><br>' + dados.get("obs_tc","") + '</div>' if dados.get("obs_tc") else ''}

          <hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0">
          <p style="font-size:11px;color:#94a3b8">Portal de Impute · Connect Group · {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
        </body></html>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[IMPUTE] Novo Pedido {id_pedido} — {dados.get('razao_social','')} · {dados.get('produto','')}"
        msg["From"]    = cfg.get("from", cfg["user"])
        msg["To"]      = ", ".join(EMAILS_BKO)
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL(cfg["host"], int(cfg["port"]), timeout=20) as sv:
            sv.login(cfg["user"], cfg["password"])
            sv.sendmail(cfg["user"], EMAILS_BKO, msg.as_string())
        return True
    except Exception as e:
        st.warning(f"⚠️ Pedido salvo, mas erro ao enviar e-mail: {e}")
        return False


# ─────────────────────────────────────────────────────────────────
#  AUTENTICAÇÃO
# ─────────────────────────────────────────────────────────────────

def autenticar(login: str, senha: str):
    h = hashlib.sha256(senha.encode()).hexdigest()

    # Admin fixo — sempre funciona independente do Sheets
    if login == "admin" and h == hashlib.sha256("ConnectAdmin@2026".encode()).hexdigest():
        return {
            "login":   "admin",
            "nome":    "Hugo Khesley",
            "perfil":  "admin",
            "vinculo": "Connect Group",
            "email":   "hugo@connectgroup.solutions",
        }

    # Demais usuários — busca na planilha
    try:
        gc = get_gc()
        planilha = gc.open_by_key(SPREADSHEET_ID)
        try:
            aba = planilha.worksheet(ABA_USUARIOS)
            dados = aba.get_all_records()
            if not dados:
                return None
            df = pd.DataFrame(dados)
            row = df[(df["login"] == login) & (df["ativo"] == "sim")]
            if row.empty:
                return None
            r = row.iloc[0]
            if r["senha_hash"] == h:
                return {
                    "login":   login,
                    "nome":    r["nome"],
                    "perfil":  r["perfil"],
                    "vinculo": r.get("vinculo",""),
                    "email":   r.get("email",""),
                }
        except gspread.WorksheetNotFound:
            return None
    except Exception:
        return None
    return None


# ─────────────────────────────────────────────────────────────────
#  COMPONENTES REUTILIZÁVEIS
# ─────────────────────────────────────────────────────────────────

def card_pedido(row, user, mostrar_acao=False, contexto=""):
    """Renderiza card de pedido."""
    cor      = STATUS_CORES.get(row.get("status",""), "#94a3b8")
    id_p     = str(row.get('id','')) + contexto
    status   = row.get('status','—')
    empresa  = row.get('razao_social','—')
    cnpj     = row.get('cnpj','—')
    produto  = row.get('produto','—')
    acessos  = row.get('qtd_acessos_novos','—')
    data     = row.get('data_cadastro','—')
    cad_por  = row.get('cadastrado_por','—')
    perfil_c = row.get('perfil_cadastrador','—')
    vinculo_c= row.get('vinculo_cadastrador','—')
    pedido_tim = row.get('pedido_tim','')
    bko_resp = row.get('bko_responsavel','')
    id_show  = row.get('id','—')

    # Monta linhas extras
    extra = ""
    if pedido_tim:
        extra += f"TIM: {pedido_tim} · "
    if bko_resp:
        extra += f"BKO: {bko_resp} · "

    # Acessos portados
    try:
        portados = json.loads(row.get("acessos_portados","[]"))
        n_port = len(portados)
    except Exception:
        n_port = 0

    html = f"""<div class="pedido-card" style="border-left-color:{cor};margin-bottom:10px">
  <div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:8px">
    <div style="flex:1;min-width:200px">
      <div class="pedido-empresa">{empresa}</div>
      <div class="pedido-info">CNPJ: {cnpj} · {produto} · {acessos} acessos novos</div>
      <div class="pedido-info">{extra}📅 {data}</div>
      <div class="pedido-info">👤 {cad_por} ({perfil_c}) · {vinculo_c}</div>
      {"<div class='pedido-info'>📱 " + str(n_port) + " acesso(s) portado(s)</div>" if n_port > 0 else ""}
    </div>
    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px">
      <span class="status-badge" style="background:{cor}">{status}</span>
      <span style="font-size:0.7rem;color:#94a3b8;font-weight:600">ID: {id_show}</span>
    </div>
  </div>
</div>"""

    if mostrar_acao:
        col_card, col_btn = st.columns([5, 1])
        with col_card:
            st.markdown(html, unsafe_allow_html=True)
        with col_btn:
            if st.button("📄 Ficha", key=f"ficha_{id_p}", use_container_width=True):
                st.session_state[f"ver_ficha_{id_p}"] = True
    else:
        st.markdown(html, unsafe_allow_html=True)

    # Ficha detalhada
    if st.session_state.get(f"ver_ficha_{id_p}"):
        with st.expander(f"📄 Ficha — {id_show}", expanded=True):
            render_ficha(row)
            if st.button("✖ Fechar", key=f"fechar_{id_p}"):
                del st.session_state[f"ver_ficha_{id_p}"]
                st.rerun()


def render_ficha(row):
    """Renderiza ficha formatada para o BKO copiar no Radar Blue."""
    portados = []
    try:
        portados = json.loads(row.get("acessos_portados","[]"))
    except Exception:
        pass

    st.markdown(f"""
    <div class="ficha-box">

      <div class="ficha-section">
        <div class="ficha-title">🏢 Dados do Cliente</div>
        <div class="ficha-field"><span class="ficha-key">CNPJ</span><span class="ficha-val">{row.get('cnpj','')}</span></div>
        <div class="ficha-field"><span class="ficha-key">Inscrição Estadual</span><span class="ficha-val">{row.get('inscricao_estadual','')}</span></div>
        <div class="ficha-field"><span class="ficha-key">Atividade Econômica</span><span class="ficha-val">{row.get('atividade_economica','')}</span></div>
        <div class="ficha-field"><span class="ficha-key">Razão Social</span><span class="ficha-val"><b>{row.get('razao_social','')}</b></span></div>
        <div class="ficha-field"><span class="ficha-key">Nome Fantasia</span><span class="ficha-val">{row.get('nome_fantasia','')}</span></div>
        <div class="ficha-field"><span class="ficha-key">Data de Fundação</span><span class="ficha-val">{row.get('data_fundacao','')}</span></div>
        <div class="ficha-field"><span class="ficha-key">Capital Social</span><span class="ficha-val">{row.get('capital_social','')}</span></div>
        <div class="ficha-field"><span class="ficha-key">Telefone</span><span class="ficha-val">{row.get('telefone_cliente','')}</span></div>
        <div class="ficha-field"><span class="ficha-key">Email</span><span class="ficha-val">{row.get('email_cliente','')}</span></div>
      </div>

      <div class="ficha-section">
        <div class="ficha-title">👤 Administrador do Contrato</div>
        <div class="ficha-field"><span class="ficha-key">Nome</span><span class="ficha-val">{row.get('adm_nome','')} {row.get('adm_sobrenome','')}</span></div>
        <div class="ficha-field"><span class="ficha-key">CPF</span><span class="ficha-val">{row.get('adm_cpf','')}</span></div>
        <div class="ficha-field"><span class="ficha-key">RG</span><span class="ficha-val">{row.get('adm_rg','')}</span></div>
        <div class="ficha-field"><span class="ficha-key">Email</span><span class="ficha-val">{row.get('adm_email','')}</span></div>
        <div class="ficha-field"><span class="ficha-key">Telefone</span><span class="ficha-val">{row.get('adm_telefone','')}</span></div>
      </div>

      <div class="ficha-section">
        <div class="ficha-title">📍 Endereço / Entrega</div>
        <div class="ficha-field"><span class="ficha-key">CEP</span><span class="ficha-val">{row.get('end_cep','')}</span></div>
        <div class="ficha-field"><span class="ficha-key">Logradouro</span><span class="ficha-val">{row.get('end_logradouro','')} {row.get('end_numero','')} {row.get('end_complemento','')}</span></div>
        <div class="ficha-field"><span class="ficha-key">Bairro</span><span class="ficha-val">{row.get('end_bairro','')}</span></div>
        <div class="ficha-field"><span class="ficha-key">Cidade / Estado</span><span class="ficha-val">{row.get('end_cidade','')} / {row.get('end_estado','')}</span></div>
        <div class="ficha-field"><span class="ficha-key">Ponto de Referência</span><span class="ficha-val">{row.get('ent_ponto_ref','')}</span></div>
        <div class="ficha-field"><span class="ficha-key">Entrega aos Sábados</span><span class="ficha-val">{row.get('ent_sabado','Não')} · {row.get('ent_hora_ini','')} às {row.get('ent_hora_fim','')}</span></div>
      </div>

      <div class="ficha-section">
        <div class="ficha-title">💳 Faturamento / Produto</div>
        <div class="ficha-field"><span class="ficha-key">Produto</span><span class="ficha-val"><b>{row.get('produto','')}</b></span></div>
        <div class="ficha-field"><span class="ficha-key">Acessos Novos</span><span class="ficha-val">{row.get('qtd_acessos_novos','')}</span></div>
        <div class="ficha-field"><span class="ficha-key">Tipo Fatura</span><span class="ficha-val">{row.get('fat_tipo','')}</span></div>
        <div class="ficha-field"><span class="ficha-key">Dia Vencimento</span><span class="ficha-val">Dia {row.get('fat_dia_vencimento','')}</span></div>
        <div class="ficha-field"><span class="ficha-key">Email Fatura</span><span class="ficha-val">{row.get('fat_email','')}</span></div>
      </div>

      {'<div class="ficha-section"><div class="ficha-title">📱 Acessos Portados</div>' + ''.join([f"<div class='ficha-field'><span class='ficha-key'>{p.get('nome','')}</span><span class='ficha-val'>CPF: {p.get('cpf','')} · GSM: {p.get('gsm','')}</span></div>" for p in portados]) + '</div>' if portados else ''}

      {'<div class="ficha-section"><div class="ficha-title">📝 Obs. Termo de Contratação</div><div style="font-size:0.82rem;color:#1e293b">' + row.get("obs_tc","") + '</div></div>' if row.get("obs_tc") else ''}

    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="aviso-doc">
      📎 <b>Documentação necessária do cliente:</b><br>
      Solicite ao vendedor/parceiro que envie para <b>adm@connectgroup.solutions</b>, <b>guthyerre.silva@connectbrasil.tech</b> e <b>bko2@connectbrasil.tech</b>:<br>
      • Contrato Social / CNPJ · RG e CPF do Administrador · Comprovante de Endereço · Documentos dos Sócios
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
#  FORMULÁRIO DE CADASTRO DE PEDIDO
# ─────────────────────────────────────────────────────────────────

def form_novo_pedido(user):
    st.markdown('<div class="section-header">🔍 BUSCAR CLIENTE PELO CNPJ</div>', unsafe_allow_html=True)

    col_cnpj, col_btn = st.columns([3, 1])
    with col_cnpj:
        cnpj_input = st.text_input("CNPJ do Cliente", placeholder="00.000.000/0000-00", key="form_cnpj")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔍 Buscar na Receita Federal", use_container_width=True, key="btn_buscar_cnpj"):
            with st.spinner("Consultando Receita Federal..."):
                dados = buscar_cnpj(cnpj_input)
            if "erro" in dados:
                st.error(f"❌ {dados['erro']}")
            else:
                st.session_state.form_cnpj_dados = dados
                st.success(f"✅ **{dados['razao_social']}** encontrado!")

    c = st.session_state.get("form_cnpj_dados", {})
    if not c:
        st.info("Digite o CNPJ e clique em Buscar para iniciar o cadastro.")
        return

    with st.form("form_pedido_completo"):
        # ── Dados do Cliente ────────────────────────────────────
        st.markdown('<div class="section-header">🏢 DADOS DO CLIENTE</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            cnpj             = st.text_input("CNPJ *", value=c.get("cnpj",""))
            razao_social     = st.text_input("Razão Social *", value=c.get("razao_social",""))
            data_fundacao    = st.text_input("Data de Fundação *", value=c.get("data_fundacao",""))
            telefone_cliente = st.text_input("Telefone *", value=c.get("telefone",""))
        with col2:
            inscricao_estadual  = st.text_input("Inscrição Estadual *", value=c.get("inscricao_estadual",""))
            nome_fantasia       = st.text_input("Nome Fantasia *", value=c.get("nome_fantasia",""))
            capital_social      = st.text_input("Capital Social *", value=c.get("capital_social",""))
            email_cliente       = st.text_input("Email do Cliente *", value=c.get("email",""))
        with col3:
            atividade_economica = st.text_input("Atividade Econômica *", value=c.get("atividade_economica",""))

        # ── Produto ─────────────────────────────────────────────
        st.markdown('<div class="section-header">📦 PRODUTO</div>', unsafe_allow_html=True)
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            produto = st.selectbox("Produto *", PRODUTOS, key="form_produto")
        with col_p2:
            qtd_acessos_novos = st.number_input("Quantidade de Acessos Novos *", min_value=0, value=1, key="form_acessos")

        # ── Administrador do Contrato ────────────────────────────
        st.markdown('<div class="section-header">👤 ADMINISTRADOR DO CONTRATO</div>', unsafe_allow_html=True)
        col_a1, col_a2, col_a3 = st.columns(3)
        with col_a1:
            adm_nome     = st.text_input("Nome *", key="adm_nome")
            adm_cpf      = st.text_input("CPF *", key="adm_cpf")
            adm_email    = st.text_input("Email *", value=c.get("email",""), key="adm_email")
        with col_a2:
            adm_sobrenome = st.text_input("Sobrenome *", key="adm_sobrenome")
            adm_rg        = st.text_input("RG *", key="adm_rg")
            adm_telefone  = st.text_input("Telefone *", value=c.get("telefone",""), key="adm_telefone")

        # ── Endereço ─────────────────────────────────────────────
        st.markdown('<div class="section-header">📍 ENDEREÇO</div>', unsafe_allow_html=True)
        col_e1, col_e2, col_e3 = st.columns([2,1,1])
        with col_e1:
            end_cep = st.text_input("CEP *", value=c.get("cep",""), key="end_cep")
        with col_e2:
            end_numero = st.text_input("Número *", value=c.get("numero",""), key="end_numero")
        with col_e3:
            end_complemento = st.text_input("Complemento", value=c.get("complemento",""), key="end_compl")

        col_e4, col_e5, col_e6, col_e7 = st.columns([3,2,2,1])
        with col_e4:
            end_logradouro = st.text_input("Logradouro *", value=c.get("logradouro",""), key="end_log")
        with col_e5:
            end_bairro = st.text_input("Bairro *", value=c.get("bairro",""), key="end_bairro")
        with col_e6:
            end_cidade = st.text_input("Cidade *", value=c.get("cidade",""), key="end_cidade")
        with col_e7:
            end_estado = st.text_input("UF *", value=c.get("estado",""), key="end_estado")

        # ── Dados para Entrega ───────────────────────────────────
        st.markdown('<div class="section-header">🚚 DADOS PARA ENTREGA</div>', unsafe_allow_html=True)
        copiar_end = st.checkbox("Copiar endereço acima para entrega", value=True, key="copiar_end")

        if copiar_end:
            ent_cep         = end_cep
            ent_numero      = end_numero
            ent_complemento = end_complemento
            ent_logradouro  = end_logradouro
            ent_bairro      = end_bairro
            ent_cidade      = end_cidade
            ent_estado      = end_estado
        else:
            col_ent1, col_ent2, col_ent3 = st.columns([2,1,1])
            with col_ent1:
                ent_cep = st.text_input("CEP Entrega *", key="ent_cep")
            with col_ent2:
                ent_numero = st.text_input("Número *", key="ent_numero")
            with col_ent3:
                ent_complemento = st.text_input("Complemento", key="ent_compl")
            col_ent4, col_ent5, col_ent6, col_ent7 = st.columns([3,2,2,1])
            with col_ent4:
                ent_logradouro = st.text_input("Logradouro *", key="ent_log")
            with col_ent5:
                ent_bairro = st.text_input("Bairro *", key="ent_bairro")
            with col_ent6:
                ent_cidade = st.text_input("Cidade *", key="ent_cidade")
            with col_ent7:
                ent_estado = st.text_input("UF *", key="ent_estado")

        ent_ponto_ref = st.text_input("Ponto de Referência", key="ent_ref")
        col_sab, col_hi, col_hf = st.columns(3)
        with col_sab:
            ent_sabado = st.selectbox("Entrega aos Sábados? *", ["Não","Sim"], key="ent_sabado")
        with col_hi:
            ent_hora_ini = st.text_input("Hora Inicial (ex: 08:00)", key="ent_hini")
        with col_hf:
            ent_hora_fim = st.text_input("Hora Final (ex: 18:00)", key="ent_hfim")

        # ── Faturamento ──────────────────────────────────────────
        st.markdown('<div class="section-header">💳 DADOS DE FATURAMENTO</div>', unsafe_allow_html=True)
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            fat_tipo = st.selectbox("Tipo de Fatura *", TIPO_FATURA, key="fat_tipo")
        with col_f2:
            fat_dia = st.selectbox("Dia do Vencimento *", DIA_VENCIMENTO, index=24, key="fat_dia")
        with col_f3:
            fat_email = st.text_input("Email para Fatura", value=c.get("email",""), key="fat_email")

        # ── Acessos Portados ─────────────────────────────────────
        st.markdown('<div class="section-header">📱 ACESSOS PORTADOS (OPCIONAL)</div>', unsafe_allow_html=True)
        st.caption("Informe os números que serão portados para a TIM. Clique em + para adicionar mais.")

        n_portados = st.number_input("Quantos acessos portados?", min_value=0, max_value=50, value=0, key="n_portados")
        portados_lista = []
        if n_portados > 0:
            for i in range(int(n_portados)):
                col_pn, col_pc, col_pg = st.columns(3)
                with col_pn:
                    pnome = st.text_input(f"Nome #{i+1}", key=f"p_nome_{i}")
                with col_pc:
                    pcpf = st.text_input(f"CPF #{i+1}", key=f"p_cpf_{i}")
                with col_pg:
                    pgsm = st.text_input(f"GSM (número atual) #{i+1}", key=f"p_gsm_{i}")
                portados_lista.append({"nome": pnome, "cpf": pcpf, "gsm": pgsm})

        # ── Obs TC ───────────────────────────────────────────────
        st.markdown('<div class="section-header">📝 OBSERVAÇÃO PARA O TERMO DE CONTRATAÇÃO</div>', unsafe_allow_html=True)
        obs_tc = st.text_area("Observações (opcional)", height=80, key="obs_tc")

        # ── Vínculo (quem é responsável) ─────────────────────────
        st.markdown('<div class="section-header">🔗 RESPONSÁVEL PELO PEDIDO</div>', unsafe_allow_html=True)

        # Busca líderes/parceiros disponíveis para vincular
        df_usu = load_usuarios()
        opcoes_vinculo = [user["nome"]]  # padrão: ele mesmo
        if not df_usu.empty and user["perfil"] in ["admin","bko"]:
            todos_nomes = df_usu[df_usu["ativo"]=="sim"]["nome"].tolist()
            opcoes_vinculo = sorted(set(todos_nomes))

        vinculo_sel = st.selectbox(
            "Pedido cadastrado em nome de:",
            opcoes_vinculo,
            index=opcoes_vinculo.index(user["nome"]) if user["nome"] in opcoes_vinculo else 0,
            key="vinculo_sel"
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Aviso documentação ───────────────────────────────────
        st.markdown("""
        <div class="aviso-doc">
          📎 <b>Após enviar este cadastro</b>, solicite ao cliente que envie os documentos para o BKO:<br>
          <b>adm@connectgroup.solutions · guthyerre.silva@connectbrasil.tech · bko2@connectbrasil.tech</b><br><br>
          Documentos necessários: Contrato Social · RG e CPF do Administrador · Comprovante de Endereço · Documentos dos Sócios
        </div>
        """, unsafe_allow_html=True)

        submitted = st.form_submit_button("✅ Enviar Pedido para Fila de Impute", type="primary", use_container_width=True)

        if submitted:
            if not all([cnpj, razao_social, adm_nome, adm_cpf, end_cep]):
                st.error("⚠️ Preencha todos os campos obrigatórios (*)")
            else:
                dados_pedido = {
                    "cnpj": cnpj, "inscricao_estadual": inscricao_estadual,
                    "atividade_economica": atividade_economica,
                    "razao_social": razao_social, "nome_fantasia": nome_fantasia,
                    "data_fundacao": data_fundacao, "capital_social": capital_social,
                    "telefone_cliente": telefone_cliente, "email_cliente": email_cliente,
                    "adm_nome": adm_nome, "adm_sobrenome": adm_sobrenome,
                    "adm_cpf": adm_cpf, "adm_rg": adm_rg,
                    "adm_email": adm_email, "adm_telefone": adm_telefone,
                    "end_cep": end_cep, "end_numero": end_numero,
                    "end_complemento": end_complemento, "end_logradouro": end_logradouro,
                    "end_bairro": end_bairro, "end_estado": end_estado, "end_cidade": end_cidade,
                    "ent_cep": ent_cep, "ent_numero": ent_numero,
                    "ent_complemento": ent_complemento, "ent_logradouro": ent_logradouro,
                    "ent_bairro": ent_bairro, "ent_estado": ent_estado, "ent_cidade": ent_cidade,
                    "ent_ponto_ref": ent_ponto_ref, "ent_sabado": ent_sabado,
                    "ent_hora_ini": ent_hora_ini, "ent_hora_fim": ent_hora_fim,
                    "fat_tipo": fat_tipo, "fat_dia_vencimento": fat_dia, "fat_email": fat_email,
                    "produto": produto, "qtd_acessos_novos": qtd_acessos_novos,
                    "acessos_portados": portados_lista,
                    "obs_tc": obs_tc,
                }
                with st.spinner("Salvando pedido e notificando BKO..."):
                    id_novo = salvar_pedido(dados_pedido, user)
                    enviar_email_bko(id_novo, dados_pedido, user)

                st.success(f"""
                ✅ **Pedido {id_novo} enviado para a fila de impute!**

                O BKO foi notificado por e-mail e vai processar em breve.
                Solicite ao cliente que envie a documentação para:
                **adm@connectgroup.solutions**
                """)
                st.session_state.pop("form_cnpj_dados", None)


# ─────────────────────────────────────────────────────────────────
#  TELAS POR PERFIL
# ─────────────────────────────────────────────────────────────────

def header(user):
    perfil_info = PERFIS.get(user["perfil"], {"label": user["perfil"], "icon": "👤"})
    st.markdown(f"""
    <div class="header-portal">
      <div>
        <p class="header-title">📋 Portal de Impute — Connect Group</p>
        <p class="header-sub">{perfil_info['icon']} {user['nome']} · {perfil_info['label']} · {user.get('vinculo','')}</p>
      </div>
      <span class="header-badge">{perfil_info['icon']} {perfil_info['label'].upper()}</span>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown(f"**{perfil_info['icon']} {user['nome']}**")
        st.caption(perfil_info['label'])
        st.markdown("---")
        if st.button("🔄 Atualizar dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.pop("user", None)
            st.rerun()


def filtrar_pedidos(df, user):
    """Filtra pedidos de acordo com o perfil do usuário."""
    if df.empty:
        return df
    if user["perfil"] in ["admin","bko"]:
        return df  # vê tudo
    elif user["perfil"] == "lider":
        # Vê pedidos da equipe dele (vinculo_cadastrador == vinculo do líder)
        return df[df["vinculo_cadastrador"].str.strip().str.lower() == user.get("vinculo","").strip().lower()]
    else:
        # Parceiro e vendedor veem só os seus
        return df[df["cadastrado_por"] == user["login"]]


def tela_fila_bko(df, user):
    """Fila de pedidos aguardando BKO."""
    if df.empty or "status" not in df.columns:
        st.markdown('<div class="section-header">⏳ FILA DE IMPUTE — 0 pedido(s) aguardando</div>', unsafe_allow_html=True)
        st.success("✅ Fila vazia! Nenhum pedido aguardando.")
        return
    aguardando = df[df["status"] == "Aguardando BKO"]
    st.markdown(f'<div class="section-header">⏳ FILA DE IMPUTE — {len(aguardando)} pedido(s) aguardando</div>', unsafe_allow_html=True)

    if aguardando.empty:
        st.success("✅ Fila vazia! Nenhum pedido aguardando.")
        return

    for _, row in aguardando.sort_values("data_cadastro").iterrows():
        cor = STATUS_CORES.get(row.get("status",""), "#94a3b8")
        col_card, col_assumir = st.columns([5, 1])
        with col_card:
            card_pedido(row, user, mostrar_acao=True, contexto="_fila")
        with col_assumir:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(f"🙋 Assumir", key=f"assumir_{row.get('id','')}", use_container_width=True, type="primary"):
                if bko_assumir(row.get("id",""), user["login"]):
                    st.success(f"✅ Pedido {row.get('id','')} assumido!")
                    st.rerun()


def tela_todos_pedidos(df, user):
    """Todos os pedidos com filtros e atualização de status."""
    st.markdown('<div class="section-header">📋 TODOS OS PEDIDOS</div>', unsafe_allow_html=True)

    if df.empty or "status" not in df.columns:
        st.info("Nenhum pedido cadastrado ainda.")
        return

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        status_sel = st.selectbox("Status", ["Todos"] + STATUS_OPCOES, key="filtro_status_todos")
    with col_f2:
        busca = st.text_input("Buscar CNPJ / Empresa", key="busca_todos")
    with col_f3:
        if user["perfil"] in ["admin","bko"]:
            cadastradores = ["Todos"] + sorted(df["cadastrado_por"].dropna().unique().tolist()) if "cadastrado_por" in df.columns else ["Todos"]
            cad_sel = st.selectbox("Cadastrado por", cadastradores, key="filtro_cad")
        else:
            cad_sel = "Todos"
    with col_f4:
        produtos_opts = ["Todos"] + sorted(df["produto"].dropna().unique().tolist()) if "produto" in df.columns else ["Todos"]
        prod_sel = st.selectbox("Produto", produtos_opts, key="filtro_prod")

    df_f = df.copy()
    if status_sel != "Todos":
        df_f = df_f[df_f["status"] == status_sel]
    if busca:
        mask = df_f.get("razao_social", pd.Series(dtype=str)).str.contains(busca, case=False, na=False) | \
               df_f.get("cnpj", pd.Series(dtype=str)).str.contains(busca, na=False)
        df_f = df_f[mask]
    if cad_sel != "Todos":
        df_f = df_f[df_f["cadastrado_por"] == cad_sel]
    if prod_sel != "Todos":
        df_f = df_f[df_f["produto"] == prod_sel]

    df_f = df_f.sort_values("data_cadastro", ascending=False) if "data_cadastro" in df_f.columns else df_f
    st.caption(f"{len(df_f)} pedido(s) encontrado(s)")

    for _, row in df_f.iterrows():
        id_pedido = row.get("id","")
        card_pedido(row, user, mostrar_acao=True, contexto="_todos")

        # Painel de atualização (só BKO e Admin)
        if user["perfil"] in ["admin","bko"]:
            with st.expander(f"✏️ Atualizar status — {id_pedido}"):
                col_s1, col_s2, col_s3 = st.columns(3)
                with col_s1:
                    idx = STATUS_OPCOES.index(row.get("status","Aguardando BKO")) if row.get("status") in STATUS_OPCOES else 0
                    novo_status = st.selectbox("Novo status", STATUS_OPCOES, index=idx, key=f"ns_{id_pedido}")
                with col_s2:
                    pedido_tim = st.text_input("Nº Pedido TIM", value=row.get("pedido_tim",""), key=f"pt_{id_pedido}")
                with col_s3:
                    obs_int = st.text_input("Obs. interna", value=row.get("obs_interna",""), key=f"oi_{id_pedido}")
                if st.button("💾 Salvar", key=f"sv_{id_pedido}", type="primary"):
                    if atualizar_status_pedido(id_pedido, novo_status, pedido_tim, obs_int, user["login"]):
                        st.success("✅ Atualizado!")
                        st.rerun()

    if not df_f.empty:
        st.markdown("---")
        st.download_button("⬇️ Exportar CSV", df_f.to_csv(index=False).encode("utf-8"), "pedidos_impute.csv", "text/csv")


def tela_usuarios(user):
    """Gerenciamento de usuários (admin only)."""
    st.markdown('<div class="section-header">👥 USUÁRIOS CADASTRADOS</div>', unsafe_allow_html=True)
    df_usu = load_usuarios()
    if not df_usu.empty:
        cols_show = [c for c in ["login","nome","perfil","vinculo","email","ativo","criado_em"] if c in df_usu.columns]
        st.dataframe(df_usu[cols_show], use_container_width=True, hide_index=True)

    st.markdown('<div class="section-header">➕ NOVO USUÁRIO</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        u_nome   = st.text_input("Nome completo", key="u_nome")
        u_login  = st.text_input("Login (sem espaços)", key="u_login")
        u_perfil = st.selectbox("Perfil", list(PERFIS.keys()), format_func=lambda x: f"{PERFIS[x]['icon']} {PERFIS[x]['label']}", key="u_perfil")
    with col2:
        u_vinculo = st.text_input("Vínculo (empresa/equipe)", key="u_vinculo")
        u_email   = st.text_input("Email", key="u_email")
        u_senha   = st.text_input("Senha", type="password", key="u_senha")
        u_senha2  = st.text_input("Confirmar senha", type="password", key="u_senha2")

    if st.button("✅ Criar Usuário", type="primary", use_container_width=True):
        if not all([u_nome, u_login, u_senha, u_email]):
            st.error("Preencha todos os campos.")
        elif u_senha != u_senha2:
            st.error("Senhas não coincidem.")
        else:
            df_exist = load_usuarios()
            if not df_exist.empty and u_login in df_exist["login"].values:
                st.error(f"Login '{u_login}' já existe.")
            else:
                salvar_usuario(u_login, u_senha, u_nome, u_perfil, u_vinculo, u_email)
                st.success(f"✅ Usuário **{u_nome}** criado com perfil **{PERFIS[u_perfil]['label']}**!")
                st.rerun()


# ─────────────────────────────────────────────────────────────────
#  TELA LOGIN
# ─────────────────────────────────────────────────────────────────

def tela_login():
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("""
        <div style="text-align:center;padding:50px 0 30px">
          <span style="font-size:3rem">📋</span>
          <h2 style="font-size:1.6rem;font-weight:800;color:#1e293b;margin:12px 0 4px">Portal de Impute</h2>
          <p style="color:#64748b;font-size:0.85rem;margin:0">Connect Group · TIM Empresas</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            login = st.text_input("Login", placeholder="Seu usuário de acesso")
            senha = st.text_input("Senha", type="password", placeholder="Sua senha")
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("🔐 Entrar", use_container_width=True, type="primary")

        if submitted:
            if not login or not senha:
                st.error("Preencha login e senha.")
            else:
                user = autenticar(login.strip(), senha.strip())
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Login ou senha incorretos.")

        st.markdown("""
        <div style="text-align:center;margin-top:16px;font-size:0.75rem;color:#94a3b8">
          Problemas de acesso? Contate a Connect Group.
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────

def main():
    if "user" not in st.session_state:
        tela_login()
        return

    user = st.session_state.user
    header(user)

    df_todos  = load_pedidos()
    df_filtrado = filtrar_pedidos(df_todos, user)

    # KPIs
    total      = len(df_filtrado)
    aguardando = len(df_filtrado[df_filtrado["status"] == "Aguardando BKO"]) if not df_filtrado.empty else 0
    em_tram    = len(df_filtrado[df_filtrado["status"].isin(["BKO Assumiu","Em Análise TIM","Pré-venda","Em Tramitação"])]) if not df_filtrado.empty else 0
    ativados   = len(df_filtrado[df_filtrado["status"] == "Ativado"]) if not df_filtrado.empty else 0

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-label">📋 Total</div>
          <div class="kpi-value">{total}</div><div class="kpi-sub">pedidos</div></div>""", unsafe_allow_html=True)
    with k2:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-label" style="color:#94a3b8">⏳ Aguardando BKO</div>
          <div class="kpi-value" style="color:#64748b">{aguardando}</div><div class="kpi-sub">na fila</div></div>""", unsafe_allow_html=True)
    with k3:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-label" style="color:#f59e0b">🔄 Em Andamento</div>
          <div class="kpi-value" style="color:#d97706">{em_tram}</div><div class="kpi-sub">em processo</div></div>""", unsafe_allow_html=True)
    with k4:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-label" style="color:#22c55e">✅ Ativados</div>
          <div class="kpi-value" style="color:#15803d">{ativados}</div><div class="kpi-sub">contratos ativados</div></div>""", unsafe_allow_html=True)

    st.markdown("")

    # Tabs por perfil
    if user["perfil"] in ["admin","bko"]:
        tab_fila, tab_todos, tab_novo, tab_usuarios = st.tabs([
            f"⏳ Fila BKO ({aguardando})",
            "📋 Todos os Pedidos",
            "➕ Novo Pedido",
            "👥 Usuários" if user["perfil"] == "admin" else "—"
        ])
        with tab_fila:
            tela_fila_bko(df_todos, user)
        with tab_todos:
            tela_todos_pedidos(df_filtrado, user)
        with tab_novo:
            form_novo_pedido(user)
        with tab_usuarios:
            if user["perfil"] == "admin":
                tela_usuarios(user)

    elif user["perfil"] == "lider":
        tab_fila, tab_todos, tab_novo = st.tabs([
            f"⏳ Aguardando ({aguardando})",
            "📋 Pedidos da Equipe",
            "➕ Novo Pedido"
        ])
        with tab_fila:
            pendentes = df_filtrado[df_filtrado["status"] == "Aguardando BKO"] if not df_filtrado.empty else pd.DataFrame()
            for _, row in (pendentes.iterrows() if not pendentes.empty else []):
                card_pedido(row, user, mostrar_acao=True, contexto="_lider")
            if pendentes.empty:
                st.info("Nenhum pedido aguardando BKO.")
        with tab_todos:
            tela_todos_pedidos(df_filtrado, user)
        with tab_novo:
            form_novo_pedido(user)

    else:  # parceiro / vendedor
        tab_meus, tab_novo = st.tabs(["📋 Meus Pedidos", "➕ Novo Pedido"])
        with tab_meus:
            if df_filtrado.empty:
                st.info("Você ainda não tem pedidos. Use **➕ Novo Pedido** para começar!")
            else:
                status_f = st.selectbox("Filtrar por status", ["Todos"] + STATUS_OPCOES, key="filtro_meus")
                df_m = df_filtrado if status_f == "Todos" else df_filtrado[df_filtrado["status"] == status_f]
                df_m = df_m.sort_values("data_cadastro", ascending=False) if "data_cadastro" in df_m.columns else df_m
                for _, row in df_m.iterrows():
                    card_pedido(row, user, mostrar_acao=True, contexto="_meus")
        with tab_novo:
            form_novo_pedido(user)


main()
