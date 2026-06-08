"""Ingestion en masse des cessions FR dans la base locale SQLite (cf. store_fr).

Deux étapes, toutes deux RÉSUMABLES (relancer reprend là où on en est) :
  1. cessions   : export BODACC année par année -> table `cessions` (prix + SIREN) ;
  2. enrichment : pour les SIREN pas encore enrichis, identité (NAF, nb étab.) + finances
                  (CA/EBE/EBIT par exercice) -> tables `companies` / `financials`.

Exemples :
    python -m comparables.fr.ingest                      # 10 ans, tout métier, puis enrichit 500 SIREN
    python -m comparables.fr.ingest --contains menuiserie --years 10
    python -m comparables.fr.ingest --enrich-only --max-enrich 2000
    python -m comparables.fr.ingest --no-enrich         # ingère seulement les cessions

L'enrichissement fait 2 appels réseau par SIREN : sur tout le corpus national (~dizaines de
milliers), le lancer par tranches (--max-enrich) et relancer. Les appels passent par le cache HTTP.
"""
from __future__ import annotations
import argparse
import logging
import time
from datetime import date

from comparables.fr import bodacc, entreprises, finances_inpi, store_fr
from comparables.fr.pipeline import default_since, resolve_terms

logger = logging.getLogger("comparables.fr.ingest")


def _year_bounds(since: str, until: str) -> list[tuple[str, str]]:
    """Découpe [since, until] en tranches annuelles (réponses d'export raisonnables)."""
    y0, y1 = int(since[:4]), int(until[:4])
    out = []
    for y in range(y0, y1 + 1):
        out.append((max(since, f"{y}-01-01"), min(until, f"{y}-12-31")))
    return out


def ingest_cessions(contains: str | None = None, departement: str | None = None,
                    years: int = 10, expand: bool = True, db_path: str | None = None) -> int:
    """Ingère les cessions (prix) de la fenêtre, année par année. Renvoie le nb upserté."""
    since = default_since(years)
    until = date.today().isoformat()
    terms = resolve_terms(contains, expand=expand) or None
    total = 0
    for start, end in _year_bounds(since, until):
        cessions = bodacc.fetch_cessions_bulk(departement=departement, terms=terms,
                                              since=start, until=end)
        store_fr.upsert_cessions(cessions, db_path=db_path)
        total += len(cessions)
        logger.info("Cessions %s..%s : %d (cumul %d)", start, end, len(cessions), total)
    store_fr.set_meta("last_ingest", date.today().isoformat(), db_path=db_path)
    return total


def enrich(max_n: int | None = None, db_path: str | None = None, delay: float = 0.3) -> int:
    """Enrichit les SIREN pas encore identifiés (identité + finances). Renvoie le nb identifié.

    Robuste au rate-limiting : `delay` espace les appels (recherche-entreprises ~7 req/s) et la
    session retente les 429 (cf. cache.get_session). Une société n'est marquée « enrichie » QUE si
    son identité aboutit ; un échec transitoire la laisse dans la file (réessayée au prochain run).
    """
    sirens = store_fr.sirens_without_company(limit=max_n, db_path=db_path)
    logger.info("À enrichir : %d SIREN", len(sirens))
    done = failed = 0
    for s in sirens:
        try:                                           # finances : best-effort, idempotent
            store_fr.upsert_financials(s, finances_inpi.fetch_financials(s), db_path=db_path)
        except Exception as exc:
            logger.warning("Finances %s : %s", s, exc)
        try:                                           # identité : marque le SIREN comme traité
            store_fr.upsert_company(s, entreprises.fetch_company(s), db_path=db_path)
            done += 1
        except Exception as exc:                       # échec transitoire -> NON marqué, à réessayer
            failed += 1
            logger.warning("Identité %s (à réessayer) : %s", s, exc)
        if delay:
            time.sleep(delay)
        if done and done % 100 == 0:
            logger.info("  enrichis : %d (à réessayer : %d)", done, failed)
    logger.info("Enrichissement : %d identifiés, %d à réessayer", done, failed)
    return done


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Ingestion locale des cessions FR (BODACC + INPI).")
    p.add_argument("--contains", default=None, help="Limiter à un métier (sinon tout).")
    p.add_argument("--departement", default=None, help="Limiter à un département (ex 75).")
    p.add_argument("--years", type=int, default=10, help="Profondeur d'historique (défaut 10).")
    p.add_argument("--no-expand", action="store_true", help="Ne pas élargir aux synonymes.")
    p.add_argument("--no-enrich", action="store_true", help="Ingérer les cessions sans enrichir.")
    p.add_argument("--enrich-only", action="store_true", help="Sauter l'ingestion, enrichir seulement.")
    p.add_argument("--max-enrich", type=int, default=500, help="Plafond de SIREN à enrichir (défaut 500).")
    p.add_argument("--delay", type=float, default=0.3, help="Pause entre SIREN (anti rate-limit, défaut 0.3s).")
    p.add_argument("--db", default=None, help="Chemin de base SQLite (défaut: settings.cessions_db_path).")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not args.enrich_only:
        n = ingest_cessions(contains=args.contains, departement=args.departement,
                            years=args.years, expand=not args.no_expand, db_path=args.db)
        logger.info("Cessions ingérées : %d", n)
    if not args.no_enrich:
        n = enrich(max_n=args.max_enrich, db_path=args.db, delay=args.delay)
        logger.info("SIREN enrichis : %d", n)
    logger.info("Base : %s", store_fr.get_stats(db_path=args.db))


if __name__ == "__main__":
    main()
