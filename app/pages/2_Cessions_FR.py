"""Onglet Cessions FR : prix de cession des fonds de commerce, en % du CA et en multiple d'EBE.

Couvre TOUTES les entreprises françaises (aucun filtre de taille). Sources publiques gratuites
sans clé : BODACC (prix + SIREN) + Ratios Financiers INPI/BCE (CA, EBE, multi-exercices).
En pratique le BODACC ne publie que des cessions de fonds de commerce (commerces, TPE/PME) ;
les grands groupes cèdent des titres (actes de greffe), hors de ce périmètre.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st
import plotly.express as px

from comparables.streamlit_auth import require_authentication
from comparables.fr import pipeline
from comparables.fr.parsing import robust_mask, PCT_CA_BOUNDS, MULT_EBE_BOUNDS

st.set_page_config(page_title="Cessions FR", layout="wide")
require_authentication()
st.title("Cessions de fonds de commerce — France")
st.caption("Prix de cession en % du CA et en multiple d'EBE. BODACC (prix) + Ratios INPI/BCE "
           "(CA, EBE, ~10 ans). Toutes entreprises françaises ; couverture financière partielle "
           "(comptes confidentiels exclus).")

with st.sidebar:
    st.header("Filtres")
    activite = st.text_input("Activité (texte libre)", "boulangerie",
                             help="Domaine, libellé ou code NAF (ex : conseil en informatique, "
                                  "restaurant, 62.02A) — traduit en mots-clés élargis + codes "
                                  "NAF cibles. Vide = toutes.")
    departement = st.text_input("Département (optionnel)", "", help="Code, ex : 75, 33…")
    annees = st.slider("Fenêtre (années)", 1, 10, 10)
    limit = st.slider("Nombre de cessions à retenir", 10, 80, 30, step=10)
    inclure_sans_ca = st.checkbox("Inclure les sociétés sans CA", value=False,
                                  help="Par défaut, seules les cessions avec CA disponible sont retenues.")
    run = st.button("Analyser les cessions", type="primary")

if run:
    since = pipeline.default_since(annees)
    msg = "Récupération et croisement avec les comptes (peut prendre un moment)…"
    with st.spinner(msg):
        batch = pipeline.build_cessions(
            departement=departement.strip() or None,
            contains=activite.strip() or None,
            since=since, limit=limit, require_ca=not inclure_sans_ca)
    st.session_state["fr_cessions"] = batch.cessions
    st.session_state["fr_batch"] = batch
    st.session_state.pop("cess_editor", None)      # repart d'une sélection par défaut

if "fr_cessions" not in st.session_state:
    st.info("Choisissez les filtres puis « Analyser les cessions ».")
    st.stop()

cessions = st.session_state["fr_cessions"]
batch = st.session_state.get("fr_batch")
if batch is not None and (batch.keywords or batch.n_annonces):
    parts = []
    if batch.keywords:
        parts.append("recherche élargie : " + " ou ".join(batch.keywords))
    if batch.naf_labels:
        extra = f" (+{len(batch.naf_codes) - 3})" if len(batch.naf_codes) > 3 else ""
        parts.append("NAF ciblés : " + " ; ".join(batch.naf_labels[:3]) + extra)
    parts.append(f"{batch.n_annonces} annonces avec prix balayées")
    if batch.n_naf_exclues:
        parts.append(f"{batch.n_naf_exclues} hors activité")
    if batch.n_sans_ca:
        parts.append(f"{batch.n_sans_ca} sans CA exploitable")
    parts.append(f"{len(cessions)} retenue(s)")
    st.caption("🔎 " + " · ".join(parts))
if not cessions:
    if batch is not None and batch.n_annonces == 0:
        st.warning("Aucune annonce BODACC ne correspond à ces mots-clés sur la période. "
                   "Le BODACC ne publie que les ventes de fonds de commerce : certaines "
                   "activités (services B2B…) se vendent surtout par cession de titres, hors "
                   "de ce périmètre. Élargissez le terme, le département ou la fenêtre.")
    elif batch is not None and batch.n_sans_ca:
        st.warning(f"{batch.n_annonces} annonce(s) trouvée(s) mais aucune exploitable : "
                   f"{batch.n_sans_ca} sans CA disponible (comptes confidentiels). Cochez "
                   "« Inclure les sociétés sans CA » ou élargissez la fenêtre.")
    else:
        st.warning("Aucune cession avec prix trouvée pour ces critères. Élargissez l'activité, "
                   "le département ou la fenêtre.")
    st.stop()

# Sélection par défaut = ensemble « règle d'or » (bornes + non-outlier MAD) sur prix/CA ou × EBE.
pct_mask = robust_mask([c.pct_ca for c in cessions], PCT_CA_BOUNDS)
ebe_mask = robust_mask([c.mult_ebe for c in cessions], MULT_EBE_BOUNDS)
default_retenu = [pct_mask[i] or ebe_mask[i] for i in range(len(cessions))]

editor_df = pd.DataFrame([{
    "Retenu": default_retenu[i],
    "Société": c.nom, "Ville": c.ville, "Dépt": c.departement, "Date": c.date,
    "Prix (€)": c.prix, "CA (€)": c.ca, "EBE (€)": c.ebe, "Exercice": c.ca_annee,
    "% de CA": round(c.pct_ca * 100, 1) if c.pct_ca is not None else None,
    "× EBE": round(c.mult_ebe, 1) if c.mult_ebe is not None else None,
    "NAF": c.naf,
} for i, c in enumerate(cessions)])

metrics_box = st.container()
st.markdown("**Cessions** — cochez/décochez la colonne *Retenu* ; les médianes se recalculent.")
edited = st.data_editor(
    editor_df, hide_index=True, width="stretch", key="cess_editor",
    column_config={"Retenu": st.column_config.CheckboxColumn(
        "Retenu", help="Inclure cette cession dans les médianes", default=True)},
    disabled=[col for col in editor_df.columns if col != "Retenu"])

# Recalcul des agrégats EN DIRECT sur la sélection
sel = edited[edited["Retenu"].fillna(False)]
pct = (sel["% de CA"].dropna() / 100.0)
ebe = sel["× EBE"].dropna()
prix = sel["Prix (€)"].dropna()
with metrics_box:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Cessions retenues", int(len(sel)))
    m2.metric("Médiane prix / CA", f"{pct.median() * 100:.0f} %" if not pct.empty else "n.d.")
    m3.metric("Médiane × EBE", f"{ebe.median():.1f}x" if not ebe.empty else "n.d.")
    m4.metric("Prix médian", f"{prix.median():,.0f} €".replace(",", " ") if not prix.empty else "n.d.")
    n_off = sum(1 for i, c in enumerate(cessions)
                if not default_retenu[i] and (c.pct_ca is not None or c.mult_ebe is not None))
    if n_off:
        st.caption(f"🛡️ Règle d'or : {n_off} cession(s) hors fourchette / extrême(s) décochée(s) "
                   "par défaut — cochez-les pour les réintégrer.")

# Barème par activité + distribution, recalculés sur la sélection
col_a, col_b = st.columns([1, 1])
with col_a:
    base = sel.dropna(subset=["% de CA"])
    if not base.empty:
        st.subheader("Barème par activité (sélection)")
        g = (base.assign(NAF=base["NAF"].fillna("(inconnu)"))
             .groupby("NAF").agg(n=("% de CA", "size"), pct=("% de CA", "median"),
                                 ebe=("× EBE", "median"), prix=("Prix (€)", "median"))
             .reset_index().sort_values("n", ascending=False))
        g["% de CA (méd.)"] = g["pct"].round(0)
        g["× EBE (méd.)"] = g["ebe"].round(1)
        g["Prix médian (€)"] = g["prix"].round(0)
        st.dataframe(g[["NAF", "n", "% de CA (méd.)", "× EBE (méd.)", "Prix médian (€)"]],
                     width="stretch", hide_index=True)
with col_b:
    if not pct.empty:
        st.subheader("Distribution prix / CA (sélection)")
        st.plotly_chart(px.histogram(pd.DataFrame({"% de CA": pct.values * 100}), x="% de CA",
                                      nbins=20, labels={"% de CA": "Prix en % du CA"}),
                        width="stretch")

st.download_button("📥 Exporter la sélection (CSV)",
                   data=sel.drop(columns=["Retenu"]).to_csv(index=False).encode("utf-8-sig"),
                   file_name="cessions_fonds_commerce_fr.csv", mime="text/csv")

with st.expander("⚠️ Lire avant d'utiliser — portée et limites"):
    st.markdown(
        "- **Périmètre** : toutes les entreprises françaises, mais le BODACC ne publie que les "
        "**cessions de fonds de commerce** (commerces / TPE-PME). Les grands groupes cèdent des "
        "**titres** (actes de greffe) — hors de ce périmètre.\n"
        "- **Prix** : extrait du texte libre des annonces (« moyennant le prix de … »), best-effort.\n"
        "- **CA / EBE** : jeu Ratios INPI/BCE, exercice calé sur la date de cession. **Indisponibles "
        "pour les comptes confidentiels** (~45 % des dépôts) → couverture partielle.\n"
        "- **Sélection (colonne *Retenu*)** : par défaut, on coche l'ensemble « règle d'or » — "
        "prix/CA entre 5 % et 400 %, multiple d'EBE entre 0,5x et 15x, **et** hors extrêmes "
        "statistiques (z-score modifié sur la MAD, en log, dès 8 points). Décochez/cochez pour "
        "ajuster : les médianes se recalculent en direct sur votre sélection.\n"
        "- Ordres de grandeur indicatifs, à croiser avec le jugement d'un analyste.")
