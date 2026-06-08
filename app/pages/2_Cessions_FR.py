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
from comparables.fr import pipeline, store_fr
from comparables.fr.parsing import (robust_mask, robust_values, robust_median,
                                    parse_naf_filters, naf_codes_for,
                                    PCT_CA_BOUNDS, MULT_EBE_BOUNDS)

st.set_page_config(page_title="Cessions FR", layout="wide")
require_authentication()
st.title("Cessions de fonds de commerce — France")
st.caption("Prix de cession en % du CA et en multiple d'EBE. BODACC (prix) + Ratios INPI/BCE "
           "(CA, EBE, ~10 ans). Toutes entreprises françaises ; couverture financière partielle "
           "(comptes confidentiels exclus).")

with st.sidebar:
    st.header("Filtres")
    source = st.radio(
        "Source", ["API en direct", "Base locale (rapide)"],
        help="Base locale = corpus pré-ingéré (instantané, hors quota). À alimenter via "
             "`python -m comparables.fr.ingest`.")
    activite = st.text_input(
        "Activité (un ou plusieurs termes)", "boulangerie",
        help="Plusieurs termes = OU (ex : « menuiserie, charpente » ou « bar tabac »). "
             "Guillemets pour une expression exacte (ex : \"salon de coiffure\"). Vide = toutes.")
    elargir = st.checkbox(
        "Élargir aux métiers proches (synonymes)", value=True,
        help="menuiserie → charpente, agencement, fermetures… (multiplie le gisement).")
    naf_filtre = st.text_input(
        "Filtrer par code NAF (optionnel)", "",
        help="Garde uniquement le secteur visé, après identification. Codes exacts, préfixes ou "
             "liste : « 43.32A », « 43 », « 43.32A, 16.23Z ». Écarte les faux positifs du mot-clé.")
    departement = st.text_input("Département (optionnel)", "", help="Code, ex : 75, 33…")
    annees = st.slider("Fenêtre (années)", 1, 10, 10)
    limit = st.slider("Nombre de cessions à retenir", 10, 200, 50, step=10)
    inclure_sans_ca = st.checkbox(
        "Inclure les sociétés sans donnée financière", value=False,
        help="Par défaut, seules les cessions avec CA ou EBE public sont retenues.")
    mono_etab = st.checkbox(
        "Décocher les multi-établissements par défaut", value=True,
        help="Le prix porte sur UN fonds ; si la société a plusieurs établissements, son CA/EBE "
             "couvre tout le groupe → ratio faussé. Décoché par défaut (recochable à la main).")
    run = st.button("Analyser les cessions", type="primary")

if run:
    since = pipeline.default_since(annees)
    manual_naf = parse_naf_filters(naf_filtre.strip())
    auto_naf = naf_codes_for(activite) if not manual_naf else []   # NAF auto si métier reconnu
    naf_f = manual_naf or auto_naf or None
    local = source.startswith("Base locale")
    stats: dict = {"naf_applied": naf_f, "naf_auto": bool(auto_naf and not manual_naf)}
    if local:
        terms = pipeline.resolve_terms(activite.strip() or None, expand=elargir)
        with st.spinner("Lecture de la base locale…"):
            cessions = store_fr.load_cessions(
                terms=terms or None, naf_filters=naf_f,
                departement=departement.strip() or None, since=since,
                require_financials=not inclure_sans_ca, limit=limit)
        stats.update({"terms": terms, "local": True, "n_returned": len(cessions)})
    else:
        msg = "Récupération et croisement avec les comptes (peut prendre un moment)…"
        with st.spinner(msg):
            cessions = pipeline.build_cessions(
                departement=departement.strip() or None,
                contains=activite.strip() or None,
                since=since, limit=limit, require_ca=not inclure_sans_ca,
                expand=elargir, naf_filters=naf_f, stats=stats)
    st.session_state["fr_cessions"] = cessions
    st.session_state["fr_stats"] = stats
    st.session_state.pop("cess_editor", None)      # repart d'une sélection par défaut

if "fr_cessions" not in st.session_state:
    st.info("Choisissez les filtres puis « Analyser les cessions ».")
    st.stop()

# Funnel de recherche : où se perd l'échantillon (transparence).
stats = st.session_state.get("fr_stats") or {}
if stats:
    terms = stats.get("terms") or []
    if terms:
        st.caption("🔎 Termes recherchés (OU) : " + ", ".join(f"`{t}`" for t in terms))
    naf_applied = stats.get("naf_applied")
    if naf_applied:
        lib = " (métier reconnu)" if stats.get("naf_auto") else ""
        st.caption("🎯 Filtre NAF" + lib + " : " + ", ".join(f"`{n}`" for n in naf_applied)
                   + (" — videz/ajustez le champ « code NAF » pour élargir." if stats.get("naf_auto") else ""))
    if activite.strip() and not terms:
        st.warning("Le terme saisi correspond à du texte juridique présent dans presque toutes les "
                   "annonces (ex. « publicité », « avis ») ou est trop générique : il a été **ignoré** "
                   "pour la recherche texte. Affinez le terme ou utilisez le filtre NAF.")
    if stats.get("local"):
        db = store_fr.get_stats()
        maj = f" (maj {db['last_ingest']})" if db.get("last_ingest") else ""
        st.caption(
            f"🗃️ Base locale{maj} : **{db['n_cessions']}** cessions, "
            f"**{db['n_companies']}** sociétés enrichies"
            + (f", {db['date_min']}→{db['date_max']}" if db.get("date_min") else "")
            + f" · **{stats.get('n_returned', 0)}** retenue(s) pour ces filtres.")
        if db["n_cessions"] == 0:
            st.warning("Base locale vide. Alimentez-la : `python -m comparables.fr.ingest "
                       "--contains \"" + (activite.strip() or "boulangerie") + "\"`")
    else:
        n_ex = stats.get("n_examined", 0)
        n_ca = stats.get("n_ca_public", 0)
        cov = f" ({n_ca / n_ex * 100:.0f}%)" if n_ex else ""
        st.caption(
            f"📊 Funnel : **{n_ex}** annonce(s) avec prix examinée(s) · "
            f"**{n_ca}** avec CA public{cov} · **{stats.get('n_ebe_public', 0)}** avec EBE public · "
            f"**{stats.get('n_returned', 0)}** retenue(s). "
            + ("Gisement limité pour ce métier : élargissez les termes/synonymes, la fenêtre, "
               "ou cochez « Inclure les sociétés sans donnée financière »."
               if stats.get("n_returned", 0) < limit else ""))

cessions = st.session_state["fr_cessions"]
if not cessions:
    st.warning("Aucune cession exploitable pour ces critères. Pistes : élargir la fenêtre ou les "
               "termes ; ajuster/vider le filtre NAF. ⚠️ Certains métiers (services, professions "
               "libérales : agences de publicité, conseil, etc.) **ne se cèdent pas en fonds de "
               "commerce** mais en *titres* (hors BODACC) → peu ou pas de données ici.")
    st.stop()

# Sélection par défaut = ensemble « règle d'or » (bornes + non-outlier MAD) sur prix/CA ou × EBE.
pct_mask = robust_mask([c.pct_ca for c in cessions], PCT_CA_BOUNDS)
ebe_mask = robust_mask([c.mult_ebe for c in cessions], MULT_EBE_BOUNDS)
default_retenu = [pct_mask[i] or ebe_mask[i] for i in range(len(cessions))]
if mono_etab:
    # Biais fonds vs entité : décoche par défaut les sociétés à plusieurs établissements
    # (leur CA/EBE couvre tout le groupe, pas le seul fonds cédé). Recochables à la main.
    default_retenu = [keep and (cessions[i].nb_etablissements or 1) <= 1
                      for i, keep in enumerate(default_retenu)]

editor_df = pd.DataFrame([{
    "Retenu": default_retenu[i],
    "Société": c.nom, "SIREN": c.siren, "Ville": c.ville, "Dépt": c.departement, "Date": c.date,
    "Prix (€)": c.prix, "CA (€)": c.ca, "EBE (€)": c.ebe, "Exercice": c.ca_annee,
    "% de CA": round(c.pct_ca * 100, 1) if c.pct_ca is not None else None,
    "× EBE": round(c.mult_ebe, 1) if c.mult_ebe is not None else None,
    "Étab.": c.nb_etablissements, "NAF": c.naf, "Annonce BODACC": c.url,
} for i, c in enumerate(cessions)])

metrics_box = st.container()
st.markdown("**Cessions** — cochez/décochez la colonne *Retenu* ; les médianes se recalculent.")
edited = st.data_editor(
    editor_df, hide_index=True, width="stretch", key="cess_editor",
    column_config={"Retenu": st.column_config.CheckboxColumn(
        "Retenu", help="Inclure cette cession dans les médianes", default=True)},
    disabled=[col for col in editor_df.columns if col != "Retenu"])

# Recalcul des agrégats EN DIRECT sur la sélection.
# Chaque médiane n'utilise que les valeurs plausibles de SA métrique (bande + non-aberrant) :
# une ligne retenue pour son %CA ne pollue plus la médiane ×EBE avec un multiple hors-bande.
sel = edited[edited["Retenu"].fillna(False)]
pct_list = (sel["% de CA"].dropna() / 100.0).tolist()
ebe_list = sel["× EBE"].dropna().tolist()
prix = sel["Prix (€)"].dropna()
med_pct, n_pct = robust_median(pct_list, PCT_CA_BOUNDS)
med_ebe, n_ebe = robust_median(ebe_list, MULT_EBE_BOUNDS)
pct_kept, _ = robust_values(pct_list, PCT_CA_BOUNDS)         # pour l'histogramme
with metrics_box:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Cessions retenues", int(len(sel)))
    m2.metric("Médiane prix / CA", f"{med_pct * 100:.0f} %" if med_pct is not None else "n.d.",
              help=f"sur {n_pct} valeur(s) dans la bande 5–400 % (extrêmes exclus)")
    m3.metric("Médiane × EBE", f"{med_ebe:.1f}x" if med_ebe is not None else "n.d.",
              help=f"sur {n_ebe} valeur(s) dans la bande 0,5–15x (extrêmes exclus)")
    m4.metric("Prix médian", f"{prix.median():,.0f} €".replace(",", " ") if not prix.empty else "n.d.")
    st.caption(f"ℹ️ Médianes calculées par métrique sur ses seules valeurs plausibles "
               f"(× EBE : n={n_ebe} · prix/CA : n={n_pct}). "
               "Une ligne au %CA correct mais au ×EBE aberrant ne fausse plus le multiple.")
    n_off = sum(1 for i, c in enumerate(cessions)
                if not default_retenu[i] and (c.pct_ca is not None or c.mult_ebe is not None))
    if n_off:
        st.caption(f"🛡️ Règle d'or : {n_off} cession(s) hors fourchette / extrême(s) décochée(s) "
                   "par défaut — cochez-les pour les réintégrer.")

# Barème par activité + distribution, recalculés sur la sélection
col_a, col_b = st.columns([1, 1])
with col_a:
    base = sel.dropna(subset=["% de CA"]).copy()
    if not base.empty:
        st.subheader("Barème par activité (sélection)")
        # Médianes par NAF sur les seules valeurs DANS la bande (même cohérence que les KPIs).
        base["_pct"] = base["% de CA"].where(
            base["% de CA"].between(PCT_CA_BOUNDS[0] * 100, PCT_CA_BOUNDS[1] * 100))
        base["_ebe"] = base["× EBE"].where(
            base["× EBE"].between(MULT_EBE_BOUNDS[0], MULT_EBE_BOUNDS[1]))
        g = (base.assign(NAF=base["NAF"].fillna("(inconnu)"))
             .groupby("NAF").agg(n=("_pct", "count"), pct=("_pct", "median"),
                                 ebe=("_ebe", "median"), prix=("Prix (€)", "median"))
             .reset_index().sort_values("n", ascending=False))
        g = g[g["n"] > 0]
        g["% de CA (méd.)"] = g["pct"].round(0)
        g["× EBE (méd.)"] = g["ebe"].round(1)
        g["Prix médian (€)"] = g["prix"].round(0)
        st.dataframe(g[["NAF", "n", "% de CA (méd.)", "× EBE (méd.)", "Prix médian (€)"]],
                     width="stretch", hide_index=True)
with col_b:
    if pct_kept:
        st.subheader("Distribution prix / CA (sélection)")
        st.plotly_chart(px.histogram(pd.DataFrame({"% de CA": [v * 100 for v in pct_kept]}),
                                      x="% de CA", nbins=20,
                                      labels={"% de CA": "Prix en % du CA"}), width="stretch")

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
