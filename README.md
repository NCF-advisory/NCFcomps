# Comparables boursiers — bêtas & multiples

Outil interne pour produire un tableau de **comparables boursiers** (sociétés cotées) :
bêta publié, bêta calculé par régression avec **R²**, bêta désendetté (Hamada), et
multiples de valorisation (VE/CA, VE/EBITDA, VE/EBIT, PER, P/B), avec export Excel et
tableau de bord. Données **gratuites** (Yahoo Finance ; SEC EDGAR et autres sources à venir).

> Outil d'aide à l'analyse. Les multiples ne sont pas retraités et les bêtas dépendent de
> l'indice et de la période choisis : à utiliser avec le jugement d'un analyste.

## Prérequis

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/) (recommandé) ou pip

## Installation

```bash
git clone <repo> && cd comparables-tool
cp .env.example .env            # ajuster si besoin (taux d'IS, période du bêta…)

# avec uv
uv venv
uv pip install -e ".[dev]"

# ou avec pip
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -e ".[dev]"
```

## Authentification (interne)

L'accès est protégé par mot de passe (`streamlit-authenticator`). Première configuration :

```bash
cp auth_config.example.yaml auth_config.yaml      # NON versionné

# 1 utilisateur = 1 entrée ; générer le hash de son mot de passe :
python -m comparables.auth hash "MotDePasse"      # -> coller dans auth_config.yaml
# clé de signature du cookie de session (dans .env) :
python -m comparables.auth genkey                 # -> AUTH_COOKIE_KEY=...
```

Renseigner `AUTH_COOKIE_KEY` dans `.env`. Pour désactiver l'auth en local : `AUTH_ENABLED=false`.

## Lancer l'application

```bash
streamlit run app/streamlit_app.py
```

L'interface s'ouvre dans le navigateur : saisir les tickers (un par ligne), régler le taux
d'IS, la période et la fréquence du bêta, puis « Lancer le calcul ». Le tableau, les visuels
et un bouton de téléchargement Excel s'affichent.

### Tickers

Suffixe Yahoo selon la place : `.PA` (Paris), `.AS` (Amsterdam), `.L` (Londres),
`.SW` (Suisse), `.VI` (Vienne), `.DE` (Francfort), `.MI` (Milan), aucun suffixe = USA.
Exemple par défaut : `WMS`, `GF.SW`, `AALB.AS`, `GEN.L`, `WIE.VI`, `MWA`.

## Tests

```bash
pytest          # vérifie le cœur financier (bêta, Hamada, multiples)
ruff check .
```

## Déploiement interne

```bash
docker compose up --build
```

L'authentification applicative est intégrée (voir ci-dessus). Le port 8501 n'est lié qu'à
`127.0.0.1` : pour un accès distant, placer derrière un reverse proxy HTTPS (modèle Caddy
commenté dans `docker-compose.yml`), ou intercaler oauth2-proxy pour du SSO d'entreprise.

## Structure

Voir `CLAUDE.md` pour l'architecture détaillée, le pattern d'adaptateurs de sources et la
feuille de route (TODO).

## Sources de données

| Source | Type | Couverture | Statut |
|---|---|---|---|
| Yahoo Finance (yfinance) | fondamentaux + cours | mondiale (incomplète sur small caps) | implémenté (cache disque des cours) |
| SEC EDGAR (data.sec.gov) | fondamentaux | États-Unis | reporté (articulation market_cap à trancher) |
| Stooq | cours | mondiale | abandonné (historique CSV gratuit fermé, clé API requise) |
| ESEF (filings.xbrl.org) | fondamentaux | UE (XBRL) | à implémenter (avancé) |
| Frankfurter (BCE) | taux de change | — | non utilisé (normalisation FX écartée) |
| BODACC (opendatasoft) | cessions de fonds de commerce (prix) | France | implémenté (onglet Cessions FR) |
| Ratios INPI/BCE (data.gouv) | CA, EBE, EBIT par SIREN (~10 ans) | France | implémenté (onglet Cessions FR) |
| Recherche d'entreprises (data.gouv) | NAF + identité par SIREN | France | implémenté (résolution d'identité) |

### Onglet « Cessions de fonds de commerce — France »

Estime le **prix de cession des fonds de commerce en % du CA et en multiple d'EBE** (« × fois
l'EBE »), pour **toutes les entreprises françaises**, sur une fenêtre jusqu'à 10 ans. Cessions
BODACC enrichies du CA/EBE via le jeu **Ratios INPI/BCE** (exercice calé sur la date de cession).
Gratuit, sans clé. ⚠️ Couverture partielle : CA/EBE indisponibles pour les comptes **confidentiels**
(~45 % des dépôts) ; ratios retenus entre 5–400 % du CA et 0,5–15x l'EBE. Ordre de grandeur indicatif.
En pratique le BODACC ne couvre que des cessions de fonds de commerce (commerces, TPE/PME) ; les
grands groupes cèdent des titres (actes de greffe), hors périmètre.
