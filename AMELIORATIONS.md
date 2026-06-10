# Améliorations & backlog — audit du 2026-06-07

> Document de travail issu d'un audit du code (analyse multi-agents, 6 dimensions, ~110 lectures
> de fichiers). Il **complète** la feuille de route de [`CLAUDE.md`](CLAUDE.md) (section TODO), il ne
> la remplace pas. Chaque item porte une **priorité** (🔴 haute / 🟠 moyenne / 🟢 basse) et un
> **effort** (faible / moyen / élevé). Les chemins de fichiers sont relatifs à la racine du projet.

## État de base (sain)

75 tests passent, `ruff` propre, cœur financier `finance/*` robuste et testé, secrets correctement
gérés (gitignore + `.env`/`auth_config.yaml` non suivis), Docker durci. Ce backlog est de
l'**amélioration**, pas du sauvetage — à **une exception** : le bug de correctness sur l'export Excel
(voir §1).

## Avancement (maj 2026-06-10)

**Lot 0 du cahier des charges réalisé** (cf. [`CAHIER_DES_CHARGES.md`](CAHIER_DES_CHARGES.md)) :
🐛 bug Excel `_stats` corrigé (délègue à `summary_stats`, + `tests/test_excel.py`) ;
retry/backoff Yahoo (`_with_retry`, réglages `yahoo_max_attempts`/`yahoo_backoff_seconds`) ;
cache disque des fondamentaux (`cache.load/store_cached_fundamentals`, TTL 72 h, échecs non mis
en cache) ; parallélisation du lot (`pipeline_max_workers`, ordre préservé, règle 5 conservée) ;
indices pré-téléchargés une seule fois (`_prefetch_indices`) ; dédoublonnage BODACC + filtre
rectificatifs/annulations + `_cedant_siren` déterministe (+ `tests/test_fr_bodacc.py`) ;
CI GitHub Actions (3.11/3.12) + `.gitattributes`. Suite : 93 tests.

## Ordre d'attaque suggéré

- **Lot 1 — quick wins, fort levier, faible risque** : 🐛 bug Excel `_stats` (§1) → `.gitattributes`
  (§6) → CI GitHub Actions (§6) → bêta ajusté Blume + `std/quartiles/count` dans `summary_stats` (§1).
- **Lot 2 — robustesse & perf** : parallélisation du lot (§3) → retry/backoff Yahoo + cache des
  fondamentaux (§2) → mutualisation du fetch d'indice (§3).
- **Lot 3 — UX analyste** : afficher source + n_obs, récap des sociétés en échec, formatage des
  montants, sélection/exclusion de comparables (§4).
- **Lot 4 — fiabilité Cessions FR** : dédoublonnage BODACC, correction `_cedant_siren`, cohérence
  du barème par activité (§5).
- **Lot 5 — extension de couverture (roadmap)** : routage par capacité + `merge_records` → EDGAR
  (Step 3) → ESEF (Step 6).

## Roadmap officielle restante (`CLAUDE.md`)

| Step | État | Verrou réel |
|---|---|---|
| **Step 3 — EDGAR** (fondamentaux US) | reporté | EDGAR ne fournit pas la capitalisation → besoin d'un helper pur `merge_records(primary, secondary)` (voir §2) pour combler les `None` via Yahoo. |
| **Step 6 — ESEF** (fondamentaux UE, XBRL/arelle) | à faire | Principal trou de couverture (fondamentaux européens). Avancé. Prérequis : routage par capacité + `merge_records` + `esef.supports()` affiné. |

---

## 1. Cœur financier (`finance/*`)

**Points forts** : robustesse numérique sérieuse (filtrage inf/nan dans `compute_beta`, `safe_ratio`,
`summary_stats`, `unlever`/`relever`), cas « indice à variance nulle » géré et testé, formules Hamada
et OLS vérifiées par tests de valeur, option `floor_net_debt_at_zero` (trésorerie nette) testée,
rejet des dénominateurs négatifs.

- 🔴 **[faible] 🐛 Bug — l'export Excel recalcule les stats sans filtrer inf/nan.**
  `export/excel.py` `_stats()` (l.43-50) recalcule médiane/moyenne/min/max en ne filtrant que
  `is not None`, **pas** les `inf`/`nan` (contrairement à `finance.multiples.summary_stats` qui
  applique `math.isfinite`). Un `nan`/`inf` qui atteindrait un champ polluerait les stats de **tout
  l'échantillon dans le fichier livré au client**. → faire pointer `_stats` vers `summary_stats`
  (DRY + correction). *C'est le seul vrai défaut de correctness identifié.*
  **Fichiers** : `comparables/export/excel.py`, `comparables/finance/multiples.py`.

- 🔴 **[faible] Bêta ajusté Blume absent.** `compute_beta` ne renvoie que le bêta brut, sans option
  d'ajustement Blume (`2/3·β_raw + 1/3·1.0`), qui est la convention de marché (Bloomberg « adjusted
  beta ») pour un bêta prospectif et un WACC. → ajouter `adjust_beta_blume(raw)` (coefficient
  paramétrable) + exposer `beta_adjusted` dans `BetaResult`, avec test de valeur.
  **Fichiers** : `comparables/finance/beta.py`, `tests/test_beta.py`.

- 🔴 **[faible] `summary_stats` ne donne ni écart-type, ni quartiles, ni `n`.** Il ne renvoie que
  median/mean/min/max. Manquent : `std` (dispersion), `q1`/`q3` (robustes aux outliers, préférés à
  min/max), et `count` (combien de sociétés ont réellement contribué). Sans `n`, une médiane sur 2
  sociétés paraît aussi fiable qu'une sur 10. → ajouter `std`, `q1`, `q3`, `count` + tests.
  **Fichiers** : `comparables/finance/multiples.py`, `tests/test_multiples.py`.

- 🟠 **[moyen] Aucun traitement des outliers sur les multiples.** Pas de winsorisation ni
  d'exclusion (ex. EV/EBITDA = 80x, P/E = 300x). La moyenne y est très sensible. → fonction pure
  `winsorize(values, lower, upper)` ou `filter_outliers(values, k_iqr)` (règle de Tukey), optionnelle
  dans `summary_stats`, testée.
  **Fichiers** : `comparables/finance/multiples.py`, `tests/test_multiples.py`.

- 🟠 **[moyen] `beta_source` (bêta publié Yahoo) jamais réconcilié ni désendetté.** Le pipeline ne
  désendette que `beta_regression` et n'utilise `beta_source` que pour l'affichage. Manque : (1) une
  fonction de comparaison régression vs publié (signal de fiabilité quand R² faible / n_obs proche du
  minimum) ; (2) le choix de désendetter aussi `beta_source` (déjà un bêta endetté). → petite fonction
  pure testée + exposer le choix de la base.
  **Fichiers** : `comparables/finance/beta.py`, `comparables/pipeline.py`, `comparables/models.py`.

- 🟠 **[faible] Pas d'intervalle de confiance / signal sur R² faible.** `compute_beta` capture
  `model.rsquared` mais jette l'erreur-standard de la pente (`model.bse[1]`, `conf_int()`). Un bêta
  de 1.4 avec IC [0.6 ; 2.2] n'a pas la même valeur qu'un bêta serré. → exposer `std_err_beta` ou un
  flag `low_confidence` (r² < seuil ou n_obs < seuil), + test.
  **Fichiers** : `comparables/finance/beta.py`, `tests/test_beta.py`.

- 🟠 **[faible] Lacunes de tests sur cas-limites réalistes.** (1) aucun test avec dates désalignées
  titre/indice (le `join='inner'` est la logique la plus critique en pratique) ; (2) pas de test que
  `min_obs` s'applique sur le `n` **après** alignement/filtrage ; (3) `unlever` : pas de cas
  `denom`≈0 non nul ; (4) `tax_rate` hors bornes (> 1 → `(1-IS)` négatif inverse le signe) accepté
  silencieusement → ajouter une garde `0 ≤ tax_rate < 1` et les tests.
  **Fichiers** : `tests/test_beta.py`, `tests/test_unlever.py`, `comparables/finance/unlever.py`.

- 🟢 **[faible] `returns_from_prices` : rendements simples uniquement + trous masqués.** Pas de
  log-rendements (alternative standard, atténue les chocs) ; `dropna()` masque silencieusement les
  trous de calendrier (rendements multi-périodes traités comme mono-période → biais). → paramètre
  `method='simple'|'log'` + tracer/documenter les trous, testé.
  **Fichiers** : `comparables/finance/beta.py`, `tests/test_beta.py`.

## 2. Sources de données & couverture (`sources/*`)

**Points forts** : interface `DataSource` minimale et correcte (contrat « renvoie None plutôt que
lever »), `yahoo.fetch_fundamentals` robuste sur les données manquantes, recherche de symbole soignée
(normalisation accents/apostrophes, priorité de place de cotation), `fetch_prices` branché sur le
cache disque et testé, stubs EDGAR/ESEF avec plan d'implémentation précis, abandon de Stooq documenté.

- 🔴 **[moyen] Yahoo = point de défaillance unique sans retry ni gestion du rate-limit.** Stooq
  abandonné et EDGAR/ESEF non branchés → yfinance est l'unique source. `tk.info` et `yf.download`
  sont des appels uniques : un 429/timeout transitoire = record entièrement partiel (donnée perdue).
  De plus `fetch_prices` est appelé 2×/ticker (titre + indice). → retry borné avec backoff (2-3
  essais), distinguer échec définitif (None) vs transitoire (réessai).
  **Fichiers** : `comparables/sources/yahoo.py`, `comparables/pipeline.py`.

- 🟠 **[moyen] `tk.info` (fondamentaux) n'est pas mis en cache disque** alors que les cours le sont,
  et que c'est l'appel le plus lourd et le plus throttlé par Yahoo. → étendre le cache disque (ou un
  cache TTL) aux fondamentaux, TTL plus long (changent moins vite que les cours).
  **Fichiers** : `comparables/sources/yahoo.py`, `comparables/cache.py`.

- 🟠 **[moyen] Le routage ignore `supports()` et les flags de capacité.** `registry.py` retourne le
  singleton Yahoo **en dur** ; `supports()` n'est appelé **nulle part**, `provides_*` jamais lus. Le
  pattern d'adaptateurs n'est câblé qu'à moitié. → registre = liste ordonnée de sources ;
  `fundamentals_source_for`/`price_source_for` itèrent et sélectionnent par capacité + `supports()`.
  Ajouter une source devient « ajouter une ligne ».
  **Fichiers** : `comparables/sources/registry.py`, `comparables/sources/base.py`.

- 🟠 **[moyen] Pas de fusion entre sources → EDGAR reste bloqué.** `pipeline.build_record` n'utilise
  qu'une seule source de fondamentaux. C'est le verrou EDGAR (pas de market_cap). → helper pur
  `merge_records(primary, secondary)` (comble les `None` de primary par secondary), appelé quand la
  source primaire ne couvre pas market_cap. Débloque EDGAR **et** ESEF.
  **Fichiers** : `comparables/pipeline.py`, `comparables/models.py`.

- 🟢 **[faible] User-Agent EDGAR en dur, pas relié à `.env`.** `edgar.py` l.26 :
  `SEC_USER_AGENT = "comparables-tool contact@example.com"` (placeholder ; SEC renvoie 403 sans
  contact réel). → champ `sec_user_agent`/`sec_contact_email` dans `config.Settings` (lu depuis
  `.env`), point d'accroche réseau = `cache.get_session()`.
  **Fichiers** : `comparables/sources/edgar.py`, `comparables/config.py`.

- 🟢 **[faible] `esef.supports()` trop grossier (`"." in ticker`).** Un point ≠ Europe (Toronto `.TO`,
  Tokyo `.T`, Hong Kong `.HK`, Australie `.AX`). → s'appuyer sur un ensemble explicite de suffixes
  UE dérivé de `config.INDEX_BY_SUFFIX`. À corriger **avant** d'implémenter `fetch_fundamentals`,
  sinon le routage par capacité se trompe de source.
  **Fichiers** : `comparables/sources/esef.py`, `comparables/config.py`.

- 🟢 **[faible] `DataSource(ABC)` sans `@abstractmethod`.** Une sous-classe incomplète s'instancie
  sans erreur (échec seulement à l'appel). → durcir le contrat (ou test générique paramétré sur les
  sources enregistrées vérifiant la cohérence `provides_*` ↔ méthodes surchargées).
  **Fichiers** : `comparables/sources/base.py`.

## 3. Orchestration & robustesse (`pipeline.py`, `models.py`, `config.py`, `cache.py`)

**Points forts** : règle 5 (isolation par société) implémentée et testée à deux niveaux, fallback
propre sur `None`, dérivés défensifs (`if rec.X is None`), cache disque résistant à la corruption,
logging ciblé (plus de `except: pass`).

- 🔴 **[moyen] Le lot est 100 % séquentiel.** `build_comparables` boucle sur les tickers ; chaque
  `build_record` fait 3 appels réseau bloquants. Pour 6-10 sociétés = 18-30 téléchargements I/O-bound
  enchaînés → l'utilisateur attend le spinner plusieurs dizaines de secondes. → `ThreadPoolExecutor`
  (max_workers borné pour respecter les quotas), `executor.map` préserve l'ordre, garder le try/except
  par ticker **dans** la tâche (règle 5). Permet aussi un timeout par `future`.
  **Fichiers** : `comparables/pipeline.py`.

- 🟠 **[moyen] L'indice de référence est re-téléchargé 1×/ticker.** Plusieurs sociétés d'une même
  place partagent le même indice (`^FCHI`, `^AEX`…). Au 1er run (cache vide) ou si TTL=0 → N
  téléchargements redondants. → pré-calculer les indices distincts et les fetcher une fois en amont,
  passer la série déjà chargée à `build_record`.
  **Fichiers** : `comparables/pipeline.py`, `comparables/config.py`.

- 🟠 **[faible] Aucune validation pydantic sur `CompanyRecord`.** `ticker` n'est ni `strip()` ni
  `upper()` (un `" wms "` casse le découpage de suffixe `rsplit('.')`) ; le nettoyage existe côté UI
  mais pas dans le modèle, donc tout appel programmatique de `build_comparables` n'est pas protégé.
  → `@field_validator('ticker')` (strip+upper) + éventuelles bornes de cohérence.
  **Fichiers** : `comparables/models.py`, `comparables/pipeline.py`.

- 🟠 **[moyen] Pas de timeout sur les appels yfinance bloquants.** Un ticker lent bloque tout le run
  séquentiel. → la parallélisation (ci-dessus) permet `future.result(timeout=...)` et une dégradation
  gracieuse en record partiel (renforce la règle 5 face aux pannes réseau, pas seulement aux
  exceptions).
  **Fichiers** : `comparables/pipeline.py`, `comparables/sources/yahoo.py`.

- 🟢 **[faible] `get_session()` recrée une `CachedSession` à chaque appel.** Appelée 1×/nom en mode
  recherche → gaspillage (pas de pooling keep-alive). → mémoïser (singleton module / `lru_cache`).
  Note liée : la résolution de tickers avale toute exception en `m=None` **sans logging**.
  **Fichiers** : `comparables/cache.py`, `comparables/sources/yahoo.py`.

- 🟢 **[faible] Condition `gearing`/`beta_unlevered` implicite + pas de diagnostic.** `if rec.market_cap
  and rec.net_debt is not None` : market_cap=0.0 saute le calcul (correct mais implicite → rendre
  `> 0` explicite) ; quand le bêta désendetté manque, aucun champ n'indique pourquoi (donnée absente
  vs erreur). → petit champ de diagnostic (notes/flags) sur `CompanyRecord`.
  **Fichiers** : `comparables/pipeline.py`, `comparables/models.py`.

## 4. Interface Streamlit & UX (`app/`)

**Points forts** : gestion d'état correcte (résultats en session, pop du `saved_run_id`), mode
« Nom de société » avec résolution transparente, graphe « Bêta vs R² » pertinent, onglet Cessions FR
remarquable (data_editor + recalcul live + présélection « règle d'or » + signalement des limites),
feedbacks de progression clairs.

- 🔴 **[faible] Source et n_obs calculés mais jamais affichés.** `CompanyRecord` porte `source` et
  `n_obs` (nombre de points de la régression) mais aucun n'apparaît à l'écran ni dans `DISPLAY`
  (Excel). L'analyste voit R² mais pas si le bêta repose sur 24 ou 60 points, ni quelle source a
  produit la ligne (le sourcing est une exigence). → colonnes « Source » et « N pts » (écran + Excel).
  **Fichiers** : `app/streamlit_app.py`, `comparables/export/excel.py`, `comparables/models.py`.

- 🔴 **[moyen] Pas de signalement des sociétés en échec / partielles.** Un ticker en échec devient
  une ligne tout-`None` sans avertissement ; aucun récap « 5/6 sociétés récupérées, 1 sans données :
  WIE.VI ». → `st.warning` listant les tickers concernés + colonne « Couverture » (✓/⚠/✗) ou
  `st.metric`. Savoir qu'un comparable est incomplet **avant** de l'inclure dans une médiane est
  critique.
  **Fichiers** : `app/streamlit_app.py`.

- 🔴 **[moyen] Montants du tableau écran non formatés.** `market_cap` sort en `89000000000`, gearing
  en `0.1834` (au lieu de 18 %), `ev_ebitda` sans suffixe `x`. L'Excel, lui, met en millions et
  formate par type → l'écran est moins lisible que l'export. → `st.column_config.NumberColumn`
  (monétaire en M, %, suffixe x, 2 décimales).
  **Fichiers** : `app/streamlit_app.py`, `app/pages/1_Historique.py`.

- 🟠 **[moyen] Pas de sélection/exclusion de comparables sur la page principale.** L'onglet FR le
  fait (colonne « Retenu » + recalcul direct), mais pour les comparables boursiers il faut réécrire
  la liste de tickers et tout recalculer (re-fetch réseau) pour écarter un outlier — geste M&A
  quotidien. → reproduire le pattern `data_editor` + « Retenu » + recalcul des médianes + Excel sur
  la sélection.
  **Fichiers** : `app/streamlit_app.py`.

- 🟠 **[moyen] Stats écran plus pauvres que l'Excel + R² faible non signalé.** L'écran ne montre que
  les médianes ; l'Excel calcule médiane/moyenne/min/max. Aucun seuil de qualité visuel. → afficher
  les 4 stats + style conditionnel (griser/colorer R² < seuil, multiples hors bande).
  **Fichiers** : `app/streamlit_app.py`, `comparables/export/excel.py`.

- 🟢 **[faible] L'Excel est régénéré à chaque rerun.** `build_excel_bytes(records)` est en argument
  du `download_button` dans le corps du script → recréé à chaque interaction. → mémoriser les bytes
  en session (recalcul quand `records` change) ou `@st.cache_data`.
  **Fichiers** : `app/streamlit_app.py`.

- 🟠 **[élevé] Historique : sélection + comparaison de runs.** La sélection passe par un `selectbox`
  qui duplique le tableau ; aucune comparaison entre runs (évolution d'une médiane entre deux dates
  pour le même échantillon — tout l'intérêt d'historiser). Les params enregistrés (IS, période,
  fréquence) ne sont pas affichés alors qu'ils conditionnent la comparabilité. → sélection dans le
  tableau (`on_select`), comparaison de 2 runs (deltas des médianes), afficher les params.
  **Fichiers** : `app/pages/1_Historique.py`.

- 🟢 **[moyen] Cessions FR : export Excel + liens de vérification.** L'onglet n'exporte qu'en CSV
  (incohérent avec le reste) et n'offre aucun lien vers l'annonce BODACC / la fiche société
  (`annuaire-entreprises.data.gouv.fr/entreprise/<siren>`) pour vérifier un prix « best-effort ».
  → `st.column_config.LinkColumn` + export Excel cohérent.
  **Fichiers** : `app/pages/2_Cessions_FR.py`.

## 5. Module Cessions de fonds de commerce — France (`fr/*`)

**Points forts** : `parsing.py` 100 % pur et largement testé, filet par société (règle 5) testé,
filtrage statistique robuste (garde-fous métier + z-score MAD en log, Iglewicz & Hoaglin), choix
d'exercice INPI bien pensé (`pick_for_date`), distinction prix vs capital social, honnêteté sur les
limites (comptes confidentiels ~45 %).

- 🔴 **[moyen] Pas de dédoublonnage des annonces BODACC.** `fetch_cessions` accumule tout sans
  dédoublonner. BODACC publie rectificatifs/additifs/republications du même acte → doublons qui
  gonflent `n` et tirent les médianes. → déduplication sur clé stable (`url_complete`, ou
  `(siren, prix, date arrondie)`) + filtrer `typeavis != rectificatif`.
  **Fichiers** : `comparables/fr/bodacc.py`, `comparables/fr/parsing.py`.

- 🔴 **[moyen] `_cedant_siren` peut retenir l'acheteur (cessionnaire).** Le fallback final est
  `next(iter(registre), None)` où `registre` est un `set` → itération non déterministe : on peut
  rattacher le CA/EBE de la **mauvaise société** sans aucun signal. → conserver la **liste ordonnée**
  d'`extract_sirens` (le cédant est cité en premier dans le descriptif), ou marquer le SIREN comme
  incertain.
  **Fichiers** : `comparables/fr/bodacc.py`.

- 🔴 **[faible] Barème par activité incohérent avec l'UI.** `summarize_by_activity` (l.166-169) ne
  construit les groupes NAF qu'à partir de `with_pct` filtré sur `is_plausible_pct`. Une cession au
  `mult_ebe` plausible mais au `pct_ca` absent/hors-bande est absente du `by_activite` alors qu'elle
  est cochée par défaut dans l'UI (`pct_mask OR ebe_mask`) → la médiane ×EBE du pipeline diffère de
  ce que l'analyste voit. → grouper sur `is_plausible_pct(pct_ca) OR is_plausible_mult_ebe(mult_ebe)`.
  **Fichiers** : `comparables/fr/parsing.py`.

- 🟠 **[moyen] Pas d'indicateur de fiabilité par ligne.** Infos calculées puis perdues : force du
  mot-clé de prix (« prix de cession » vs « moyennant » isolé), `pick_for_date` a-t-il trouvé un
  exercice **avant** la cession (nominal) ou fait le fallback « plus récent » (CA possiblement
  postérieur), écart en mois cession/clôture. → exposer `exercice_avant_cession` + qualité du prix,
  colonne fiabilité, + tests (règle 7).
  **Fichiers** : `comparables/fr/models.py`, `comparables/fr/finances_inpi.py`,
  `comparables/fr/pipeline.py`, `app/pages/2_Cessions_FR.py`.

- 🟠 **[faible] `parse_fr_amount` mal interprète un décimal sans virgule.** Sans virgule, tous les
  points sont supprimés comme séparateurs de milliers : `4.5 → 45`, `99.9 → 999`. → ne traiter le
  point comme séparateur de milliers que si les groupes suivants font exactement 3 chiffres, sinon
  décimale. + tests.
  **Fichiers** : `comparables/fr/parsing.py`, `tests/test_fr_parsing.py`.

- 🟠 **[moyen] Agrégats au seul niveau NAF complet (n faibles).** Groupes par code complet (`10.71C`)
  → beaucoup de groupes à n=1-2 sans valeur statistique. → agrégation à un niveau plus large
  (division NAF 2 chiffres, configurable) + masquer/avertir les médianes sur n < seuil (ex. 5).
  **Fichiers** : `comparables/fr/parsing.py`, `app/pages/2_Cessions_FR.py`.

- 🟢 **[moyen] Notations « million » / « K€ » / « M€ » non reconnues.** `« 1,2 million euros »`,
  `« 250 K€ »` → `None` : les **gros tickets** disparaissent davantage → biais vers le bas. → étendre
  `_PRICE_RE` / `parse_fr_amount` aux suffixes K/M/million(s)/milliard. + tests.
  **Fichiers** : `comparables/fr/parsing.py`, `tests/test_fr_parsing.py`.

- 🟢 **[moyen] `extract_price` retourne le 1er match, pas le plus fiable.** Sur une annonce
  multi-montants (répartition du prix, cautionnement), le 1er montant peut être une composante. →
  collecter tous les matches et retenir celui du mot-clé le plus fort (ou le max plausible), + test.
  **Fichiers** : `comparables/fr/parsing.py`, `tests/test_fr_parsing.py`.

## 6. Tests, qualité & exploitation

**Points forts** : cœur et logique pure bien couverts (75 tests), tests déterministes sans réseau
(HTTP mocké), secrets gérés, exposition réseau Docker maîtrisée (127.0.0.1, limites ressources,
secrets en volume read-only), règle 5 testée des deux côtés, `uv.lock` versionné, index git en LF.

- 🔴 **[faible] CI GitHub Actions absente.** Aucun `.github/`. → `ci.yml` sur `push`/`pull_request` :
  installer uv, `uv sync` (ou `uv pip install -e .[dev]`), puis `ruff check .` et `pytest`. Suite
  rapide (~30 s) et 100 % offline. Tester Python 3.11 et 3.12. **Garde-fou n°1** contre une
  régression du cœur financier (règle 1).
  **Fichiers** : `.github/workflows/ci.yml`, `pyproject.toml`.

- 🔴 **[faible] Le Dockerfile ignore `uv.lock`.** `uv pip install --system -r pyproject.toml` (l.5)
  résout les plages de versions à la date du build → builds non reproductibles malgré le lock
  versionné. → installer depuis le lock (`uv sync --frozen --no-dev`, ou
  `uv export --frozen --no-dev | uv pip install --system -r -`). Bonus : meilleur cache de couches
  (copier `pyproject.toml` + `uv.lock` avant le code).
  **Fichiers** : `Dockerfile`, `uv.lock`.

- 🟠 **[faible] `.gitattributes` manquant.** `core.autocrlf=true` sur cette machine Windows ; l'index
  est propre (LF) mais rien ne le garantit pour un autre clone. → `.gitattributes` avec
  `* text=auto eol=lf`, `*.py text eol=lf`, `*.lock -text`, `*.xlsx binary`.
  **Fichiers** : `.gitattributes`.

- 🟠 **[faible] Sélection de règles `ruff` minimale.** `[tool.ruff]` ne fixe que `line-length` et
  `target-version` (donc seulement E + F par défaut). → activer `I` (tri imports), `UP` (pyupgrade,
  cohérent avec `from __future__ import annotations`), `B` (bugbear : attrape les `except Exception`
  trop larges), `W`. Puis `ruff check --fix` une fois.
  **Fichiers** : `pyproject.toml`.

- 🟠 **[moyen] `export/excel.py` entièrement non testé.** Sortie livrée au client, et `_stats` est
  une fonction de calcul (règle 7). → test offline : 2-3 `CompanyRecord` → `build_excel_bytes` →
  ré-ouvrir avec `openpyxl.load_workbook`, asserter une cellule de stat, le `n.d.` des None, la
  division /1e6.
  **Fichiers** : `comparables/export/excel.py`, `tests/test_excel.py`.

- 🟠 **[faible] Helpers purs non testés : `config.index_for()` et `fr/bodacc` (`_acte_dict`,
  `_cedant_siren`).** `index_for()` mappe le suffixe de place → indice (un mauvais routage fausse
  tous les bêtas) ; `_acte_dict`/`_cedant_siren` gèrent les cas tordus du texte libre BODACC. →
  couvrir (tests purs, sans réseau).
  **Fichiers** : `comparables/config.py`, `comparables/fr/bodacc.py`, `tests/test_config.py`.

- 🟠 **[moyen] Durcir le Dockerfile.** (1) `HEALTHCHECK` utilise `curl`, **absent** de
  `python:3.12-slim` → toujours `unhealthy` ; remplacer par un check Python (`urllib.request` sur
  `/_stcore/health`). (2) conteneur en root → ajouter un utilisateur non privilégié (`USER`). (3)
  double installation (`uv pip install -r pyproject.toml` puis `pip install -e .`) → une seule fois.
  **Fichiers** : `Dockerfile`.

- 🟢 **[faible] Marquer les tests lents + pytest strict.** ~30 s dominés par `test_app_gate.py`
  (AppTest, timeout 60). → marqueur `@pytest.mark.slow` (exclusion en dev rapide via `-m 'not slow'`),
  `addopts = "--strict-markers"`.
  **Fichiers** : `pyproject.toml`, `tests/test_app_gate.py`.

---

*Audit réalisé le 2026-06-07 par analyse multi-agents (6 dimensions). Référence : voir aussi la
section TODO de [`CLAUDE.md`](CLAUDE.md).*
