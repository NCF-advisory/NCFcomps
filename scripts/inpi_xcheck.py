"""Validation croisée : extraction structurée (bilanSaisi) vs dataset ratios INPI/BCE.

Sur de vraies sociétés (SIREN issus du BODACC), compare le CA/EBE calculé depuis les
comptes structurés à celui du dataset ratios_inpi_bce pour le même exercice. Si les
deux coïncident, le choix de colonne (m1/m3) et l'échelle (euros) sont validés sur des
sociétés opérationnelles (ce que Danone, holding, ne permettait pas).

Données publiques. Usage : .venv/bin/python scripts/inpi_xcheck.py [nb_comparaisons]
"""
from __future__ import annotations

import sys

from comparables.fr import bodacc, finances_inpi
from comparables.fr.comptes import bilan_saisi, inpi_client


def main() -> int:
    want = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    cessions = bodacc.fetch_cessions(since="2016-01-01", limit=120)
    sirens = [c.siren for c in cessions if c.siren]
    print(f"{len(sirens)} SIREN issus du BODACC ; recherche de {want} comparaisons…\n")

    client = inpi_client.InpiClient()
    done = 0
    for siren in sirens:
        if done >= want:
            break
        try:
            ratios = finances_inpi.fetch_financials(siren)
        except Exception:
            continue
        ratios_by_year = {(r.get("date_cloture_exercice") or "")[:4]: r
                          for r in ratios if r.get("chiffre_d_affaires")}
        if not ratios_by_year:
            continue
        saisi = inpi_client.fetch_comptes_saisi(siren, client=client)
        if not saisi:
            continue
        meta, payload = saisi
        year = (meta.get("dateCloture") or "")[:4]
        ref = ratios_by_year.get(year)
        res = bilan_saisi.extract(payload)
        print(f"SIREN {siren}  exercice {year}  (type {meta.get('typeBilan')}, {meta.get('confidentiality')})")
        if res is None:
            print("   structuré : régime indétectable\n")
            continue
        print(f"   structuré : CA={_f(res.ca)}  EBE={_f(res.ebe)}  EBIT={_f(res.ebit)}  ({res.regime})")
        if ref:
            print(f"   ratios    : CA={_f(ref.get('chiffre_d_affaires'))}  "
                  f"EBE={_f(ref.get('ebe'))}  EBIT={_f(ref.get('ebit'))}")
            if res.ca and ref.get("chiffre_d_affaires"):
                ecart = abs(res.ca - ref["chiffre_d_affaires"]) / ref["chiffre_d_affaires"]
                verdict = "✓ COHÉRENT" if ecart < 0.02 else f"✗ écart {ecart:.0%}"
                print(f"   CA : {verdict}")
        else:
            print(f"   ratios    : pas d'exercice {year} (années dispo : {sorted(ratios_by_year)})")
        print()
        done += 1
    print(f"{done} comparaison(s) effectuée(s).")
    return 0


def _f(v) -> str:
    return f"{v:,.0f}".replace(",", " ") if isinstance(v, (int, float)) else "—"


if __name__ == "__main__":
    raise SystemExit(main())
