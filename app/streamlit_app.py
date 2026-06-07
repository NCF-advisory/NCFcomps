"""Interface Streamlit : saisie des tickers -> tableau de comparables + visuels + export Excel.

Lancement (depuis la racine du projet, apres `pip install -e .`) :
    streamlit run app/streamlit_app.py
"""
from __future__ import annotations
import sys
from pathlib import Path

# Permet l'import du package meme sans installation editable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
import plotly.express as px

from comparables.config import settings
from comparables.pipeline import build_comparables, to_dataframe
from comparables.export.excel import build_excel_bytes, DISPLAY
from comparables.streamlit_auth import require_authentication
from comparables.sources.yahoo import best_symbol
from comparables import store

st.set_page_config(page_title="Comparables boursiers", layout="wide")
auth_user = require_authentication()   # bloque tant que l'utilisateur n'est pas connecté
st.title("Comparables boursiers — bêtas & multiples")

DEFAULT_NAMES = "L'Oréal\nAir Liquide\nLVMH\nSchneider Electric\nWatts Water\nMueller Water Products"
DEFAULT_TICKERS = "WMS\nGF.SW\nAALB.AS\nGEN.L\nWIE.VI\nMWA"

with st.sidebar:
    st.header("Paramètres")
    mode = st.radio("Saisie par", ["Nom de société", "Ticker"], horizontal=True)
    if mode == "Nom de société":
        raw = st.text_area("Sociétés (un nom par ligne)", DEFAULT_NAMES, height=170,
                           help="Le ticker est recherché automatiquement (vérifiable dans le tableau).")
    else:
        raw = st.text_area("Tickers (un par ligne)", DEFAULT_TICKERS, height=170)
    tax = st.number_input("Taux d'IS", 0.0, 0.60, settings.tax_rate, 0.01)
    period = st.selectbox("Période du bêta", ["2y", "3y", "5y", "10y"], index=2)
    frequency = st.selectbox("Fréquence", ["1mo", "1wk"], index=0)
    run = st.button("Lancer le calcul", type="primary")

# Calcul -> on memorise le resultat en session pour qu'il survive aux reruns (ex: bouton Enregistrer)
if run:
    lines = [t.strip() for t in raw.splitlines() if t.strip()]
    if not lines:
        st.warning("Saisissez au moins une société.")
        st.stop()
    if mode == "Nom de société":
        resolution, tickers = [], []
        with st.spinner("Recherche des tickers…"):
            for name in lines:
                try:
                    m = best_symbol(name)
                except Exception:
                    m = None
                if m:
                    tickers.append(m["symbol"])
                    resolution.append({"Saisi": name, "Ticker": m["symbol"],
                                       "Société (Yahoo)": m["name"], "Place": m["exchange"]})
                else:
                    resolution.append({"Saisi": name, "Ticker": "—",
                                       "Société (Yahoo)": "introuvable", "Place": ""})
        st.session_state["resolution"] = resolution
    else:
        tickers = lines
        st.session_state.pop("resolution", None)
    if not tickers:
        st.warning("Aucun ticker n'a pu être résolu. Vérifiez les noms ou passez en mode « Ticker ».")
        st.stop()
    with st.spinner(f"Récupération de {len(tickers)} sociétés…"):
        records = build_comparables(tickers, tax_rate=tax, period=period, frequency=frequency)
    st.session_state["records"] = records
    st.session_state["df"] = to_dataframe(records)
    st.session_state["params"] = {"tickers": tickers, "tax_rate": tax,
                                  "period": period, "frequency": frequency}
    st.session_state.pop("saved_run_id", None)

if "records" not in st.session_state:
    st.info("Renseignez les sociétés dans le panneau de gauche puis cliquez sur « Lancer le calcul ».")
    st.stop()

# Tickers résolus (mode Nom) : transparence pour vérifier/corriger
if st.session_state.get("resolution"):
    with st.expander("🔎 Tickers résolus automatiquement (vérifiez ; sinon passez en mode « Ticker »)",
                     expanded=True):
        st.dataframe(pd.DataFrame(st.session_state["resolution"]), width="stretch", hide_index=True)

records = st.session_state["records"]
df = st.session_state["df"]
labels = {field: label for field, label, *_ in DISPLAY}

# Tableau (libelles FR via DISPLAY)
cols = [f for f, *_ in DISPLAY if f in df.columns]
st.subheader("Tableau de comparables")
st.dataframe(df[cols].rename(columns=labels), width="stretch", hide_index=True)

# Visuels
st.subheader("Tableau de bord")
c1, c2 = st.columns(2)
with c1:
    if df["ev_ebitda"].notna().any():
        st.plotly_chart(
            px.bar(df.dropna(subset=["ev_ebitda"]), x="ticker", y="ev_ebitda",
                   title="VE / EBITDA", labels={"ev_ebitda": "VE/EBITDA", "ticker": ""}),
            width="stretch")
with c2:
    sub = df.dropna(subset=["beta_regression", "r2"])
    if not sub.empty:
        st.plotly_chart(
            px.scatter(sub, x="r2", y="beta_regression", text="ticker",
                       title="Bêta (régression) vs R²",
                       labels={"r2": "R²", "beta_regression": "Bêta"}),
            width="stretch")

# Statistiques d'echantillon
stat_cols = ["beta_regression", "r2", "ev_ebitda", "pe_trailing", "beta_unlevered"]
present = [c for c in stat_cols if c in df.columns]
if present:
    st.subheader("Médianes de l'échantillon")
    med = df[present].median(numeric_only=True).rename(index=labels)
    st.dataframe(med.to_frame("Médiane"), width="stretch")

# Export Excel + historisation
col_dl, col_save = st.columns(2)
with col_dl:
    st.download_button(
        "📥 Télécharger l'Excel",
        data=build_excel_bytes(records),
        file_name="comparables_boursiers.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
with col_save:
    if st.button("💾 Enregistrer dans l'historique"):
        tk = st.session_state["params"]["tickers"]
        label = ", ".join(tk[:4]) + ("…" if len(tk) > 4 else "")
        rid = store.save_run(records, username=(auth_user[0] if auth_user else None),
                             label=label, params=st.session_state["params"])
        st.session_state["saved_run_id"] = rid
    if st.session_state.get("saved_run_id"):
        st.success(f"Analyse enregistrée (#{st.session_state['saved_run_id']}). "
                   "Retrouvez-la dans l'onglet **Historique**.")
