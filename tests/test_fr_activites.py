"""Tests de l'interprétation d'activité (texte libre -> mots-clés + NAF). Aucun réseau."""
from __future__ import annotations

from comparables.fr.activites import (
    ActivityQuery,
    interpret,
    keep_cession,
    load_naf,
    load_naf_levels,
    normalize,
    tokens,
)


# --- nomenclature embarquée ---

def test_load_naf_complet():
    entries = load_naf()
    assert len(entries) == 732                      # niveau 5 de la NAF rev. 2 (INSEE)
    codes = dict(entries)
    assert codes["62.02A"] == "Conseil en systèmes et logiciels informatiques"
    assert codes["10.71C"] == "Boulangerie et boulangerie-pâtisserie"


def test_load_naf_levels_complet():
    par_niveau = {}
    for niveau, _, _ in load_naf_levels():
        par_niveau[niveau] = par_niveau.get(niveau, 0) + 1
    # Divisions, groupes, classes, sous-classes de la NAF rev. 2 (INSEE)
    assert par_niveau == {2: 88, 3: 272, 4: 615, 5: 732}


# --- normalisation / tokens ---

def test_normalize_accents_et_ponctuation():
    assert normalize("Pâtisserie-Chocolaterie !") == "patisserie chocolaterie"


def test_tokens_filtre_les_mots_outils():
    assert tokens("conseil en informatique") == ["conseil", "informatique"]
    assert tokens("Commerce de détail de pain") == ["commerce", "detail", "pain"]


# --- interpret : texte libre ---

def test_interpret_conseil_en_informatique():
    q = interpret("conseil en informatique")
    # Matche la division 62 (« Programmation, conseil et autres activités informatiques »)
    # -> toute la famille est ciblée, pas seulement 62.02A.
    assert set(q.naf_codes) == {"62.01Z", "62.02A", "62.02B", "62.03Z", "62.09Z"}
    assert q.naf_labels == ["Programmation, conseil et autres activités informatiques"]
    # Mots-clés BODACC : le distinctif + ses synonymes, jamais le générique seul.
    assert "informatique" in q.keywords and "logiciel" in q.keywords
    assert "conseil" not in q.keywords


def test_interpret_boulangerie_couvre_le_commerce_de_detail():
    q = interpret("boulangerie")
    assert "10.71C" in q.naf_codes
    assert "47.24Z" in q.naf_codes                  # via le synonyme « pâtisserie »
    assert "patisserie" in q.keywords


def test_interpret_restaurant_couvre_la_division():
    # « restauration » (synonyme) matche le libellé de la division 56 entière.
    q = interpret("restaurant")
    assert {"56.10A", "56.10C", "56.29A"} <= set(q.naf_codes)


def test_interpret_singulier_pluriel():
    q = interpret("agence immobilière")
    assert "68.31Z" in q.naf_codes                  # libellé « Agences immobilières »


def test_interpret_code_naf_exact():
    q = interpret("62.02A")
    assert q.naf_codes == ["62.02A"]
    assert q.keywords                               # mots-clés tirés du libellé
    assert "conseil" not in q.keywords              # les génériques ne partent pas seuls


def test_interpret_prefixe_naf():
    q = interpret("62")
    assert set(q.naf_codes) == {"62.01Z", "62.02A", "62.02B", "62.03Z", "62.09Z"}


def test_interpret_texte_inconnu_reste_litteral():
    q = interpret("xyzxyz")
    assert q.keywords == ["xyzxyz"]                 # comportement historique
    assert q.naf_codes == []                        # et aucun filtre NAF


def test_interpret_vide():
    q = interpret("  ")
    assert q.keywords == [] and q.naf_codes == []


# --- keep_cession : filtre NAF + repêchage par le nom ---

def _q_informatique() -> ActivityQuery:
    return interpret("conseil en informatique")


def test_keep_naf_cible():
    assert keep_cession("62.02A", "DUPONT CONSEIL", _q_informatique())


def test_keep_rejette_autre_naf():
    assert not keep_cession("56.10A", "LE BISTROT", _q_informatique())


def test_keep_repeche_par_le_nom():
    # Mal classée mais le nom porte le mot-clé : on garde.
    assert keep_cession("47.41Z", "ATOUT INFORMATIQUE", _q_informatique())
    assert keep_cession("47.24Z", "BOULANGERIE DUPONT", interpret("boulangerie"))


def test_keep_rejette_naf_inconnu_sans_indice():
    assert not keep_cession(None, "SARL MARTIN", _q_informatique())


def test_keep_prefixe_limite_aux_flexions():
    """« agencement » (synonyme de menuiserie) ne doit pas repêcher les « AGENCE … » :
    l'appariement par préfixe est réservé aux flexions (écart de longueur <= 3)."""
    q = interpret("menuiserie")
    assert "agencement" in q.keywords               # le synonyme est bien là
    assert not keep_cession("68.31Z", "AGENCE IMMOBILIERE DE COLOMIERS", q)
    assert keep_cession("43.32A", "MENUISERIE THENAULT", q)
    assert keep_cession("47.41Z", "ATOUT INFORMATIQUES", _q_informatique())  # flexion OK


def test_keep_sans_filtre_naf_laisse_tout_passer():
    q = interpret("xyzxyz")                         # aucun NAF cible
    assert keep_cession("56.10A", "LE BISTROT", q)
    assert keep_cession(None, None, q)
