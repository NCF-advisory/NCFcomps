"""Onglet Historique : consulter, re-exporter et supprimer les analyses enregistrees."""
import sys
from pathlib import Path

# Chaque page multipage s'execute independamment : racine du projet sur le path + auth.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st
import plotly.express as px

from comparables.streamlit_auth import require_authentication
from comparables import store
from comparables.pipeline import to_dataframe
from comparables.export.excel import build_excel_bytes, DISPLAY

st.set_page_config(page_title="Historique", layout="wide")
require_authentication()
st.title("Historique des analyses")

runs = store.list_runs()
if not runs:
    st.info("Aucune analyse enregistrée. Lancez un calcul puis « 💾 Enregistrer dans l'historique ».")
    st.stop()

labels = {field: label for field, label, *_ in DISPLAY}

# Recapitulatif des analyses
recap = pd.DataFrame(runs)[["id", "created_at", "username", "label", "n_records"]].rename(
    columns={"id": "N°", "created_at": "Date (UTC)", "username": "Utilisateur",
             "label": "Libellé", "n_records": "Sociétés"})
st.dataframe(recap, width="stretch", hide_index=True)

# Selection d'une analyse
options = {f"#{r['id']} — {r['created_at']} — {r['label'] or '(sans libellé)'}": r["id"]
           for r in runs}
choice = st.selectbox("Analyse à consulter", list(options))
run_id = options[choice]
records = store.load_run(run_id)
if not records:
    st.warning("Analyse vide ou introuvable.")
    st.stop()

df = to_dataframe(records)
cols = [f for f, *_ in DISPLAY if f in df.columns]
st.subheader("Tableau de comparables")
st.dataframe(df[cols].rename(columns=labels), width="stretch", hide_index=True)

# Visuel + medianes
c1, c2 = st.columns([2, 1])
with c1:
    if "ev_ebitda" in df.columns and df["ev_ebitda"].notna().any():
        st.plotly_chart(
            px.bar(df.dropna(subset=["ev_ebitda"]), x="ticker", y="ev_ebitda",
                   title="VE / EBITDA", labels={"ev_ebitda": "VE/EBITDA", "ticker": ""}),
            width="stretch")
with c2:
    stat_cols = ["beta_regression", "ev_sales", "ev_ebitda", "pe_trailing", "beta_unlevered"]
    present = [c for c in stat_cols if c in df.columns]
    if present:
        st.markdown("**Médianes**")
        med = df[present].median(numeric_only=True).rename(index=labels)
        st.dataframe(med.to_frame("Médiane"), width="stretch")

# Re-export / suppression
col_dl, col_del = st.columns(2)
with col_dl:
    st.download_button("📥 Excel", data=build_excel_bytes(records),
                       file_name=f"analyse_{run_id}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
with col_del:
    if st.button("🗑️ Supprimer cette analyse"):
        store.delete_run(run_id)
        st.rerun()
