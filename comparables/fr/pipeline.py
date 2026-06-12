"""Orchestration cessions FR : activité interprétée (mots-clés + NAF) -> BODACC (prix +
SIREN) -> filtre NAF -> finances INPI (CA/EBE, exercice calé sur la cession) + identité
-> prix/CA et prix/EBE, avec compteurs d'entonnoir (traçabilité du « 0 résultat »)."""
from __future__ import annotations
import logging
from datetime import date
from typing import Callable, Optional

import pandas as pd

from comparables.fr import activites, bodacc, entreprises, finances_inpi, referentiels
from comparables.fr.comptes import bilan_saisi, cascade, inpi_client
from comparables.fr.models import Cession, CessionsBatch
from comparables.fr.parsing import compute_pct_ca, compute_mult_ebe, summarize_by_activity

logger = logging.getLogger(__name__)

__all__ = ["build_cessions", "summarize_by_activity", "to_dataframe", "default_since"]

# Filet « comptes déposés INPI » : budget de sociétés tentées par lot (chaque tentative
# = 1 à 3 appels RNE cadencés à >= 0,5 s — sans plafond, une recherche de niche sur la
# fenêtre 2008- peut durer des heures) et plancher de date de cession (le RNE n'a
# pratiquement aucun compte déposé avant 2017 : appels à fonds perdus).
_RNE_BUDGET_LOT = 150
_RNE_COMPTES_DEPUIS = "2017-01-01"


def default_since(years: int = 10) -> str:
    """Date 'YYYY-MM-DD' il y a `years` ans (fenêtre d'analyse par défaut)."""
    today = date.today()
    return today.replace(year=today.year - years).isoformat()


def _recule_un_an(d: date) -> date:
    try:
        return d.replace(year=d.year - 1)
    except ValueError:                      # 29 février
        return d.replace(year=d.year - 1, day=28)


def _fenetres_annuelles(since: str) -> list[tuple[str, Optional[str]]]:
    """Tranches d'un an [(début, fin exclue), …] du plus récent au plus ancien,
    de aujourd'hui jusqu'à `since`. La 1re tranche n'a pas de borne haute."""
    out: list[tuple[str, Optional[str]]] = []
    fin: Optional[date] = None
    borne = date.today()
    while borne.isoformat() > since:
        debut = max(_recule_un_an(borne), date.fromisoformat(since))
        out.append((debut.isoformat(), fin.isoformat() if fin else None))
        fin = borne = debut
    return out


def _apply_identity(c: Cession, id_cache: dict[str, Optional[dict]],
                    local: bool = False) -> None:
    """Complète nom / NAF / activité : référentiel Sirene local si chargé (instantané,
    sans quota), sinon API Recherche d'entreprises. Échec isolé, résultat caché."""
    if not c.siren:
        return
    if c.siren not in id_cache:
        info = None
        try:
            if local:
                info = referentiels.lookup_company(c.siren)
            if info is None:                    # base locale absente ou SIREN inconnu
                info = entreprises.fetch_company(c.siren)
        except Exception as exc:
            logger.warning("Echec identité SIREN %s : %s", c.siren, exc)
        id_cache[c.siren] = info
    info = id_cache[c.siren]
    if info:
        c.nom = info.get("nom") or c.nom
        c.naf = info.get("naf")
        c.activite = info.get("naf")


def build_cessions(departement: Optional[str] = None, contains: Optional[str] = None,
                   since: Optional[str] = None, limit: int = 50, enrich: bool = True,
                   require_ca: bool = True, max_scan: Optional[int] = None,
                   progress: Optional[Callable[[int, int], None]] = None) -> CessionsBatch:
    """Récupère des cessions (prix) et calcule prix/CA et prix/EBE quand disponibles.

    `contains` est un texte libre (« conseil en informatique », « boulangerie », « 62.02A ») :
    il est interprété en mots-clés combinés en OU pour le BODACC + codes NAF cibles
    (cf. `activites.interpret`). Quand des NAF sont ciblés, l'identité de la cédante est
    récupérée AVANT ses finances et l'annonce est écartée si l'activité ne correspond pas
    (sauf si son nom porte un mot-clé de la recherche).

    Avec les référentiels locaux chargés (ventes BODACC + Sirene), la recherche est une
    JOINTURE locale exhaustive sur toute la fenêtre (prix et NAF déjà résolus) ; sinon,
    balayage de l'API par passes (mots-clés, puis générique si l'identité est locale).

    require_ca=True : ne renvoie QUE les sociétés dont le CA est disponible (comptes publics),
    en sur-balayant le BODACC (jusqu'à max_scan cessions) pour en réunir `limit`. L'échec
    d'une société n'arrête pas le lot. Renvoie un `CessionsBatch` (cessions + compteurs).
    `progress(traitées, balayées)` est appelé au fil de l'enrichissement (suivi de job).
    """
    query = activites.interpret(contains) if contains and contains.strip() else None
    naf_filter = bool(query and query.naf_codes and enrich)
    # Référentiels locaux (Sirene / ratios BCE / ventes BODACC) : lookups instantanés
    # quand chargés, repli automatique sur les API unitaires sinon (fr/referentiels.py).
    local_id = referentiels.available("unites_legales") if enrich else False
    local_fin = referentiels.available("ratios") if enrich else False

    # Voie royale : ventes BODACC répliquées en local + identité Sirene locale ->
    # la recherche par activité est une JOINTURE exhaustive (toute la fenêtre, prix
    # déjà extraits, NAF déjà joints), sans pagination ni balayage par mots-clés.
    pool: list[Cession] = []
    pool_local = False
    if naf_filter and local_id and referentiels.available("ventes"):
        ventes = referentiels.lookup_ventes(since=since or default_since(),
                                            departement=departement)
        if ventes is not None:
            pool_local = True
            pool = [Cession(siren=v["siren"], nom=v["nom_officiel"] or v["nom_bodacc"],
                            ville=v["ville"], departement=v["departement"],
                            date=v["date"], categorie=v["categorie"], prix=v["prix"],
                            url=v["url"], naf=v["naf"], activite=v["naf"])
                    for v in ventes]
            max_scan = len(pool)

    if max_scan is None:
        if naf_filter and local_id:
            # Identité locale = filtrage NAF gratuit : on peut balayer très large
            # (la plupart des actes ne décrivent pas l'activité de la cédante).
            # La profondeur suit l'objectif : 50 visées -> 4 000 annonces (~1-2 min),
            # 200 -> 16 000 (~5-8 min, quasi-exhaustif sur 5 ans).
            max_scan = min(20000, max(limit * 80, 1000))
        elif naf_filter:
            # Les mots-clés larges ramènent beaucoup d'annonces hors cible (« matériel
            # informatique » dans un inventaire…) : la densité utile est faible, il faut
            # sur-balayer bien plus que pour le seul filtre CA.
            max_scan = min(1200, max(limit * 40, 200))
        elif require_ca:
            max_scan = min(600, max(limit * 12, limit))
        else:
            max_scan = limit
    if pool_local:
        pass                                # pool déjà construit par la jointure locale
    elif naf_filter:
        # Jusqu'à trois passes BODACC, de la plus précise à la plus large :
        # 1) le NOM du commerçant (« DUPONT INFORMATIQUE » exerce vraiment dans le
        #    domaine) ; 2) le texte de l'acte (haut rappel mais bruité : « matériel
        #    informatique » dans un inventaire de café…) ; 3) avec le référentiel
        #    Sirene local seulement : balayage GÉNÉRIQUE sans mots-clés — la plupart
        #    des actes ne nomment pas l'activité, seul le filtre NAF la voit.
        pool = bodacc.fetch_cessions(departement=departement, keywords=query.keywords,
                                     since=since or default_since(), limit=max_scan,
                                     search_in=("commercant",))
        deja = {(c.siren, c.prix) for c in pool}

        def _complete(fetched: list[Cession]) -> None:
            for c in fetched:
                if (c.siren, c.prix) not in deja and len(pool) < max_scan:
                    deja.add((c.siren, c.prix))
                    pool.append(c)

        if len(pool) < max_scan:
            _complete(bodacc.fetch_cessions(departement=departement,
                                            keywords=query.keywords,
                                            since=since or default_since(),
                                            limit=max_scan - len(pool),
                                            search_in=("acte",)))
        if local_id and len(pool) < max_scan:
            # Par tranches d'un an, du plus récent au plus ancien : chaque tranche
            # repart à zéro dans la pagination BODACC (plafonnée à ~10 000 annonces
            # par requête, bien moins que le gisement « ventes avec prix »).
            for debut, fin in _fenetres_annuelles(since or default_since()):
                if len(pool) >= max_scan:
                    break
                _complete(bodacc.fetch_cessions(departement=departement, since=debut,
                                                until=fin, limit=max_scan - len(pool)))
    else:
        pool = bodacc.fetch_cessions(departement=departement,
                                     keywords=query.keywords if query else None,
                                     since=since or default_since(), limit=max_scan)
    batch = CessionsBatch(n_annonces=len(pool),
                          keywords=query.keywords if query else [],
                          naf_codes=query.naf_codes if query else [],
                          naf_labels=query.naf_labels if query else [])
    if not enrich:
        batch.cessions = pool[:limit]
        return batch

    out: list[Cession] = []
    fin_cache: dict[str, list] = {}
    id_cache: dict[str, Optional[dict]] = {}
    rne_tentees = 0
    total = len(pool)
    done = 0
    if progress:
        progress(0, total)

    def _tick() -> None:
        nonlocal done
        done += 1
        if progress:
            progress(done, total)

    # Un seul client INPI authentifié pour tout le lot : on se connecte une fois et on
    # réutilise le jeton (sinon une connexion par SIREN -> blocage par le RNE).
    inpi = inpi_client.InpiClient() if inpi_client.configured() else None
    for c in pool:
        # 0) Filtre d'activité : identité (NAF) AVANT les finances — précision du ciblage
        #    et économie d'appels INPI (on n'interroge que les annonces pertinentes).
        #    Le repêchage par le nom ne se fonde QUE sur le nom officiel de la cédante :
        #    le champ `commercant` BODACC mêle cédant et cessionnaire (un acheteur
        #    « X INFORMATIQUE » ne rend pas la cible informatique).
        if naf_filter:
            if pool_local:
                # Identité déjà jointe (Sirene) : NAF présent <=> cédante identifiée.
                nom_cedant = c.nom if c.naf is not None else None
            else:
                _apply_identity(c, id_cache, local=local_id)
                nom_cedant = c.nom if (c.siren and id_cache.get(c.siren)) else None
            if not activites.keep_cession(c.naf, nom_cedant, query):
                batch.n_naf_exclues += 1
                _tick()
                continue
        # 1) Finances (CA/EBE) de l'exercice calé sur la date de cession
        if c.siren:
            try:
                if c.siren not in fin_cache:
                    rows = referentiels.lookup_financials(c.siren) if local_fin else None
                    if rows is None:        # base locale indisponible -> API unitaire
                        rows = finances_inpi.fetch_financials(c.siren)
                    fin_cache[c.siren] = rows
                fin = finances_inpi.pick_for_date(fin_cache[c.siren], c.date)
            except Exception as exc:
                logger.warning("Echec finances SIREN %s : %s", c.siren, exc)
                fin = None
            if fin:
                c.ca = fin.get("chiffre_d_affaires")
                c.ebe = fin.get("ebe")
                c.ebit = fin.get("ebit")
                cloture = fin.get("date_cloture_exercice") or ""
                c.ca_annee = int(cloture[:4]) if cloture[:4].isdigit() else None
                c.pct_ca = compute_pct_ca(c.prix, c.ca)
                c.mult_ebe = compute_mult_ebe(c.prix, c.ebe)
        # 1bis) Comptes déposés INPI quand le dataset ratios n'a rien donné — inactif sans
        #        credentials INPI (lot 3). On privilégie le compte STRUCTURÉ (bilanSaisi,
        #        gratuit et déterministe) ; à défaut seulement, la cascade PDF/OCR/LLM.
        #        Budget par lot + plancher de date : cf. _RNE_BUDGET_LOT.
        if (c.siren and c.ca is None and inpi_client.configured()
                and (c.date or "") >= _RNE_COMPTES_DEPUIS and rne_tentees < _RNE_BUDGET_LOT):
            rne_tentees += 1
            extraction = None
            meta: Optional[dict] = None
            try:
                saisi = inpi_client.fetch_comptes_saisi(c.siren, before_date=c.date, client=inpi)
                if saisi:
                    res = bilan_saisi.extract(saisi[1])
                    if res and res.ca is not None:
                        extraction, meta = res, saisi[0]
                if extraction is None:                  # filet : PDF déposé
                    fetched = inpi_client.fetch_comptes_pdf(c.siren, before_date=c.date, client=inpi)
                    if fetched:
                        res = cascade.extract_comptes(fetched[1])
                        if res and res.ca is not None:
                            extraction, meta = res, fetched[0]
            except Exception as exc:
                logger.warning("Echec comptes déposés SIREN %s : %s", c.siren, exc)
                extraction, meta = None, None
            if extraction and meta:
                c.ca, c.ebe, c.ebit = extraction.ca, extraction.ebe, extraction.ebit
                cloture = meta.get("dateCloture") or ""
                c.ca_annee = int(cloture[:4]) if cloture[:4].isdigit() else None
                c.pct_ca = compute_pct_ca(c.prix, c.ca)
                c.mult_ebe = compute_mult_ebe(c.prix, c.ebe)
        # 2) Exclusion des sociétés sans CA disponible
        if require_ca and c.ca is None:
            batch.n_sans_ca += 1
            _tick()
            continue
        # 3) Identité (NAF, nom) — uniquement pour les cessions retenues (déjà faite si
        #    le filtre d'activité est actif)
        if not naf_filter:
            _apply_identity(c, id_cache, local=local_id)
        out.append(c)
        _tick()
        if len(out) >= limit:
            break
    # 4) Objet social RNE (détail d'activité, texte libre) pour les cessions RETENUES
    #    seulement — best-effort, jamais bloquant (cf. inpi_client.fetch_objet_social).
    if inpi_client.configured():
        for c in out:
            if c.siren:
                c.objet_social = inpi_client.fetch_objet_social(c.siren, client=inpi)
    # Compteurs exacts : « balayées » = annonces réellement traitées (la boucle s'arrête
    # à `limit` atteint — en jointure locale, le pool est la fenêtre entière).
    batch.n_annonces = done
    if progress and done < total:
        progress(done, done)
    batch.cessions = out
    return batch


def to_dataframe(cessions: list[Cession]) -> pd.DataFrame:
    return pd.DataFrame([c.model_dump() for c in cessions])
