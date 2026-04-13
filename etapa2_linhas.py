"""
ETAPA 2 — COMPOSIÇÃO DAS LINHAS
Módulo separado que é importado pelo app.py principal
"""

import streamlit as st
import json

# ─────────────────────────────────────────────────────────────────
#  DADOS DE PLANOS E APARELHOS (editar aqui ou migrar pro Sheets)
# ─────────────────────────────────────────────────────────────────

PLANOS_TIM = [
    {"id": "P01", "nome": "TIM Controle 4GB",    "gb": 4,   "valor": 24.99, "tipo": "Controle"},
    {"id": "P02", "nome": "TIM Controle 6GB",    "gb": 6,   "valor": 29.99, "tipo": "Controle"},
    {"id": "P03", "nome": "TIM Controle 10GB",   "gb": 10,  "valor": 39.99, "tipo": "Controle"},
    {"id": "P04", "nome": "TIM Black 15GB",      "gb": 15,  "valor": 44.99, "tipo": "Pós-Pago"},
    {"id": "P05", "nome": "TIM Black 20GB",      "gb": 20,  "valor": 49.99, "tipo": "Pós-Pago"},
    {"id": "P06", "nome": "TIM Black 30GB",      "gb": 30,  "valor": 59.99, "tipo": "Pós-Pago"},
    {"id": "P07", "nome": "TIM Black 50GB",      "gb": 50,  "valor": 79.99, "tipo": "Pós-Pago"},
    {"id": "P08", "nome": "TIM Black 100GB",     "gb": 100, "valor": 99.99, "tipo": "Pós-Pago"},
    {"id": "P09", "nome": "TIM Black Ilimitado", "gb": 0,   "valor": 129.99,"tipo": "Pós-Pago"},
]

APARELHOS_TIM = [
    {"id": "A00", "nome": "— Sem aparelho —",          "valor": 0.0},
    {"id": "A01", "nome": "iPhone 15 128GB",           "valor": 3999.00},
    {"id": "A02", "nome": "iPhone 15 Pro 256GB",       "valor": 5999.00},
    {"id": "A03", "nome": "Samsung Galaxy S24 128GB",  "valor": 3499.00},
    {"id": "A04", "nome": "Samsung Galaxy A55 128GB",  "valor": 1799.00},
    {"id": "A05", "nome": "Samsung Galaxy A35 128GB",  "valor": 1299.00},
    {"id": "A06", "nome": "Motorola Edge 50 256GB",    "valor": 1999.00},
    {"id": "A07", "nome": "Motorola Moto G85 128GB",   "valor": 1099.00},
    {"id": "A08", "nome": "Xiaomi Redmi Note 13 128GB","valor": 999.00},
]

OPERADORAS = ["Claro", "Vivo", "Oi", "TIM", "Nextel", "Algar", "Outra"]

PLANOS_DICT    = {p["id"]: p for p in PLANOS_TIM}
APARELHOS_DICT = {a["id"]: a for a in APARELHOS_TIM}

PLANOS_NOMES    = [f"{p['nome']} — R$ {p['valor']:.2f}" for p in PLANOS_TIM]
APARELHOS_NOMES = [f"{a['nome']}{' — R$ ' + str(a['valor']) if a['valor'] > 0 else ''}" for a in APARELHOS_TIM]


# ─────────────────────────────────────────────────────────────────
#  COMPONENTE PRINCIPAL
# ─────────────────────────────────────────────────────────────────

def form_linhas(key_prefix="linhas"):
    """
    Renderiza o formulário de composição de linhas.
    Retorna lista de dicts com os dados de cada linha.
    """

    st.markdown("""
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;
                padding:12px 18px;margin-bottom:20px;font-size:0.82rem;color:#475569">
      ℹ️ <b>Como funciona:</b> Defina a quantidade de linhas e configure cada uma abaixo.
      Linhas com o mesmo plano e tipo podem ser agrupadas — informe a quantidade no grupo.
    </div>
    """, unsafe_allow_html=True)

    # ── Cedente único (para portabilidades do mesmo titular) ──────
    st.markdown("### 🔄 Cedente Único da Portabilidade")
    st.caption("Se todas ou a maioria das linhas portadas vêm do mesmo titular, preencha aqui. Você pode sobrescrever por linha se necessário.")

    usar_cedente_unico = st.checkbox(
        "Todas as linhas portadas têm o mesmo cedente",
        key=f"{key_prefix}_cedente_unico_check"
    )

    cedente_unico = {}
    if usar_cedente_unico:
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            cu_nome = st.text_input("Nome do Cedente", key=f"{key_prefix}_cu_nome")
            cu_cpfcnpj = st.text_input("CPF / CNPJ do Cedente", key=f"{key_prefix}_cu_doc")
        with col_c2:
            cu_operadora = st.selectbox("Operadora Atual", OPERADORAS, key=f"{key_prefix}_cu_op")
            cu_obs = st.text_input("Obs. do Cedente (opcional)", key=f"{key_prefix}_cu_obs")
        cedente_unico = {
            "nome": cu_nome,
            "cpf_cnpj": cu_cpfcnpj,
            "operadora": cu_operadora,
            "obs": cu_obs,
        }

    st.markdown("---")

    # ── Quantidade de grupos de linhas ────────────────────────────
    st.markdown("### 📱 Grupos de Linhas")
    st.caption("Cada grupo representa linhas com o mesmo plano e configuração. Ex: 3 linhas 30GB portadas = 1 grupo.")

    n_grupos = st.number_input(
        "Quantos grupos de linhas diferentes?",
        min_value=1, max_value=20, value=1,
        key=f"{key_prefix}_n_grupos"
    )

    grupos = []
    total_linhas = 0
    total_valor = 0.0

    for i in range(int(n_grupos)):
        with st.expander(f"📦 Grupo {i+1}", expanded=True):
            col_g1, col_g2, col_g3 = st.columns([1, 3, 1])

            with col_g1:
                qtd = st.number_input(
                    "Qtd. linhas",
                    min_value=1, max_value=200, value=1,
                    key=f"{key_prefix}_g{i}_qtd"
                )

            with col_g2:
                plano_idx = st.selectbox(
                    "Plano",
                    range(len(PLANOS_TIM)),
                    format_func=lambda x: PLANOS_NOMES[x],
                    key=f"{key_prefix}_g{i}_plano"
                )
                plano = PLANOS_TIM[plano_idx]

            with col_g3:
                valor_ajustado = st.number_input(
                    "Valor (R$)",
                    min_value=0.0,
                    value=float(plano["valor"]),
                    step=0.01,
                    format="%.2f",
                    key=f"{key_prefix}_g{i}_valor"
                )

            col_t1, col_t2 = st.columns(2)

            with col_t1:
                tipo_linha = st.radio(
                    "Tipo da linha",
                    ["🆕 Nova (sem portabilidade)", "🔄 Portada"],
                    key=f"{key_prefix}_g{i}_tipo",
                    horizontal=True
                )
                e_portada = "Portada" in tipo_linha

            with col_t2:
                aparelho_idx = st.selectbox(
                    "Aparelho (opcional)",
                    range(len(APARELHOS_TIM)),
                    format_func=lambda x: APARELHOS_NOMES[x],
                    key=f"{key_prefix}_g{i}_aparelho"
                )
                aparelho = APARELHOS_TIM[aparelho_idx]

            # ── Dados de portabilidade ────────────────────────────
            cedentes_grupo = []
            if e_portada:
                st.markdown(f"**🔄 Portabilidade — {int(qtd)} linha(s)**")

                # Se cedente único está ativado, mostra resumo e permite override
                if usar_cedente_unico and cedente_unico.get("nome"):
                    override = st.checkbox(
                        f"Este grupo tem cedente diferente do único cadastrado",
                        key=f"{key_prefix}_g{i}_override"
                    )
                    if not override:
                        # Usa cedente único — só pede os GSMs
                        st.info(f"✅ Cedente: **{cedente_unico['nome']}** · {cedente_unico['cpf_cnpj']} · {cedente_unico['operadora']}")
                        for j in range(int(qtd)):
                            gsm = st.text_input(
                                f"GSM atual da linha {j+1}",
                                placeholder="(83) 9XXXX-XXXX",
                                key=f"{key_prefix}_g{i}_gsm_{j}"
                            )
                            cedentes_grupo.append({
                                **cedente_unico,
                                "gsm": gsm
                            })
                    else:
                        # Override — preenche cedente individual por linha
                        cedentes_grupo = _form_cedentes_individuais(i, qtd, key_prefix)
                else:
                    # Sem cedente único — preenche por linha
                    cedentes_grupo = _form_cedentes_individuais(i, qtd, key_prefix)

            # ── Resumo do grupo ───────────────────────────────────
            subtotal = qtd * valor_ajustado
            if aparelho["valor"] > 0:
                subtotal += qtd * aparelho["valor"]

            total_linhas += qtd
            total_valor  += subtotal

            ap_txt = f" + {aparelho['nome']}" if aparelho["valor"] > 0 else ""
            st.markdown(f"""
            <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;
                        padding:10px 14px;margin-top:8px;font-size:0.82rem;color:#15803d">
              ✅ <b>{int(qtd)}x {plano['nome']}</b>{ap_txt} · R$ {valor_ajustado:.2f}/linha · 
              <b>Subtotal: R$ {subtotal:.2f}</b>
            </div>
            """, unsafe_allow_html=True)

            grupos.append({
                "grupo":         i + 1,
                "qtd":           int(qtd),
                "plano_id":      plano["id"],
                "plano_nome":    plano["nome"],
                "plano_gb":      plano["gb"],
                "tipo":          "Portada" if e_portada else "Nova",
                "valor_linha":   valor_ajustado,
                "aparelho_id":   aparelho["id"],
                "aparelho_nome": aparelho["nome"] if aparelho["valor"] > 0 else "",
                "aparelho_valor":aparelho["valor"],
                "subtotal":      subtotal,
                "cedentes":      cedentes_grupo,
            })

    # ── Resumo total ──────────────────────────────────────────────
    st.markdown("---")
    n_portadas = sum(g["qtd"] for g in grupos if g["tipo"] == "Portada")
    n_novas    = sum(g["qtd"] for g in grupos if g["tipo"] == "Nova")

    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
    with col_r1:
        st.metric("📱 Total de Linhas", total_linhas)
    with col_r2:
        st.metric("🆕 Novas", n_novas)
    with col_r3:
        st.metric("🔄 Portadas", n_portadas)
    with col_r4:
        st.metric("💰 Valor Mensal Total", f"R$ {total_valor:.2f}")

    return {
        "grupos":          grupos,
        "total_linhas":    total_linhas,
        "total_valor":     total_valor,
        "n_novas":         n_novas,
        "n_portadas":      n_portadas,
        "cedente_unico":   cedente_unico if usar_cedente_unico else {},
    }


def _form_cedentes_individuais(grupo_idx, qtd, key_prefix):
    """Formulário de cedente individual por linha portada."""
    cedentes = []
    for j in range(int(qtd)):
        st.markdown(f"**Linha portada {j+1}:**")
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        with col_p1:
            nome_c = st.text_input(
                "Nome do titular atual",
                key=f"{key_prefix}_g{grupo_idx}_c{j}_nome"
            )
        with col_p2:
            doc_c = st.text_input(
                "CPF / CNPJ",
                key=f"{key_prefix}_g{grupo_idx}_c{j}_doc"
            )
        with col_p3:
            gsm_c = st.text_input(
                "Número atual (GSM)",
                placeholder="(83) 9XXXX-XXXX",
                key=f"{key_prefix}_g{grupo_idx}_c{j}_gsm"
            )
        with col_p4:
            op_c = st.selectbox(
                "Operadora",
                OPERADORAS,
                key=f"{key_prefix}_g{grupo_idx}_c{j}_op"
            )
        cedentes.append({
            "nome":      nome_c,
            "cpf_cnpj":  doc_c,
            "gsm":       gsm_c,
            "operadora": op_c,
        })
    return cedentes


def resumo_linhas_html(dados_linhas: dict) -> str:
    """Gera HTML do resumo de linhas para o email do BKO."""
    if not dados_linhas or not dados_linhas.get("grupos"):
        return "<i>Sem dados de linhas</i>"

    html = f"""
    <table style='border-collapse:collapse;width:100%;font-size:12px'>
      <tr style='background:#1e3a5f;color:#fff'>
        <th style='padding:7px 10px;text-align:left'>Grupo</th>
        <th style='padding:7px 10px'>Qtd</th>
        <th style='padding:7px 10px;text-align:left'>Plano</th>
        <th style='padding:7px 10px'>Tipo</th>
        <th style='padding:7px 10px;text-align:left'>Aparelho</th>
        <th style='padding:7px 10px'>Valor/linha</th>
        <th style='padding:7px 10px'>Subtotal</th>
      </tr>
    """
    for g in dados_linhas["grupos"]:
        tipo_cor = "#22c55e" if g["tipo"] == "Nova" else "#3b82f6"
        ap = g.get("aparelho_nome","") or "—"
        html += f"""
      <tr style='border-bottom:1px solid #e2e8f0'>
        <td style='padding:6px 10px'>Grupo {g['grupo']}</td>
        <td style='padding:6px 10px;text-align:center'><b>{g['qtd']}</b></td>
        <td style='padding:6px 10px'>{g['plano_nome']}</td>
        <td style='padding:6px 10px;text-align:center'>
          <span style='background:{tipo_cor};color:#fff;padding:2px 8px;border-radius:99px;font-size:11px'>{g['tipo']}</span>
        </td>
        <td style='padding:6px 10px'>{ap}</td>
        <td style='padding:6px 10px;text-align:right'>R$ {g['valor_linha']:.2f}</td>
        <td style='padding:6px 10px;text-align:right'><b>R$ {g['subtotal']:.2f}</b></td>
      </tr>
        """
        # Cedentes das linhas portadas
        if g["tipo"] == "Portada" and g.get("cedentes"):
            for c in g["cedentes"]:
                if c.get("nome") or c.get("gsm"):
                    html += f"""
      <tr style='background:#eff6ff'>
        <td colspan='2'></td>
        <td colspan='5' style='padding:4px 10px;font-size:11px;color:#1e40af'>
          🔄 Portabilidade: <b>{c.get('nome','')}</b> · {c.get('cpf_cnpj','')} · 
          GSM: {c.get('gsm','')} · {c.get('operadora','')}
        </td>
      </tr>
                    """

    html += f"""
      <tr style='background:#f0fdf4;font-weight:700'>
        <td colspan='2' style='padding:8px 10px'>TOTAL</td>
        <td colspan='3' style='padding:8px 10px'>
          {dados_linhas['total_linhas']} linhas 
          ({dados_linhas['n_novas']} novas · {dados_linhas['n_portadas']} portadas)
        </td>
        <td style='padding:8px 10px;text-align:right'>—</td>
        <td style='padding:8px 10px;text-align:right'>R$ {dados_linhas['total_valor']:.2f}/mês</td>
      </tr>
    </table>
    """
    return html


def linhas_para_texto(dados_linhas: dict) -> str:
    """Gera texto simples para salvar no Sheets."""
    if not dados_linhas:
        return ""
    return json.dumps(dados_linhas, ensure_ascii=False)
