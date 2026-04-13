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

# Cores inline — não dependem de CSS externo
BG_CARD   = "#1e293b"
BG_PAGE   = "#0f172a"
TX_MAIN   = "#f1f5f9"
TX_SUB    = "#94a3b8"
BD_CARD   = "#334155"

COR_STATUS = {
    "ENTRANTE":  "#22c55e",
    "EM ANALISE":"#8b5cf6",
    "PRE-VENDA": "#f59e0b",
    "DEVOLVIDOS":"#ef4444",
    "CREDITO":   "#3b82f6",
    "CONCLUIDO": "#15803d",
    "CONCLUÍDO": "#15803d",
}


def _parse_sheet(valores):
    """Converte get_all_values() em DataFrame sem erro de colunas duplicadas.
    Pula linhas vazias iniciais para encontrar o header real."""
    if not valores:
        return pd.DataFrame()

    # Encontra a primeira linha não-vazia (header real)
    header_idx = 0
    for i, row in enumerate(valores):
        if any(str(c).strip() for c in row):
            header_idx = i
            break

    if header_idx >= len(valores) - 1:
        return pd.DataFrame()

    header_raw = valores[header_idx]
    rows_raw   = valores[header_idx + 1:]

    seen = {}
    header = []
    for h in header_raw:
        k = str(h).strip() or "col"  # mantém case original para debug
        k_lower = k.lower().replace(" ", "_")
        if k_lower in seen:
            seen[k_lower] += 1
            k_lower = f"{k_lower}_{seen[k_lower]}"
        else:
            seen[k_lower] = 0
        header.append(k_lower)

    n = len(header)
    rows = [r + [""] * (n - len(r)) if len(r) < n else r[:n] for r in rows_raw]
    df = pd.DataFrame(rows, columns=header)
    return df[df.apply(lambda r: any(str(v).strip() for v in r), axis=1)]


@st.cache_data(ttl=60, show_spinner=False)
def _load_bko_raw(_gc):
    try:
        aba = _gc.open_by_key(SPREADSHEET_ID).worksheet(ABA_BKO)
        return _parse_sheet(aba.get_all_values())
    except Exception as e:
        st.error(f"Erro ao carregar BKO-VENDEDOR-REAL: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=120, show_spinner=False)
def _load_colaboradores(_gc):
    try:
        aba = _gc.open_by_key(SPREADSHEET_ID).worksheet(ABA_COLABORADORES)
        return _parse_sheet(aba.get_all_values())
    except Exception as e:
        st.warning(f"Colaboradores: {e}")
        return pd.DataFrame()


def _gravar_vendedor(gc, pedido, vendedor_real, lider, usuario_portal):
    try:
        aba   = gc.open_by_key(SPREADSHEET_ID).worksheet(ABA_BKO)
        todos = aba.get_all_values()
        if not todos:
            return False, "Planilha vazia."
        header = [str(h).strip().lower().replace(" ", "_") for h in todos[0]]
        idx_p = next((i for i, h in enumerate(header) if h == COL_PEDIDO), None)
        idx_v = next((i for i, h in enumerate(header) if h == COL_VENDEDOR_REAL), None)
        idx_l = next((i for i, h in enumerate(header) if h == COL_LIDER), None)
        if None in (idx_p, idx_v, idx_l):
            return False, f"Colunas não encontradas. Header: {header[:10]}"
        pnorm = str(pedido).strip().lstrip("0")
        for i, row in enumerate(todos[1:], start=2):
            if not row or len(row) <= idx_p:
                continue
            if str(row[idx_p]).strip().lstrip("0") == pnorm:
                aba.update_cell(i, idx_v + 1, vendedor_real)
                aba.update_cell(i, idx_l + 1, lider)
                idx_u = next((j for j, h in enumerate(header) if h == "atualizado_por"), None)
                if idx_u is not None:
                    aba.update_cell(i, idx_u + 1, f"{usuario_portal} · {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                st.cache_data.clear()
                return True, f"Pedido {pedido} → '{vendedor_real}' salvo."
        return False, f"Pedido {pedido} não encontrado."
    except Exception as e:
        return False, f"Erro: {e}"


# ─── helpers de estilo inline ──────────────────────────────────────

def _kpi(valor, label, cor_val, cor_bg, cor_borda):
    return f"""
    <div style="background:{cor_bg};border:1px solid {cor_borda};border-radius:10px;
                padding:10px 20px;text-align:center;min-width:80px">
      <div style="font-size:1.6rem;font-weight:800;color:{cor_val};line-height:1">{valor}</div>
      <div style="font-size:0.65rem;font-weight:700;color:{cor_val};opacity:0.8;margin-top:2px">{label}</div>
    </div>"""

def _card(razao, pedido, fila, status, acessos, preco_fmt, ativ_badge, cor):
    return (
        f'<div style="background:#1e293b !important;border:1px solid #334155;border-left:4px solid {cor};'
        f'border-radius:10px;padding:12px 16px;margin-bottom:6px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">'
        f'<div>'
        f'<span style="font-size:0.95rem;font-weight:700;color:#f1f5f9 !important">{razao}</span>'
        f'<span style="font-size:0.72rem;color:#94a3b8 !important;margin-left:8px">#{pedido}</span>'
        f'</div>'
        f'<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">'
        f'{ativ_badge}'
        f'<span style="background:{cor}33;color:{cor} !important;border:1px solid {cor};'
        f'display:inline-block;padding:2px 9px;border-radius:99px;font-size:0.67rem;font-weight:700">{status}</span>'
        f'<span style="font-size:0.72rem;color:#94a3b8 !important">{fila} · {acessos} ac. · {preco_fmt}</span>'
        f'</div></div></div>'
    )


# ─── componente principal ─────────────────────────────────────────

def tela_bko_vendedor(user: dict, gc):

    with st.spinner("Carregando pedidos..."):
        df_bko   = _load_bko_raw(gc)
        df_colab = _load_colaboradores(gc)

    if df_bko.empty:
        st.warning("Nenhum dado encontrado no BKO-VENDEDOR-REAL.")
        return

    # Mapa vendedor → lider
    mapa_lider = {}
    if not df_colab.empty:
        import unicodedata
        def _norm(s):
            return ''.join(c for c in unicodedata.normalize('NFD', str(s).lower()) if unicodedata.category(c) != 'Mn')
        # Busca colunas por nome normalizado (ignora maiúsculas e acentos)
        vcol = next((c for c in df_colab.columns if "vendedor" in _norm(c)), None)
        lcol = next((c for c in df_colab.columns if "lider" in _norm(c)), None)
        if vcol and lcol:
            for _, row in df_colab.iterrows():
                v = str(row[vcol]).strip()
                l = str(row[lcol]).strip()
                if v and v.upper() not in ("VENDEDOR", ""):
                    mapa_lider[v] = l

    vendedores_lista = sorted(mapa_lider.keys())

    if not vendedores_lista:
        # Debug — mostra colunas disponíveis
        st.warning(f"⚠️ Colaboradores carregou mas sem vendedores. Colunas: `{list(df_colab.columns)}`")

    def _pend(val):
        s = str(val).strip()
        return s == "" or s.upper() in ("SEM VENDEDOR", "NAN", "NONE")

    col_vend = COL_VENDEDOR_REAL if COL_VENDEDOR_REAL in df_bko.columns else None
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

    # ── Header ────────────────────────────────────────────────────
    kpis = (
        _kpi(n_pend, "PENDENTES", "#ef4444", "rgba(239,68,68,0.15)", "#ef4444") +
        _kpi(n_ok,   "PREENCHIDOS", "#22c55e", "rgba(34,197,94,0.12)", "#22c55e") +
        _kpi(n_total,"TOTAL", "#93c5fd", "rgba(59,130,246,0.12)", "#3b82f6")
    )
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0f172a,#1e3a5f);border-radius:14px;
                padding:20px 28px;margin-bottom:20px;display:flex;align-items:center;
                justify-content:space-between;flex-wrap:wrap;gap:12px;
                border:1px solid #1e40af">
      <div>
        <div style="font-size:1.15rem;font-weight:800;color:#f1f5f9">🎯 Cadastro de Vendedor Real</div>
        <div style="font-size:0.78rem;color:#94a3b8;margin-top:3px">
          Identifique o vendedor responsável por cada pedido · sem acesso direto ao Sheets
        </div>
      </div>
      <div style="display:flex;gap:10px;flex-wrap:wrap">{kpis}</div>
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


# ─── render pendentes ─────────────────────────────────────────────

def _render_pendentes(df, vendedores_lista, mapa_lider, user, gc):
    if df.empty:
        st.success("✅ Todos os pedidos já têm vendedor cadastrado!")
        return
    if not vendedores_lista:
        st.warning("⚠️ Lista de vendedores vazia — verifique a aba Colaboradores.")
        return

    st.caption(f"**{len(df)}** pedido(s) sem vendedor. Selecione e clique em Salvar.")

    col_mes = COL_MES_ATIVACAO if COL_MES_ATIVACAO in df.columns else None
    if col_mes:
        df = df.sort_values(col_mes, ascending=False, na_position="last").reset_index(drop=True)

    with st.form("form_bko_vendedor_pendentes"):
        selecoes = {}

        for idx, row in df.iterrows():
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
                f"<span style='background:#14532d;color:#86efac;display:inline-block;"
                f"padding:2px 9px;border-radius:99px;font-size:0.67rem;font-weight:700'>✅ {mes_atv}</span>"
            ) if mes_atv and mes_atv.lower() not in ("none", "") else (
                "<span style='background:#422006;color:#fbbf24;display:inline-block;"
                "padding:2px 9px;border-radius:99px;font-size:0.67rem;font-weight:700'>⏳ Tramitando</span>"
            )

            st.markdown(_card(razao, pedido, fila, status, acessos, preco_fmt, ativ_badge, cor),
                        unsafe_allow_html=True)

            col_sel, col_lider_info = st.columns([3, 1])
            with col_sel:
                sel = st.selectbox(
                    f"Vendedor — {pedido}",
                    ["— Selecione o vendedor —"] + vendedores_lista,
                    key=f"sel_vend_{idx}_{pedido}",
                    label_visibility="collapsed",
                )
                selecoes[f"{idx}_{pedido}"] = (pedido, sel)

            with col_lider_info:
                if sel and sel != "— Selecione o vendedor —":
                    lider_auto = mapa_lider.get(sel, "—")
                    st.markdown(
                        f"<div style='background:#172554;border:1px solid #1e40af;border-radius:8px;"
                        f"padding:7px 10px;font-size:0.75rem;color:#93c5fd;margin-top:2px'>"
                        f"👤 <b>{lider_auto}</b></div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        "<div style='background:#1e293b;border:1px solid #334155;border-radius:8px;"
                        "padding:7px 10px;font-size:0.75rem;color:#475569;margin-top:2px'>Líder: —</div>",
                        unsafe_allow_html=True
                    )
            st.markdown("")

        salvar = st.form_submit_button(
            "💾 Salvar Todos os Selecionados",
            type="primary",
            use_container_width=True,
        )

        if salvar:
            preenchidos     = {k: (p, v) for k, (p, v) in selecoes.items() if v != "— Selecione o vendedor —"}
            nao_preenchidos = [p for k, (p, v) in selecoes.items() if v == "— Selecione o vendedor —"]

            if not preenchidos:
                st.error("Selecione pelo menos um vendedor antes de salvar.")
            else:
                prog = st.progress(0)
                resultados = []
                for i, (chave, (pedido, vendedor)) in enumerate(preenchidos.items()):
                    lider = mapa_lider.get(vendedor, "")
                    ok, msg = _gravar_vendedor(gc, pedido, vendedor, lider, user["login"])
                    resultados.append((ok, msg))
                    prog.progress((i + 1) / len(preenchidos))

                ok_count = sum(1 for ok, _ in resultados if ok)
                for ok, msg in resultados:
                    if not ok:
                        st.error(f"❌ {msg}")
                if nao_preenchidos:
                    st.info(f"ℹ️ {len(nao_preenchidos)} ignorado(s) sem seleção.")
                if ok_count > 0:
                    st.success(f"✅ {ok_count} pedido(s) atualizados!")
                    st.cache_data.clear()
                    st.rerun()


# ─── render todos ─────────────────────────────────────────────────

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
        df_f = df_f[~df_f[col_vend].apply(_pend)] if preenchi_f == "✅ Preenchidos" else df_f[df_f[col_vend].apply(_pend)]

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
        st.markdown("---")
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

    csv = df_f.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar CSV", csv, "bko_vendedor_real.csv", "text/csv", key="bv_export")
