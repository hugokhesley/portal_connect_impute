"""
BKO_VENDEDOR.PY — Cadastro de Vendedor Real
Portal Connect Impute — Connect Group
"""

import streamlit as st
import pandas as pd
import unicodedata
from datetime import datetime

SPREADSHEET_ID    = "1HmtEFf2Akh7NLR2prxDh9S4gmioKYw419B4bkx4yBLg"
ABA_BKO           = "BKO-VENDEDOR-REAL"
ABA_COLABORADORES = "Colaboradores"

# Nomes normalizados das colunas reais da aba BKO-VENDEDOR-REAL
# Header real: SAFRA | pedido | RAZÃO SOCIAL | VENDEDOR REAL | LIDER | TBP
COL_SAFRA         = "safra"           # col   → SAFRA (mês de referência)
COL_PEDIDO        = "pedido"          # col_1 → pedido
COL_RAZAO_SOCIAL  = "razão_social"    # col_2 → RAZÃO SOCIAL
COL_VENDEDOR_REAL = "vendedor_real"   # col_3 → VENDEDOR REAL
COL_LIDER         = "lider"           # não_preencher → LIDER
COL_TBP           = "tbp"             # col_4 → TBP
# Colunas que não existem na BKO-VENDEDOR-REAL (usadas só internamente)
COL_FILA_ATUAL    = "fila_atual"
COL_STATUS        = "status_dash"
COL_ACESSOS       = "acessos"
COL_PRECO         = "preco_oferta"
COL_MES_ATIVACAO  = "safra"           # aponta para SAFRA

COR_STATUS = {
    "ENTRANTE":  "#22c55e",
    "EM ANALISE":"#8b5cf6",
    "PRE-VENDA": "#f59e0b",
    "DEVOLVIDOS":"#ef4444",
    "CREDITO":   "#3b82f6",
    "CONCLUIDO": "#15803d",
    "CONCLUÍDO": "#15803d",
}

MES_ATUAL = datetime.now().strftime("%m/%Y")


def _norm(s):
    return ''.join(c for c in unicodedata.normalize('NFD', str(s).lower())
                   if unicodedata.category(c) != 'Mn')


def _pend(val):
    s = str(val).strip()
    return s == "" or s.upper() in ("SEM VENDEDOR", "NAN", "NONE")


def _normaliza_col(s):
    """Normaliza nome de coluna: minúsculo, sem acento, espaço→underline."""
    import unicodedata as _ud
    s = str(s).strip().lower().replace(" ", "_")
    return ''.join(c for c in _ud.normalize('NFD', s) if _ud.category(c) != 'Mn')


def _parse_sheet(valores):
    """Constrói DataFrame a partir de get_all_values().
    Detecta o header real procurando a linha que contém palavras-chave
    conhecidas (pedido, safra, vendedor, etc.), não apenas a primeira linha.
    """
    if not valores:
        return pd.DataFrame()

    KEYWORDS = {"pedido", "safra", "vendedor", "razao", "razão", "lider", "líder"}

    header_idx = 0
    for i, row in enumerate(valores):
        row_norm = {_normaliza_col(c) for c in row if str(c).strip()}
        if row_norm & KEYWORDS:
            header_idx = i
            break

    if header_idx >= len(valores) - 1:
        return pd.DataFrame()

    header_raw = valores[header_idx]
    rows_raw   = valores[header_idx + 1:]

    seen = {}
    header = []
    for h in header_raw:
        k = _normaliza_col(h) or "col"
        if k in seen:
            seen[k] += 1
            k = f"{k}_{seen[k]}"
        else:
            seen[k] = 0
        header.append(k)

    n = len(header)
    rows = [r + [""] * (n - len(r)) if len(r) < n else r[:n] for r in rows_raw]
    df = pd.DataFrame(rows, columns=header)
    return df[df.apply(lambda r: any(str(v).strip() for v in r), axis=1)].reset_index(drop=True)


@st.cache_data(ttl=60, show_spinner=False)
def _load_bko_raw(_gc):
    try:
        aba = _gc.open_by_key(SPREADSHEET_ID).worksheet(ABA_BKO)
        df = _parse_sheet(aba.get_all_values())
        # Remove linhas onde pedido está vazio ou é cabeçalho repetido
        if COL_PEDIDO in df.columns:
            df = df[
                df[COL_PEDIDO].astype(str).str.strip().ne("") &
                ~df[COL_PEDIDO].astype(str).str.upper().isin(["PEDIDO", "NAN", "NONE"])
            ].reset_index(drop=True)
        return df
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
            return False, f"Colunas não encontradas: {header[:10]}"
        pnorm = str(pedido).strip().lstrip("0")
        for i, row in enumerate(todos[1:], start=2):
            if not row or len(row) <= idx_p:
                continue
            if str(row[idx_p]).strip().lstrip("0") == pnorm:
                aba.update_cell(i, idx_v + 1, vendedor_real)
                aba.update_cell(i, idx_l + 1, lider)
                idx_u = next((j for j, h in enumerate(header) if h == "atualizado_por"), None)
                if idx_u is not None:
                    aba.update_cell(i, idx_u + 1,
                        f"{usuario_portal} · {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                st.cache_data.clear()
                return True, f"Pedido {pedido} → '{vendedor_real}' salvo."
        return False, f"Pedido {pedido} não encontrado."
    except Exception as e:
        return False, f"Erro: {e}"


def _kpi(valor, label, cor_val, cor_bg, cor_borda):
    return (
        f'<div style="background:{cor_bg};border:1px solid {cor_borda};border-radius:10px;'
        f'padding:10px 20px;text-align:center;min-width:80px">'
        f'<div style="font-size:1.6rem;font-weight:800;color:{cor_val};line-height:1">{valor}</div>'
        f'<div style="font-size:0.65rem;font-weight:700;color:{cor_val};opacity:0.8;margin-top:2px">{label}</div>'
        f'</div>'
    )


def _card(razao, pedido, fila, status, acessos, preco_fmt, ativ_badge, cor, vendedor_atual="", bloqueado=False):
    lock_badge = ""
    if bloqueado:
        lock_badge = "<span style='background:#1e3a5f;color:#93c5fd;display:inline-block;padding:2px 8px;border-radius:99px;font-size:0.65rem;font-weight:700'>🔒 Preenchido</span>"
    return (
        f'<div style="background:#1e293b;border:1px solid #334155;border-left:4px solid {cor};'
        f'border-radius:10px;padding:12px 16px;margin-bottom:4px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">'
        f'<div>'
        f'<span style="font-size:0.95rem;font-weight:700;color:#f1f5f9">{razao}</span>'
        f'<span style="font-size:0.72rem;color:#64748b;margin-left:8px">#{pedido}</span>'
        f'</div>'
        f'<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">'
        f'{ativ_badge} {lock_badge}'
        f'<span style="background:{cor}33;color:{cor};border:1px solid {cor};'
        f'display:inline-block;padding:2px 9px;border-radius:99px;font-size:0.67rem;font-weight:700">{status}</span>'
        f'<span style="font-size:0.72rem;color:#64748b">{fila} · {acessos} ac. · {preco_fmt}</span>'
        f'</div></div>'
        + (f'<div style="font-size:0.72rem;color:#22c55e;margin-top:4px">✅ Vendedor: <b>{vendedor_atual}</b></div>' if vendedor_atual else '')
        + '</div>'
    )


# ─── COMPONENTE PRINCIPAL ─────────────────────────────────────────

def tela_bko_vendedor(user: dict, gc):
    perfil = user.get("perfil", "")
    is_admin = perfil == "admin"

    with st.spinner("Carregando pedidos..."):
        df_bko   = _load_bko_raw(gc)
        df_colab = _load_colaboradores(gc)

    if df_bko.empty:
        st.warning("Nenhum dado encontrado no BKO-VENDEDOR-REAL.")
        return

    # Debug temporário — remover após confirmar funcionamento
    with st.expander("🔍 Debug — colunas detectadas", expanded=False):
        st.write("**Colunas BKO:**", list(df_bko.columns))
        st.write("**Primeiras linhas:**", df_bko.head(3).to_dict())
        if COL_SAFRA in df_bko.columns:
            st.write("**Valores SAFRA (mês):**", df_bko[COL_SAFRA].unique().tolist()[:10])
        else:
            st.warning(f"Coluna SAFRA não encontrada. Colunas: {list(df_bko.columns)}")

    # Debug temporário — remove após confirmar colunas
    with st.expander("🔍 Debug colunas BKO (temporário)", expanded=False):
        st.write("Colunas BKO:", list(df_bko.columns))
        st.write("Primeiras linhas:", df_bko.head(3).to_dict())

    # Mapa vendedor → lider
    mapa_lider = {}
    if not df_colab.empty:
        vcol = next((c for c in df_colab.columns if "vendedor" in _norm(c)), None)
        lcol = next((c for c in df_colab.columns if "lider" in _norm(c)), None)
        if vcol and lcol:
            for _, row in df_colab.iterrows():
                v = str(row[vcol]).strip()
                l = str(row[lcol]).strip()
                if v and _norm(v) not in ("vendedor", ""):
                    mapa_lider[v] = l

    vendedores_lista = sorted(mapa_lider.keys())

    if not vendedores_lista:
        st.warning(f"⚠️ Sem vendedores. Colunas da aba Colaboradores: `{list(df_colab.columns)}`")

    # ── Filtro de mês ─────────────────────────────────────────────
    meses_disponiveis = []
    col_safra = COL_SAFRA if COL_SAFRA in df_bko.columns else None
    if col_safra:
        meses_raw = df_bko[col_safra].astype(str).str.strip()
        meses_validos = sorted(
            {m for m in meses_raw if m and m.lower() not in ("none", "nan", "")},
            reverse=True
        )
        meses_disponiveis = meses_validos

    col_mes_sel, col_atv = st.columns([2, 1])
    with col_mes_sel:
        opcoes_mes = ["Todos os meses"] + meses_disponiveis
        idx_default = 1 if MES_ATUAL in meses_disponiveis else 0
        mes_sel = st.selectbox(
            "📅 Mês de referência",
            opcoes_mes,
            index=idx_default,
            key="bv_mes_sel"
        )
    with col_atv:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Atualizar", key="bv_refresh"):
            st.cache_data.clear()
            st.rerun()

    # Aplica filtro de mês — pedidos sem mês (tramitando) sempre aparecem
    if mes_sel != "Todos os meses" and col_safra:
        mask_mes = (df_bko[col_safra].astype(str).str.strip() == mes_sel)
        df_filtrado = df_bko[mask_mes].copy()
    else:
        df_filtrado = df_bko.copy()

    # Separa pendentes e preenchidos
    # COL_VENDEDOR_REAL normalizado = "vendedor_real" de "VENDEDOR REAL"
    col_vend = COL_VENDEDOR_REAL if COL_VENDEDOR_REAL in df_filtrado.columns else None
    if col_vend is None:
        # Tenta encontrar por nome parcial
        col_vend = next((c for c in df_filtrado.columns if "vendedor" in c), None)
    if col_vend:
        mask_pend    = df_filtrado[col_vend].apply(_pend)
        df_pendentes = df_filtrado[mask_pend].copy()
        df_completos = df_filtrado[~mask_pend].copy()
    else:
        df_pendentes = df_filtrado.copy()
        df_completos = pd.DataFrame()

    n_pend  = len(df_pendentes)
    n_ok    = len(df_completos)
    n_total = len(df_filtrado)

    # ── Header KPIs ───────────────────────────────────────────────
    kpis = (
        _kpi(n_pend,  "PENDENTES",   "#ef4444", "rgba(239,68,68,0.15)",  "#ef4444") +
        _kpi(n_ok,    "PREENCHIDOS", "#22c55e", "rgba(34,197,94,0.12)",  "#22c55e") +
        _kpi(n_total, "TOTAL",       "#93c5fd", "rgba(59,130,246,0.12)", "#3b82f6")
    )
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#0f172a,#1e3a5f);border-radius:14px;'
        f'padding:20px 28px;margin-bottom:20px;display:flex;align-items:center;'
        f'justify-content:space-between;flex-wrap:wrap;gap:12px;border:1px solid #1e40af">'
        f'<div>'
        f'<div style="font-size:1.15rem;font-weight:800;color:#f1f5f9">🎯 Cadastro de Vendedor Real</div>'
        f'<div style="font-size:0.78rem;color:#94a3b8;margin-top:3px">'
        f'Safra: <b style="color:#93c5fd">{mes_sel}</b> · sem acesso direto ao Sheets'
        f'</div></div>'
        f'<div style="display:flex;gap:10px;flex-wrap:wrap">{kpis}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    st.markdown("")

    tab_pend, tab_todos = st.tabs([
        f"⚠️ Pendentes ({n_pend})",
        f"✅ Preenchidos ({n_ok})",
    ])

    with tab_pend:
        _render_pendentes(df_pendentes, vendedores_lista, mapa_lider, user, gc, is_admin)
    with tab_todos:
        _render_preenchidos(df_completos, vendedores_lista, mapa_lider, user, gc, is_admin)


# ─── PENDENTES ────────────────────────────────────────────────────

def _render_pendentes(df, vendedores_lista, mapa_lider, user, gc, is_admin):
    if df.empty:
        st.success("✅ Todos os pedidos do período já têm vendedor cadastrado!")
        return
    if not vendedores_lista:
        st.warning("⚠️ Lista de vendedores vazia — verifique a aba Colaboradores.")
        return

    st.caption(f"**{len(df)}** pedido(s) aguardando identificação do vendedor.")
    st.markdown("")

    with st.form("form_bko_vendedor_pendentes"):
        selecoes = {}

        for idx, row in df.iterrows():
            pedido  = str(row.get(COL_PEDIDO, "")).strip()
            razao   = str(row.get(COL_RAZAO_SOCIAL, "—")).strip() or "—"
            fila    = str(row.get(COL_FILA_ATUAL, "—")).strip()
            status  = str(row.get(COL_STATUS, "—")).strip()
            acessos = row.get(COL_ACESSOS, "")
            preco   = row.get(COL_PRECO, "")
            mes_atv = str(row.get(COL_MES_ATIVACAO, "")).strip()

            if not pedido:
                continue  # pula linhas sem número de pedido

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
                    key=f"sv_{idx}_{pedido}",
                    label_visibility="collapsed",
                )
                selecoes[f"{idx}"] = (pedido, sel)

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
            preenchidos = {k: (p, v) for k, (p, v) in selecoes.items()
                          if v != "— Selecione o vendedor —"}
            n_ignorados = sum(1 for _, (p, v) in selecoes.items()
                              if v == "— Selecione o vendedor —")

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
                if n_ignorados:
                    st.info(f"ℹ️ {n_ignorados} pedido(s) ignorados (sem seleção).")
                if ok_count > 0:
                    st.success(f"✅ {ok_count} pedido(s) atualizados!")
                    st.cache_data.clear()
                    st.rerun()


# ─── PREENCHIDOS (admin pode alterar, outros só visualizam) ───────

def _render_preenchidos(df, vendedores_lista, mapa_lider, user, gc, is_admin):
    if df.empty:
        st.info("Nenhum pedido preenchido no período selecionado.")
        return

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        busca = st.text_input("🔍 Empresa / pedido", key="bv_busca_pre")
    with col_f2:
        lider_opts = ["Todos"] + sorted({str(r.get(COL_LIDER,"")).strip()
                                          for _, r in df.iterrows()
                                          if str(r.get(COL_LIDER,"")).strip()})
        lider_f = st.selectbox("Equipe / Líder", lider_opts, key="bv_lider_f")

    df_f = df.copy()
    if busca:
        mask = pd.Series(False, index=df_f.index)
        for col in [COL_RAZAO_SOCIAL, COL_PEDIDO]:
            if col in df_f.columns:
                mask |= df_f[col].astype(str).str.contains(busca, case=False, na=False)
        df_f = df_f[mask]
    if lider_f != "Todos" and COL_LIDER in df_f.columns:
        df_f = df_f[df_f[COL_LIDER].astype(str).str.strip() == lider_f]

    st.caption(f"**{len(df_f)}** pedido(s) preenchidos")

    cols_show = [c for c in [
        COL_PEDIDO, COL_RAZAO_SOCIAL, COL_STATUS, COL_MES_ATIVACAO,
        COL_VENDEDOR_REAL, COL_LIDER, COL_ACESSOS, COL_PRECO
    ] if c in df_f.columns]

    col_cfg = {
        COL_PEDIDO:       "Pedido",
        COL_RAZAO_SOCIAL: "Razão Social",
        COL_STATUS:       "Status",
        COL_MES_ATIVACAO: "Mês Ativação",
        COL_VENDEDOR_REAL:"Vendedor Real",
        COL_LIDER:        "Líder",
        COL_ACESSOS:      st.column_config.NumberColumn("Acessos", format="%d"),
        COL_PRECO:        st.column_config.NumberColumn("R$", format="R$ %.2f"),
    }

    st.dataframe(
        df_f[cols_show].reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
        column_config={k: v for k, v in col_cfg.items() if k in cols_show},
    )

    # Edição — SOMENTE ADMIN
    if is_admin and vendedores_lista:
        st.markdown("---")
        st.markdown(
            "<div style='background:#1e293b;border:1px solid #334155;border-radius:10px;"
            "padding:14px 18px;margin-top:8px'>"
            "<div style='font-size:0.8rem;font-weight:700;color:#f59e0b;margin-bottom:10px'>"
            "👑 Área Admin — Alterar vendedor de pedido já preenchido</div>",
            unsafe_allow_html=True
        )
        col_p, col_v, col_btn = st.columns([1, 2, 1])
        with col_p:
            ped_edit = st.text_input("Nº Pedido", key="bv_edit_pedido", placeholder="ex: 6341069")
        with col_v:
            vend_edit = st.selectbox("Novo Vendedor Real",
                                     ["— Selecione —"] + vendedores_lista, key="bv_edit_vend")
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💾 Alterar", key="bv_edit_salvar", type="primary", use_container_width=True):
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
        st.markdown("</div>", unsafe_allow_html=True)
    elif not is_admin:
        st.info("🔒 Apenas administradores podem alterar vendedores já preenchidos.")

    csv = df_f.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar CSV", csv, "bko_preenchidos.csv", "text/csv", key="bv_export_pre")
