# CLAUDE.md — Consignes pour Claude Code

> Lis ce fichier en entier avant de coder. Il décrit le but, l'architecture, les
> conventions et les règles à respecter pour ce projet.

## But du projet

Application web **interne** (plusieurs analystes d'un cabinet M&A) qui, pour un
échantillon de **sociétés cotées** saisi par l'utilisateur, récupère leurs **bêtas**
et leurs **multiples de valorisation**, les affiche dans un **tableau de comparables**
et un **tableau de bord**, et permet l'**export Excel**.

Contraintes structurantes (décidées avec l'utilisateur) :
- **Sources de données strictement gratuites** (pas d'abonnement payant).
- Interface **web partagée en interne** (Streamlit).
- Sorties : **tableau Excel** + **dashboard / visuels**.

## Stack

- **Langage** : Python ≥ 3.11.
- **Interface** : Streamlit (`app/streamlit_app.py`). Graphiques : Plotly.
- **Calcul** : pandas, numpy, statsmodels (régression du bêta).
- **Modèles / config** : pydantic, pydantic-settings.
- **Excel** : openpyxl.
- **HTTP + cache** : requests, requests-cache.
- **Gestion des dépendances** : `uv` + `pyproject.toml`.
- **Tests** : pytest. **Lint** : ruff.

## Architecture (vue d'ensemble)

```
comparables/
  config.py            # Settings (.env) + mapping indice par place de cotation
  models.py            # CompanyRecord (pydantic) = une ligne du tableau
  cache.py             # session HTTP cachée (SQLite) pour sources `requests`
  fx.py                # conversion de devises (API Frankfurter / BCE)
  finance/             # >>> COEUR FINANCIER, PUR ET TESTÉ <<<
    beta.py            # bêta par régression OLS + R²
    unlever.py         # Hamada : désendettement / réendettement
    multiples.py       # dette nette, VE, ratios, statistiques
  sources/             # adaptateurs de sources (un module par source)
    base.py            # interface commune DataSource
    yahoo.py           # IMPLÉMENTÉ (yfinance) : fondamentaux + cours
    edgar.py           # STUB : fondamentaux US (SEC EDGAR)
    stooq.py           # STUB : cours (secours)
    esef.py            # STUB : fondamentaux EU (ESEF / XBRL) — avancé
    registry.py        # routage ticker -> source
  pipeline.py          # orchestration fetch -> calcul -> CompanyRecord
  export/excel.py      # export Excel formaté (bytes)
app/
  streamlit_app.py     # interface Streamlit (héritée, retirée à terme)
  pages/               # pages multipage
backend/               # API FastAPI (lot 1 du cahier des charges)
  main.py              # create_app() ; uvicorn backend.main:app --port 8000 ; docs /api/docs
  security.py          # cookie de session signé (itsdangerous) + dépendance current_user
  jobs.py              # file de tâches en mémoire (1 worker uvicorn) avec progression
  routers/             # auth, comparables (jobs/stats/resolve/export), cessions, runs
frontend/              # Site web Next.js 15 + Tailwind 4 (lot 2) — npm run dev (port 3000)
  next.config.ts       # proxy /api -> FastAPI (même origine : cookies sans CORS)
  app/                 # login, (app)/comparables, (app)/cessions, (app)/historique
  lib/api.ts           # client API typé ; lib/format.ts : formats FR
tests/                 # tests du cœur financier + backend (TestClient, offline)
```

### Flux

`pipeline.build_comparables(tickers)` →
pour chaque ticker : `registry.fundamentals_source_for()` puis `price_source_for()` →
dérive dette nette / VE / multiples manquants (`finance.multiples`) →
calcule le bêta de régression + R² (`finance.beta`) →
gearing + bêta désendetté (`finance.unlever`) → `CompanyRecord`.

## Le pattern central : adaptateurs de sources

C'est le point d'architecture le plus important (objectif : pouvoir élargir la base).
Toute source implémente `comparables.sources.base.DataSource` :

```python
class DataSource(ABC):
    name: str
    provides_fundamentals: bool
    provides_prices: bool
    def supports(self, ticker) -> bool: ...
    def fetch_fundamentals(self, ticker) -> CompanyRecord | None: ...
    def fetch_prices(self, ticker, period, interval) -> pd.Series | None: ...
```

**Pour ajouter une source** : créer un module dans `sources/`, sous-classer `DataSource`,
remplir les capacités, implémenter les méthodes utiles, puis la déclarer dans `registry.py`.
Ne jamais mettre de logique de source ailleurs que derrière cette interface.

## Règles à respecter

1. **Ne casse pas le cœur financier.** Les modules `finance/*` sont purs (aucune I/O,
   aucun réseau) et **couverts par des tests**. Toute modification doit garder
   `pytest` au vert. N'ajoute pas de dépendance réseau dans `finance/`.
2. **Sources strictement gratuites.** Sources autorisées : Yahoo (yfinance), SEC EDGAR,
   Stooq, Frankfurter (FX). FMP / Alpha Vantage seulement via leur palier gratuit et
   uniquement si une clé est fournie dans `.env`. Ne code aucune source payante par défaut.
3. **Respecte les quotas et les conditions d'utilisation.** Toute source HTTP `requests`
   passe par `cache.get_session()`. EDGAR exige un en-tête `User-Agent` (sinon 403).
   Ne contourne aucune protection (CAPTCHA, authentification).
4. **Secrets.** Aucune clé en dur. Tout passe par `.env` (jamais versionné) via `config.Settings`.
5. **Gestion d'erreurs par société.** L'échec d'un ticker ne doit pas faire planter tout
   le lot : renvoyer un `CompanyRecord` partiel (champs à `None`), jamais une exception non gérée.
6. **Typage et style.** Type hints partout, modèles pydantic pour les données structurées,
   `ruff` propre, libellés FR pour l'affichage (voir `export/excel.py` `DISPLAY`).
7. **Tests obligatoires** pour toute nouvelle fonction de calcul financier, écrits en
   même temps que le code.

## Caveat connu (à garder en tête)

Le **strictement-gratuit plafonne la couverture des fondamentaux européens**. EDGAR ne
couvre que les sociétés américaines ; pour l'Europe, Yahoo est imparfait et la voie propre
(ESEF/XBRL) est lourde. L'architecture en adaptateurs permet d'ajouter plus tard une source
européenne payante **sans rien réécrire**.

## TODO (feuille de route priorisée — maj 2026-06-03)

- **Step 0 — [FAIT]** Durcissement du cœur financier : `inf`/`nan` filtrés (`multiples`/`beta`/`unlever`),
  crash sur indice à variance nulle corrigé, échecs beta loggués (plus de `except: pass`), filet
  par société dans `build_comparables` (règle 5), `tests/test_pipeline.py` ajouté.
- **Step 1 — [ABANDONNÉ] Normalisation des devises.** Inutile pour l'objectif (multiples + bêtas) :
  un multiple est un ratio même-devise (la devise se simplifie), un bêta est une régression de
  rendements (sans unité, en devise locale contre l'indice local). L'appli n'agrège jamais de
  montants absolus entre sociétés (cf. `STATS_FIELDS`, graphiques) ; les seuls montants en devise
  sont des colonnes d'affichage, devise indiquée par ligne. `fx.py` reste présent mais non branché.
- **Step 2 — [FAIT] Couche de cache.** Cache disque des cours yfinance (`cache.load_cached_prices`/
  `store_cached_prices`, pickle sous `data/prices/`, clé ticker+période+intervalle, TTL `price_cache_ttl_hours`),
  branché dans `yahoo.fetch_prices`. `cache.get_session()` prêt pour les futures sources `requests` (EDGAR).
- **Step 3 — [REPORTÉ] `sources/edgar.py`** (fondamentaux US via `data.sec.gov`). En suspens : EDGAR ne fournit
  pas la capitalisation → trancher d'abord l'articulation avec Yahoo (fusion comptes / market_cap actions×cours /
  comblement des trous) avant d'implémenter. Routage US + fallback Yahoo + User-Agent SEC conforme.
- **Step 4 — [ABANDONNÉ] `sources/stooq.py`** : l'historique CSV gratuit de Stooq est passé derrière une
  clé API (constaté 2026-06-03 : `/q/d/l/` → « Get your apikey », idem `stooq.pl` et plages de dates). Seule
  la cotation instantanée reste gratuite (un seul point, insuffisant pour une régression de bêta). Plus de
  source de cours de secours strictement gratuite → yfinance reste l'unique source de cours.
- **Step 5 — [FAIT] Authentification interne.** Porte `streamlit-authenticator` (`comparables/streamlit_auth.py`)
  sur la page principale ET chaque page ; identifiants hachés bcrypt dans `auth_config.yaml` (gitignore, modèle
  `auth_config.example.yaml`), clé de cookie via `.env` (`AUTH_COOKIE_KEY`), `AUTH_ENABLED=false` pour le dev.
  Helpers purs testés (`comparables/auth.py` + CLI `python -m comparables.auth hash|genkey`). Docker durci :
  8501 lié à `127.0.0.1`, limites ressources, `.dockerignore`, modèle Caddy/oauth2-proxy commenté.
- **Step 6 — `sources/esef.py`** (avancé) : fondamentaux EU via filings.xbrl.org + arelle.
- **Step 7 — [FAIT] Persistance / historisation (SQLite).** `comparables/store.py`
  (`save_run`/`list_runs`/`load_run`/`delete_run`, base `history_db_path`). Bouton « 💾 Enregistrer »
  sur la page principale (utilisateur connecté + params) ; onglet `app/pages/1_Historique.py`
  (remplace le placeholder Dashboard) pour consulter / ré-exporter / supprimer. Tests `test_store.py`.
- **[FAIT] Onglet « Cessions de fonds de commerce — France » (hors roadmap initiale).**
  `comparables/fr/` : prix de cession → **% du CA et multiple × EBE**, toutes entreprises FR,
  fenêtre 10 ans. Sources publiques **gratuites sans clé** : BODACC (`bodacc.py`, prix texte libre
  + SIREN cédant), **Ratios INPI/BCE** (`finances_inpi.py`, dataset `ratios_inpi_bce` : CA/EBE/EBIT
  multi-exercices, exercice calé sur la date de cession), Recherche d'entreprises (`entreprises.py`,
  NAF/nom). `parsing.py` (prix format FR, % CA + × EBE, bandes plausibilité 5–400 % / 0,5–15x),
  `pipeline.py`, onglet `app/pages/2_Cessions_FR.py`. **Limite structurelle** : CA/EBE absents des
  comptes confidentiels (~45 % des dépôts, art. L232-25) → couverture partielle affichée. Tests `test_fr_*`.

- **[FAIT 2026-06-10] Lot 0 — fiabilisation du moteur** (cf. `CAHIER_DES_CHARGES.md` et
  `AMELIORATIONS.md` § Avancement) : bug Excel `_stats`, retry + cache fondamentaux Yahoo,
  parallélisation du lot + mutualisation des indices, dédoublonnage BODACC + SIREN cédant
  déterministe, CI GitHub Actions, `.gitattributes`.
- **[FAIT 2026-06-10] Lots 1 & 2 — backend FastAPI (`backend/`) + site Next.js (`frontend/`).**
- **[FAIT 2026-06-11] Lot 3 — extraction comptes INPI (`comparables/fr/comptes/`).**
  Credentials INPI posés (`.env`), API RNE validée en réel. Découverte clé : `bilansSaisis`
  = liasse déjà numérisée (codes CERFA → montants) → extraction **structurée, gratuite et
  déterministe** (`bilan_saisi.py`, colonne m1 en 2033-B / m3 en 2052, CA codé `FJ` en 2052
  structuré), branchée structuré-d'abord dans `fr/pipeline.build_cessions` ; cascade
  PDF→OCR→LLM en simple filet (clé Claude **optionnelle**). Validé au centime vs dataset
  ratios sur 6 PME réelles (les deux régimes). Garde-fou anti-rafale RNE (cadence mini +
  retry, `INPI_MIN_INTERVAL_SECONDS`). Reste (optionnel) : cache des extractions + Batch API.
- **[FAIT 2026-06-11] Fiabilisation bêtas & multiples.** Tie-out : VE et multiples recalculés
  depuis les composants affichés (valeurs pré-calculées Yahoo en simple repli, filtrées > 0) ;
  repli `fast_info`/états financiers pour combler les `info` lacunaires (small/mid caps) ;
  seuil de points par fréquence (`MIN_BETA_OBS_WEEKLY=52`) ; mapping d'indices élargi à
  Copenhague/Helsinki/Oslo/Lisbonne/Dublin/Toronto/Sydney/Tokyo/Hong Kong/Singapour
  (symboles validés contre l'API) ; suffixe inconnu signalé `(defaut)` dans `index_used`.
- **[FAIT 2026-06-11] Recherche intelligente d'activité (cessions FR).** Le texte libre
  (« conseil en informatique ») est interprété par `fr/activites.py` : mots-clés élargis
  (synonymes) combinés en OU sur le BODACC + codes NAF cibles via la nomenclature INSEE
  embarquée (niveaux 2-5, `fr/data/naf_rev2.csv` — un libellé de division matché cible toute
  la famille). Double passe BODACC (nom du commerçant d'abord — haute précision — puis texte
  de l'acte), filtre NAF AVANT les finances (identité par SIREN ; repêchage par le nom officiel
  de la cédante uniquement : le champ `commercant` mêle cédant et cessionnaire). Garde-fou de
  débit Recherche d'entreprises (7 req/s + retry 429). `build_cessions` renvoie un
  `CessionsBatch` (cessions + compteurs d'entonnoir : annonces balayées / hors NAF / sans CA),
  exposé par l'API (`search`) et affiché (site + Streamlit) pour rendre tout « 0 résultat »
  explicable. Validé en réel : « conseil en informatique » passe de 0 à 10 cessions pertinentes.
- **[FAIT 2026-06-11] Efficacité du site (suite recherche intelligente).**
  (a) **Progression cessions** : `build_cessions(progress=…)` câblé au job (annonces
  traitées / balayées affichées pendant la recherche). (b) **Export .xlsx cessions**
  (`fr/export.py`, POST `/api/cessions/export`) au format de l'export comparables, médianes
  robustes en pied. (c) **Sélection « Retenu »** sur la page web cessions (présélection
  règle d'or renvoyée par l'API via `retenu_defaut`, recalcul des agrégats par POST
  `/api/cessions/stats`, parité Streamlit). (d) **Historique mixte** : `store.py` porte un
  `kind` ('comparables'|'cessions', migration ALTER douce), sauvegarde/consultation/ré-export
  des recherches cessions, base sectorielle filtrée sur kind. (e) **Jobs persistés** :
  table `jobs` dans history.sqlite (résultats sérialisés par kind, rechargés après
  redémarrage), 3 workers. (f) **Référentiels locaux** (`fr/referentiels.py` +
  `referentiels_db_path`) : Sirene (SIREN→nom/NAF) et ratios INPI/BCE (CA/EBE/EBIT)
  répliqués en SQLite — lookups instantanés, zéro quota/429, repli API automatique si
  non chargés. CLI : `python -m comparables.fr.referentiels refresh` (~2-3 Go, mensuel).
  Tests : `test_fr_referentiels.py`, `test_fr_export.py`, `test_backend_jobs.py`,
  `tests/conftest.py` (bases SQLite isolées par test).
- **[FAIT 2026-06-11] Lot 4 — socle de déploiement VPS** : `deploy/` (Dockerfile.api,
  Dockerfile.front standalone, docker-compose api+front+caddy, Caddyfile, README pas-à-pas).
  Non testé en réel (pas de Docker sur le poste) : à valider au premier déploiement.

## Commandes

```bash
# Installation
uv venv && uv pip install -e ".[dev]"

# Lancer l'appli Streamlit héritée (depuis la racine)
streamlit run app/streamlit_app.py

# Lancer le site web (backend + frontend, 2 terminaux)
uvicorn backend.main:app --port 8000        # API (AUTH_ENABLED=false pour le dev)
cd frontend && npm install && npm run dev   # http://localhost:3000

# Tests + lint
pytest
ruff check .

# Référentiels locaux cessions FR (Sirene + ratios BCE, ~2 Go ; mensuel)
python -m comparables.fr.referentiels refresh    # ou `status`

# Déploiement interne
docker compose up --build   # Streamlit héritée (voir docker-compose.yml)
docker compose -f deploy/docker-compose.yml up -d --build   # site + API + Caddy (lot 4, cf. deploy/README.md)
```
