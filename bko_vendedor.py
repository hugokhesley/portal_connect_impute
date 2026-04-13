"""
BKO_VENDEDOR.PY — Cadastro de Vendedor Real
Portal Connect Impute — Connect Group
"""

import streamlit as st
import pandas as pd
from datetime import datetime

SPREADSHEET_ID    = "1HmtEFf2Akh7NLR2prxDh9S4gmioKYw419B4bkx4yBLg"
ABA_BKO           = "BKO-VENDEDOR-REAL"
ABA_COLABORADORES = "Colaboradores"

COL_PEDIDO        = "pedido"
COL_RAZAO_SOCIAL  = "razao_social"
COL_FILA_ATUAL    = "fila_atual"
COL_STATUS        = "status_dash"
COL_ACESSOS       = "acessos"
COL_PRECO         = "preco_oferta"
COL_MES_ATIVACAO  = "mes_ativacao"
COL_VENDEDOR_REAL = "vendedor_real"
COL_LIDER         = "lider"

# ─────────────────────────────────────────────────────────────────
#  LEITURA — usa get_all_values para evitar erro de colunas duplicadas
# ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def _load_bko_raw(_gc):
    try:
        planilha = _gc.open_by_key(SPREADSHEET_ID)
        aba = planilha.worksheet(ABA_BKO)
        valores = aba.get_all_values()
        if not valores or len(valores) < 2:
            return pd.DataFrame()
        # Usa get_all_values e constrói DataFrame manualmente
        # para evitar erro de cabeçalhos duplicados
        header_raw = valores[0]
        # Deduplica cabeçalhos vazios ou repetidos
        seen = {}
        header = []
        for h in header_raw:
            h_norm = str(h).strip().lower().replace(" ", "_") or "col"
            if h_norm in seen:
                seen[h_norm] += 1
                h_norm = f"{h_norm}_{seen[h_norm]}"
            else:
                seen[h_norm] = 0
            header.append(h_norm)
        rows = valores[1:]
        # Garante que todas as linhas têm o mesmo número de colunas
        n = len(header)
        rows = [r + [""] * (n - len(r)) if len(r) < n else r[:n] for r in rows]
        df = pd.DataFrame(rows, columns=header)
        # Remove linhas completamente vazias
        df = df[df.apply(lambda r: any(v.strip() for v in r.astype(str)), axis=1)]
        return df
    except Exception as e:
        st.error(f"Erro ao carregar BKO-VENDEDOR-REAL: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=120, show_spinner=False)
def _load_colaboradores(_gc):
    try:
        planilha = _gc.open_by_key(SPREADSHEET_ID)
        aba = planilha.worksheet(ABA_COLABORADORES)
        valores = aba.get_all_values()
        if not valores or len(valores) < 2:
            return pd.DataFrame()
        header_raw = valores[0]
        seen = {}
        header = []
        for h in header_raw:
            h_norm = str(h).strip().lower().replace(" ", "_") or "col"
            if h_norm in seen:
                seen[h_norm] += 1
                h_norm = f"{h_norm}_{seen[h_norm]}"
            else:
                seen[h_norm] = 0
            header.append(h_norm)
        rows = valores[1:]
        n = len(header)
        rows = [r + [""] * (n - len(r)) if len(r) < n else r[:n] for r in rows]
        df = pd.DataFrame(rows, columns=header)
        df = df[df.apply(lambda r: any(v.strip() for v in r.astype(str)), axis=1)]
        return df
    except Exception:
        return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────
#  GRAVAÇÃO
# ─────────────────────────────────────────────────────────────────

def _gravar_vendedor(gc, pedido: str, vendedor_real: str, lider: str, usuario_portal: str):
    try:
        planilha = gc.open_by_key(SPREADSHEET_ID)
        aba = planilha.worksheet(ABA_BKO)
        todos = aba.get_all_values()
        if not todos:
            return False, "Planilha vazia."

        header_raw = todos[0]
        header = [str(h).strip().lower().replace(" ", "_") for h in header_raw]

        # Encontra índices (base 1 para gspread)
        idx_pedido   = next((i for i, h in enumerate(header) if h == COL_PEDIDO), None)
        idx_vendedor = next((i for i, h in enumerate(header) if h == COL_VENDEDOR_REAL), None)
        idx_lider    = next((i for i, h in enumerate(header) if h == COL_LIDER), None)

        if idx_pedido is None:
            return False, f"Coluna '{COL_PEDIDO}' não encontrada."
        if idx_vendedor is None:
            return False, f"Coluna '{COL_VENDEDOR_REAL}' não encontrada."
        if idx_lider is None:
            return False, f"Coluna '{COL_LIDER}' não encontrada."

        pedido_norm = str(pedido).strip().lstrip("0")

        for i, row in enumerate(todos[1:], start=2):
            if not row or len(row) <= idx_pedido:
                continue
            val = str(row[idx_pedido]).strip().lstrip("0")
            if val == pedido_norm:
                aba.update_cell(i, idx_vendedor + 1, vendedor_real)
                aba.update_cell(i, idx_lider + 1, lider)
                idx_upd = next((j for j, h in enumerate(header) if h == "atualizado_por"), None)
                if idx_upd is not None:
                    aba.update_cell(
                        i, idx_upd + 1,
                        f"{usuario_portal} · {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                    )
                st.cache_data.clear()
                return True, f"Pedido {pedido} atualizado com '{vendedor_real}'."

        return False, f"Pedido {pedido} não encontrado."
    except Exception as e:
        return False, f"Erro: {e}"


# ─────────────────────────────────────────────────────────────────
#  CSS — tema escuro compatível com o portal
# ─────────────────────────────────────────────────────────────────

CSS = """
<style>
.bv-header {
    background: linear-gradient(135deg, #0f172a, #1e3a5f);
    border-radius: 14px;
    padding: 20px 28px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    border: 1px solid #1e40af;
}
.bv-header-title {
    font-size: 1.15rem;
    font-weight: 800;
    color: #e2e8f0;
}
.bv-header-sub {
    font-size: 0.78rem;
    color: #94a3b8;
    margin-top: 3px;
}
.bv-kpi {
    border-radius: 10px;
    padding: 10px 20px;
    text-align: center;
    min-width: 80px;
}
.bv-kpi-val {
    font-size: 1.6rem;
    font-weight: 800;
    line-height: 1;
}
.bv-kpi-label {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.5px;
    margin-top: 2px;
}
.bv-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-left-width: 4px;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 4px;
}
.bv-card-empresa {
    font-size: 0.95rem;
    font-weight: 700;
    color: #f1f5f9;
}
.bv-card-info {
    font-size: 0.72rem;
    color: #94a3b8;
    margin-top: 2px;
}
.bv-badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 99px;
    font-size: 0.67rem;
    font-weight: 700;
}
.bv-lider-box {
    background: #172554;
    border: 1px solid #1e40af;
    border-radius: 8px;
    padding: 7px 10px;
    font-size: 0.75rem;
    color: #93c5fd;
    margin-top: 2px;
}
.bv-lider-empty {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 7px 10px;
    font-size: 0.75rem;
    color: #475569;
    margin-top: 2px;
}
.bv-edit-box {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 16px 20px;
    margin-top: 8px;
}
</style>
"""

COR_STATUS = {
    "ENTRANTE":  "#22c55e",
    "EM ANALISE":"#8b5cf6",
    "PRE-VENDA": "#f59e0b",
    "DEVOLVIDOS":"#ef4444",
    "CREDITO":   "#3b82f6",
    "CONCLUIDO": "#15803d",
    "CONCLUÍDO": "#15803d",
}


# ─────────────────────────────────────────────────────────────────
#  COMPONENTE PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def tela_bko_vendedor(user: dict, gc):
    st.markdown(CSS, unsafe_allow_html=True)

    with st.spinner("Carregando pedidos..."):
        df_bko   = _load_bko_raw(gc)
        df_colab = _load_colaboradores(gc)

    if df_bko.empty:
        st.warning("Nenhum dado encontrado no BKO-VENDEDOR-REAL.")
        return

    # Mapa vendedor → lider
    mapa_lider = {}
    if not df_colab.empty and "vendedor" in df_colab.columns and "lider" in df_colab.columns:
        for _, row in df_colab.iterrows():
            v = str(row.get("vendedor", "")).strip()
            l = str(row.get("lider", "")).strip()
            if v:
                mapa_lider[v] = l
    vendedores_lista = sorted(mapa_lider.keys())

    # Identifica pendentes
    col_vend = COL_VENDEDOR_REAL if COL_VENDEDOR_REAL in df_bko.columns else None

    def _pend(val):
        s = str(val).strip()
        return s == "" or s.upper() in ("SEM VENDEDOR", "NAN", "NONE", "")

    if col_vend:
        mask_pend    = df_bko[col_vend].apply(_pend)
        df_pendentes = df_bko[mask_pend].copy()
        df_completos = df_bko[~mask_pend].copy()
    else:
        df_pendentes = df_bko.copy()
        df_completos = pd.DataFrame()

    n_pend  = len(df_pendentes)
    n_ok    = len(df_completos)
    n_total = len(df_bko)

    # Header
    st.markdown(f"""
    <div class="bv-header">
      <div>
        <div class="bv-header-title">🎯 Cadastro de Vendedor Real</div>
        <div class="bv-header-sub">Identifique o vendedor responsável por cada pedido · sem acesso direto ao Sheets</div>
      </div>
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        <div class="bv-kpi" style="background:rgba(239,68,68,0.15);border:1px solid #ef4444">
          <div class="bv-kpi-val" style="color:#ef4444">{n_pend}</div>
          <div class="bv-kpi-label" style="color:#fca5a5">PENDENTES</div>
        </div>
        <div class="bv-kpi" style="background:rgba(34,197,94,0.12);border:1px solid #22c55e">
          <div class="bv-kpi-val" style="color:#22c55e">{n_ok}</div>
          <div class="bv-kpi-label" style="color:#86efac">PREENCHIDOS</div>
        </div>
        <div class="bv-kpi" style="background:rgba(59,130,246,0.12);border:1px solid #3b82f6">
          <div class="bv-kpi-val" style="color:#93c5fd">{n_total}</div>
          <div class="bv-kpi-label" style="color:#93c5fd">TOTAL</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_atv, _ = st.columns([1, 5])
    with col_atv:
        if st.button("🔄 Atualizar", key="bv_refresh"):
            st.cache_data.clear()
            st.rerun()

    st.markdown("")

    tab_pend, tab_todos = st.tabs([
        f"⚠️ Pendentes ({n_pend})",
        f"📋 Todos ({n_total})",
    ])

    with tab_pend:
        _render_pendentes(df_pendentes, vendedores_lista, mapa_lider, user, gc)

    with tab_todos:
        _render_todos(df_bko, col_vend, vendedores_lista, mapa_lider, user, gc)


# ─────────────────────────────────────────────────────────────────
#  RENDER — PENDENTES
# ─────────────────────────────────────────────────────────────────

def _render_pendentes(df, vendedores_lista, mapa_lider, user, gc):
    if df.empty:
        st.success("✅ Todos os pedidos já têm vendedor cadastrado!")
        return

    if not vendedores_lista:
        st.warning("⚠️ Aba Colaboradores não carregou — impossível exibir o dropdown.")
        return

    st.caption(f"**{len(df)}** pedido(s) sem vendedor real. Selecione e clique em Salvar.")
    st.markdown("")

    col_mes = COL_MES_ATIVACAO if COL_MES_ATIVACAO in df.columns else None
    if col_mes:
        df = df.sort_values(col_mes, ascending=False, na_position="last").reset_index(drop=True)

    with st.form("form_bko_vendedor_pendentes"):
        selecoes = {}

        for _, row in df.iterrows():
            pedido  = str(row.get(COL_PEDIDO, "")).strip()
            razao   = str(row.get(COL_RAZAO_SOCIAL, "—")).strip()
            fila    = str(row.get(COL_FILA_ATUAL, "—")).strip()
            status  = str(row.get(COL_STATUS, "—")).strip()
            acessos = row.get(COL_ACESSOS, "")
            preco   = row.get(COL_PRECO, "")
            mes_atv = str(row.get(COL_MES_ATIVACAO, "")).strip()

            try:
                preco_fmt = f"R$ {float(str(preco).replace(',','.').replace('R$','').strip()):,.2f}"
            except Exception:
                preco_fmt = str(preco)

            cor = COR_STATUS.get(status.upper(), "#64748b")

            ativ_badge = (
                f"<span class='bv-badge' style='background:#14532d;color:#86efac'>✅ {mes_atv}</span>"
            ) if mes_atv and mes_atv.lower() not in ("none", "") else (
                "<span class='bv-badge' style='background:#422006;color:#fbbf24'>⏳ Tramitando</span>"
            )

            st.markdown(f"""
            <div class="bv-card" style="border-left-color:{cor}">
              <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
                <div>
                  <span class="bv-card-empresa">{razao}</span>
                  <span style="font-size:0.72rem;color:#64748b;margin-left:8px">#{pedido}</span>
                </div>
                <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
                  {ativ_badge}
                  <span class="bv-badge" style="background:{cor}22;color:{cor};border:1px solid {cor}">{status}</span>
                  <span class="bv-card-info">{fila} &nbsp;·&nbsp; {acessos} ac. &nbsp;·&nbsp; {preco_fmt}</span>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            col_sel, col_lider_info = st.columns([3, 1])
            with col_sel:
                opcoes = ["— Selecione o vendedor —"] + vendedores_lista
                sel = st.selectbox(
                    f"Vendedor — {pedido}",
                    opcoes,
                    key=f"sel_vend_{pedido}",
                    label_visibility="collapsed",
                )
                selecoes[pedido] = sel

            with col_lider_info:
                if sel and sel != "— Selecione o vendedor —":
                    lider_auto = mapa_lider.get(sel, "—")
                    st.markdown(f'<div class="bv-lider-box">👤 <b>{lider_auto}</b></div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="bv-lider-empty">Líder: —</div>', unsafe_allow_html=True)

            st.markdown("")

        salvar = st.form_submit_button(
            "💾 Salvar Todos os Selecionados",
            type="primary",
            use_container_width=True,
        )

        if salvar:
            preenchidos     = {p: v for p, v in selecoes.items() if v != "— Selecione o vendedor —"}
            nao_preenchidos = [p for p, v in selecoes.items() if v == "— Selecione o vendedor —"]

            if not preenchidos:
                st.error("Selecione pelo menos um vendedor antes de salvar.")
            else:
                prog = st.progress(0)
                resultados = []
                for i, (pedido, vendedor) in enumerate(preenchidos.items()):
                    lider = mapa_lider.get(vendedor, "")
                    ok, msg = _gravar_vendedor(gc, pedido, vendedor, lider, user["login"])
                    resultados.append((pedido, ok, msg))
                    prog.progress((i + 1) / len(preenchidos))

                ok_count = sum(1 for _, ok, _ in resultados if ok)
                for _, ok, msg in resultados:
                    if not ok:
                        st.error(f"❌ {msg}")
                if nao_preenchidos:
                    st.info(f"ℹ️ {len(nao_preenchidos)} ignorado(s): {', '.join(nao_preenchidos)}")
                if ok_count > 0:
                    st.success(f"✅ {ok_count} pedido(s) atualizados!")
                    st.cache_data.clear()
                    st.rerun()


# ─────────────────────────────────────────────────────────────────
#  RENDER — TODOS
# ─────────────────────────────────────────────────────────────────

def _render_todos(df, col_vend, vendedores_lista, mapa_lider, user, gc):
    if df.empty:
        st.info("Nenhum pedido encontrado.")
        return

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        busca = st.text_input("🔍 Empresa / pedido", key="bv_busca")
    with col_f2:
        status_opts = ["Todos"]
        if COL_STATUS in df.columns:
            status_opts += sorted(df[COL_STATUS].dropna().unique().tolist())
        status_f = st.selectbox("Status", status_opts, key="bv_status")
    with col_f3:
        preenchi_f = st.selectbox("Vendedor", ["Todos", "✅ Preenchidos", "⚠️ Pendentes"], key="bv_preenchi")

    df_f = df.copy()
    if busca:
        mask = pd.Series(False, index=df_f.index)
        for col in [COL_RAZAO_SOCIAL, COL_PEDIDO]:
            if col in df_f.columns:
                mask |= df_f[col].astype(str).str.contains(busca, case=False, na=False)
        df_f = df_f[mask]
    if status_f != "Todos" and COL_STATUS in df_f.columns:
        df_f = df_f[df_f[COL_STATUS] == status_f]
    if preenchi_f != "Todos" and col_vend and col_vend in df_f.columns:
        def _pend(v):
            s = str(v).strip()
            return s == "" or s.upper() in ("SEM VENDEDOR", "NAN", "NONE")
        if preenchi_f == "✅ Preenchidos":
            df_f = df_f[~df_f[col_vend].apply(_pend)]
        else:
            df_f = df_f[df_f[col_vend].apply(_pend)]

    st.caption(f"**{len(df_f)}** pedido(s)")

    cols_show = [c for c in [
        COL_PEDIDO, COL_RAZAO_SOCIAL, COL_FILA_ATUAL, COL_STATUS,
        COL_ACESSOS, COL_PRECO, COL_MES_ATIVACAO, COL_VENDEDOR_REAL, COL_LIDER
    ] if c in df_f.columns]

    col_cfg = {
        COL_PEDIDO:       "Pedido",
        COL_RAZAO_SOCIAL: "Razão Social",
        COL_FILA_ATUAL:   "Fila",
        COL_STATUS:       "Status",
        COL_ACESSOS:      st.column_config.NumberColumn("Acessos", format="%d"),
        COL_PRECO:        st.column_config.NumberColumn("R$", format="R$ %.2f"),
        COL_MES_ATIVACAO: "Mês Ativação",
        COL_VENDEDOR_REAL:"Vendedor Real",
        COL_LIDER:        "Líder",
    }

    st.dataframe(
        df_f[cols_show].reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
        column_config={k: v for k, v in col_cfg.items() if k in cols_show},
    )

    # Edição rápida
    if vendedores_lista and user.get("perfil") in ["admin", "bko", "lider"]:
        st.markdown('<div class="bv-edit-box">', unsafe_allow_html=True)
        st.markdown("**✏️ Atualizar vendedor de um pedido específico:**")
        col_p, col_v, col_btn = st.columns([1, 2, 1])
        with col_p:
            ped_edit = st.text_input("Nº Pedido", key="bv_edit_pedido", placeholder="ex: 6341069")
        with col_v:
            vend_edit = st.selectbox("Vendedor Real", ["— Selecione —"] + vendedores_lista, key="bv_edit_vend")
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💾 Salvar", key="bv_edit_salvar", type="primary", use_container_width=True):
                if not ped_edit.strip():
                    st.error("Informe o número do pedido.")
                elif vend_edit == "— Selecione —":
                    st.error("Selecione o vendedor.")
                else:
                    lider = mapa_lider.get(vend_edit, "")
                    ok, msg = _gravar_vendedor(gc, ped_edit.strip(), vend_edit, lider, user["login"])
                    if ok:
                        st.success(f"✅ {msg}")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
        if vend_edit and vend_edit != "— Selecione —":
            st.caption(f"👤 Líder automático: **{mapa_lider.get(vend_edit, '—')}**")
        st.markdown('</div>', unsafe_allow_html=True)

    csv = df_f.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar CSV", csv, "bko_vendedor_real.csv", "text/csv", key="bv_export")
