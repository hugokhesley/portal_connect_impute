"""
BKO_VENDEDOR.PY — Módulo de Cadastro de Vendedor Real
Portal Connect Impute — Connect Group

Permite que BKOs e Líderes identifiquem o vendedor responsável por cada
pedido do BKO-VENDEDOR-REAL da planilha principal, sem acesso direto ao Sheets.

Integração no app.py:
    from bko_vendedor import tela_bko_vendedor
    # Na tab do perfil admin/bko:
    with tab_vendedor:
        tela_bko_vendedor(user, get_gc())
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# ─────────────────────────────────────────────────────────────────
#  CONSTANTES — mesmas da planilha do dashboard
# ─────────────────────────────────────────────────────────────────

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
#  FUNÇÕES DE LEITURA
# ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def _load_bko_raw(_gc):
    try:
        planilha = _gc.open_by_key(SPREADSHEET_ID)
        aba = planilha.worksheet(ABA_BKO)
        dados = aba.get_all_records()
        if not dados:
            return pd.DataFrame()
        df = pd.DataFrame(dados)
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro ao carregar BKO-VENDEDOR-REAL: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=120, show_spinner=False)
def _load_colaboradores(_gc):
    try:
        planilha = _gc.open_by_key(SPREADSHEET_ID)
        aba = planilha.worksheet(ABA_COLABORADORES)
        dados = aba.get_all_records()
        if not dados:
            return pd.DataFrame()
        df = pd.DataFrame(dados)
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────
#  FUNÇÃO DE GRAVAÇÃO
# ─────────────────────────────────────────────────────────────────

def _gravar_vendedor(gc, pedido: str, vendedor_real: str, lider: str, usuario_portal: str):
    """
    Localiza a linha do pedido no BKO-VENDEDOR-REAL e preenche
    vendedor_real e lider. Retorna (sucesso: bool, mensagem: str).
    """
    try:
        planilha = gc.open_by_key(SPREADSHEET_ID)
        aba = planilha.worksheet(ABA_BKO)
        todos = aba.get_all_values()

        if not todos:
            return False, "Planilha vazia."

        header = [str(h).strip().lower().replace(" ", "_") for h in todos[0]]

        try:
            col_pedido_idx   = header.index(COL_PEDIDO) + 1        # gspread base 1
            col_vendedor_idx = header.index(COL_VENDEDOR_REAL) + 1
            col_lider_idx    = header.index(COL_LIDER) + 1
        except ValueError as ve:
            return False, f"Coluna nao encontrada: {ve}"

        pedido_norm = str(pedido).strip().lstrip("0")

        for i, row in enumerate(todos[1:], start=2):
            if not row:
                continue
            val = str(row[col_pedido_idx - 1]).strip().lstrip("0")
            if val == pedido_norm:
                aba.update_cell(i, col_vendedor_idx, vendedor_real)
                aba.update_cell(i, col_lider_idx, lider)
                if "atualizado_por" in header:
                    col_upd = header.index("atualizado_por") + 1
                    aba.update_cell(
                        i, col_upd,
                        f"{usuario_portal} · {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                    )
                st.cache_data.clear()
                return True, f"Pedido {pedido} atualizado com vendedor '{vendedor_real}'."

        return False, f"Pedido {pedido} nao encontrado na planilha."
    except Exception as e:
        return False, f"Erro ao gravar: {e}"


# ─────────────────────────────────────────────────────────────────
#  COMPONENTE PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def tela_bko_vendedor(user: dict, gc):
    """
    Renderiza a tela de cadastro de Vendedor Real.
    Chamar com: tela_bko_vendedor(user, get_gc())
    """
    perfil  = user.get("perfil", "")
    login   = user.get("login", "")
    vinculo = user.get("vinculo", "")

    with st.spinner("Carregando pedidos pendentes..."):
        df_bko   = _load_bko_raw(gc)
        df_colab = _load_colaboradores(gc)

    if df_bko.empty:
        st.warning("Nenhum dado encontrado no BKO-VENDEDOR-REAL.")
        return

    # ── Mapa vendedor → lider ─────────────────────────────────────
    mapa_lider = {}
    if not df_colab.empty and "vendedor" in df_colab.columns and "lider" in df_colab.columns:
        for _, row in df_colab.iterrows():
            v = str(row.get("vendedor", "")).strip()
            l = str(row.get("lider", "")).strip()
            if v:
                mapa_lider[v] = l

    vendedores_lista = sorted(mapa_lider.keys())

    # ── Filtra pendentes ──────────────────────────────────────────
    col_vend = COL_VENDEDOR_REAL if COL_VENDEDOR_REAL in df_bko.columns else None

    def _e_pendente(val):
        s = str(val).strip()
        return s == "" or s.upper() in ("SEM VENDEDOR", "NAN", "NONE")

    if col_vend:
        mask_pend     = df_bko[col_vend].apply(_e_pendente)
        df_pendentes  = df_bko[mask_pend].copy()
        df_completos  = df_bko[~mask_pend].copy()
    else:
        df_pendentes  = df_bko.copy()
        df_completos  = pd.DataFrame()

    n_pend  = len(df_pendentes)
    n_ok    = len(df_completos)
    n_total = len(df_bko)

    # ── Header KPIs ───────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1e3a5f,#1e40af);border-radius:14px;
                padding:20px 28px;margin-bottom:20px;display:flex;
                align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px">
      <div>
        <div style="font-size:1.2rem;font-weight:800;color:#fff">🎯 Cadastro de Vendedor Real</div>
        <div style="font-size:0.8rem;color:rgba(255,255,255,0.65);margin-top:4px">
          Identifique o vendedor responsavel por cada pedido · sem acesso direto ao Sheets
        </div>
      </div>
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        <div style="background:rgba(239,68,68,0.25);border:1px solid #ef4444;border-radius:10px;
                    padding:10px 20px;text-align:center">
          <div style="font-size:1.6rem;font-weight:800;color:#ef4444">{n_pend}</div>
          <div style="font-size:0.68rem;color:#fca5a5;font-weight:600">PENDENTES</div>
        </div>
        <div style="background:rgba(34,197,94,0.2);border:1px solid #22c55e;border-radius:10px;
                    padding:10px 20px;text-align:center">
          <div style="font-size:1.6rem;font-weight:800;color:#22c55e">{n_ok}</div>
          <div style="font-size:0.68rem;color:#86efac;font-weight:600">PREENCHIDOS</div>
        </div>
        <div style="background:rgba(59,130,246,0.15);border:1px solid #3b82f6;border-radius:10px;
                    padding:10px 20px;text-align:center">
          <div style="font-size:1.6rem;font-weight:800;color:#93c5fd">{n_total}</div>
          <div style="font-size:0.68rem;color:#93c5fd;font-weight:600">TOTAL</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Botão atualizar
    col_atv, _ = st.columns([1, 4])
    with col_atv:
        if st.button("🔄 Atualizar lista", key="bv_refresh"):
            st.cache_data.clear()
            st.rerun()

    st.markdown("")

    # ── Tabs ──────────────────────────────────────────────────────
    tab_pend, tab_todos = st.tabs([
        f"⚠️ Pendentes ({n_pend})",
        f"📋 Todos os pedidos ({n_total})",
    ])

    with tab_pend:
        _render_pendentes(df_pendentes, vendedores_lista, mapa_lider, user, gc)

    with tab_todos:
        _render_todos(df_bko, col_vend, vendedores_lista, mapa_lider, user, gc)


# ─────────────────────────────────────────────────────────────────
#  RENDER — PENDENTES
# ─────────────────────────────────────────────────────────────────

COR_STATUS = {
    "ENTRANTE":  "#22c55e",
    "EM ANALISE":"#8b5cf6",
    "PRE-VENDA": "#f59e0b",
    "DEVOLVIDOS":"#ef4444",
    "CREDITO":   "#3b82f6",
    "CONCLUIDO": "#15803d",
    "CONCLUÍDO": "#15803d",
}


def _render_pendentes(df, vendedores_lista, mapa_lider, user, gc):
    if df.empty:
        st.success("Todos os pedidos ja tem vendedor cadastrado!")
        return

    if not vendedores_lista:
        st.warning("Aba Colaboradores nao carregou — impossivel exibir dropdown.")
        st.dataframe(df, use_container_width=True, hide_index=True)
        return

    st.caption(f"**{len(df)}** pedido(s) sem vendedor real. Selecione o vendedor responsavel por cada um e clique em Salvar.")
    st.markdown("")

    # Ordena: ativados primeiro
    col_mes = COL_MES_ATIVACAO if COL_MES_ATIVACAO in df.columns else None
    if col_mes:
        df = df.sort_values(col_mes, ascending=False, na_position="last").reset_index(drop=True)

    with st.form("form_bko_vendedor_pendentes"):
        selecoes = {}

        for _, row in df.iterrows():
            pedido   = str(row.get(COL_PEDIDO, "")).strip()
            razao    = str(row.get(COL_RAZAO_SOCIAL, "—")).strip()
            fila     = str(row.get(COL_FILA_ATUAL, "—")).strip()
            status   = str(row.get(COL_STATUS, "—")).strip()
            acessos  = row.get(COL_ACESSOS, "")
            preco    = row.get(COL_PRECO, "")
            mes_atv  = str(row.get(COL_MES_ATIVACAO, "")).strip()

            try:
                preco_fmt = f"R$ {float(str(preco).replace(',','.').replace('R$','').strip()):,.2f}"
            except Exception:
                preco_fmt = str(preco)

            cor = COR_STATUS.get(status.upper(), "#64748b")

            ativado_badge = (
                f"<span style='background:#dcfce7;color:#15803d;padding:2px 8px;"
                f"border-radius:99px;font-size:0.68rem;font-weight:700'>✅ {mes_atv}</span>"
            ) if mes_atv and mes_atv.lower() not in ("none", "") else (
                "<span style='background:#fef9c3;color:#92400e;padding:2px 8px;"
                "border-radius:99px;font-size:0.68rem;font-weight:700'>⏳ Em tramitacao</span>"
            )

            st.markdown(f"""
            <div style="background:#f8fafc;border:1px solid #e2e8f0;border-left:4px solid {cor};
                        border-radius:10px;padding:12px 16px;margin-bottom:4px">
              <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
                <div>
                  <span style="font-size:0.95rem;font-weight:700;color:#1e293b">{razao}</span>
                  <span style="font-size:0.75rem;color:#64748b;margin-left:8px">#{pedido}</span>
                </div>
                <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                  {ativado_badge}
                  <span style="background:{cor}22;color:{cor};border:1px solid {cor};
                               padding:2px 8px;border-radius:99px;font-size:0.68rem;font-weight:600">{status}</span>
                  <span style="font-size:0.72rem;color:#64748b">{fila} &nbsp;·&nbsp; {acessos} ac. &nbsp;·&nbsp; {preco_fmt}</span>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            col_sel, col_lider_info = st.columns([3, 1])
            with col_sel:
                opcoes = ["— Selecione o vendedor —"] + vendedores_lista
                sel = st.selectbox(
                    f"Vendedor — pedido {pedido}",
                    opcoes,
                    key=f"sel_vend_{pedido}",
                    label_visibility="collapsed",
                )
                selecoes[pedido] = sel

            with col_lider_info:
                if sel and sel != "— Selecione o vendedor —":
                    lider_auto = mapa_lider.get(sel, "—")
                    st.markdown(f"""
                    <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;
                                padding:7px 10px;font-size:0.75rem;color:#1e40af;margin-top:2px">
                      👤 <b>{lider_auto}</b>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="background:#f1f5f9;border-radius:8px;padding:7px 10px;
                                font-size:0.75rem;color:#94a3b8;margin-top:2px">
                      Lider: —
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("")

        salvar = st.form_submit_button(
            "💾 Salvar Todos os Vendedores Selecionados",
            type="primary",
            use_container_width=True,
        )

        if salvar:
            preenchidos     = {p: v for p, v in selecoes.items() if v != "— Selecione o vendedor —"}
            nao_preenchidos = [p for p, v in selecoes.items() if v == "— Selecione o vendedor —"]

            if not preenchidos:
                st.error("Selecione pelo menos um vendedor antes de salvar.")
            else:
                resultados = []
                prog = st.progress(0)
                total_p = len(preenchidos)
                for i, (pedido, vendedor) in enumerate(preenchidos.items()):
                    lider = mapa_lider.get(vendedor, "")
                    ok, msg = _gravar_vendedor(gc, pedido, vendedor, lider, user["login"])
                    resultados.append((pedido, vendedor, ok, msg))
                    prog.progress((i + 1) / total_p)

                ok_count  = sum(1 for *_, ok, _ in resultados if ok)
                err_count = len(resultados) - ok_count

                if ok_count > 0:
                    st.success(f"✅ {ok_count} pedido(s) atualizados com sucesso!")
                for pedido, vend, ok, msg in resultados:
                    if not ok:
                        st.error(f"Pedido {pedido}: {msg}")
                if nao_preenchidos:
                    st.info(f"ℹ️ {len(nao_preenchidos)} pedido(s) ignorados (sem selecao): {', '.join(nao_preenchidos)}")

                if ok_count > 0:
                    st.cache_data.clear()
                    st.rerun()


# ─────────────────────────────────────────────────────────────────
#  RENDER — TODOS OS PEDIDOS
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
        preenchi_f = st.selectbox(
            "Vendedor", ["Todos", "✅ Preenchidos", "⚠️ Pendentes"], key="bv_preenchi"
        )

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
        def _e_pend(v):
            s = str(v).strip()
            return s == "" or s.upper() in ("SEM VENDEDOR", "NAN", "NONE")
        if preenchi_f == "✅ Preenchidos":
            df_f = df_f[~df_f[col_vend].apply(_e_pend)]
        else:
            df_f = df_f[df_f[col_vend].apply(_e_pend)]

    st.caption(f"**{len(df_f)}** pedido(s)")

    cols_show = [c for c in [
        COL_PEDIDO, COL_RAZAO_SOCIAL, COL_FILA_ATUAL, COL_STATUS,
        COL_ACESSOS, COL_PRECO, COL_MES_ATIVACAO, COL_VENDEDOR_REAL, COL_LIDER
    ] if c in df_f.columns]

    col_cfg = {
        COL_PEDIDO:       "Pedido",
        COL_RAZAO_SOCIAL: "Razao Social",
        COL_FILA_ATUAL:   "Fila",
        COL_STATUS:       "Status",
        COL_ACESSOS:      st.column_config.NumberColumn("Acessos", format="%d"),
        COL_PRECO:        st.column_config.NumberColumn("R$", format="R$ %.2f"),
        COL_MES_ATIVACAO: "Mes Ativacao",
        COL_VENDEDOR_REAL:"Vendedor Real",
        COL_LIDER:        "Lider",
    }

    st.dataframe(
        df_f[cols_show].reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
        column_config={k: v for k, v in col_cfg.items() if k in cols_show},
    )

    # ── Edicao rapida de um pedido especifico ─────────────────────
    if vendedores_lista and user.get("perfil") in ["admin", "bko", "lider"]:
        st.markdown("---")
        st.markdown("**✏️ Atualizar vendedor de um pedido especifico:**")
        col_p, col_v, col_btn = st.columns([1, 2, 1])
        with col_p:
            ped_edit = st.text_input("No Pedido", key="bv_edit_pedido", placeholder="ex: 6341069")
        with col_v:
            vend_edit = st.selectbox(
                "Vendedor Real", ["— Selecione —"] + vendedores_lista, key="bv_edit_vend"
            )
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💾 Salvar", key="bv_edit_salvar", type="primary", use_container_width=True):
                if not ped_edit.strip():
                    st.error("Informe o numero do pedido.")
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
            st.caption(f"👤 Lider automatico: **{mapa_lider.get(vend_edit, '—')}**")

    csv = df_f.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exportar CSV", csv, "bko_vendedor_real.csv", "text/csv", key="bv_export")
