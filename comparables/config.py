"""Configuration centralisee (lue depuis .env via pydantic-settings)."""
from __future__ import annotations
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Hypotheses financieres
    tax_rate: float = 0.25                 # IS pour le desendettement (Hamada)
    beta_period: str = "5y"                # historique pour la regression du beta
    beta_frequency: str = "1mo"            # "1mo" (mensuel) ou "1wk" (hebdo)
    min_beta_obs: int = 24                 # nb minimum de points de rendement

    base_currency: str = "EUR"             # devise de reference pour les visuels
    benchmark_unique: Optional[str] = None # ex: "^STOXX" pour des betas comparables

    cache_path: str = "data/cache.sqlite"
    price_cache_ttl_hours: int = 24        # duree de vie du cache disque des cours (0 = desactive)
    fundamentals_cache_ttl_hours: int = 72 # duree de vie du cache disque des fondamentaux (0 = desactive)
    yahoo_max_attempts: int = 3            # tentatives par appel Yahoo (1 = pas de retry)
    yahoo_backoff_seconds: float = 1.0     # attente avant nouvelle tentative (doublee a chaque essai)
    pipeline_max_workers: int = 4          # parallelisme du lot (borne pour menager les quotas)
    history_db_path: str = "data/history.sqlite"   # base SQLite d'historisation des analyses

    # Authentification interne (Step 5) - secrets via .env, jamais en dur
    auth_enabled: bool = True
    auth_config_path: str = "auth_config.yaml"     # identifiants (hash bcrypt), non versionne
    auth_cookie_name: str = "comparables_auth"
    auth_cookie_key: str = "CHANGE_ME"             # cle de signature du cookie - A SURCHARGER via .env
    auth_cookie_expiry_days: float = 7.0

    # Backend API (lot 1) - origines CORS du front (separees par des virgules)
    cors_origins: str = "http://localhost:3000"

    # Extraction des comptes annuels INPI (lot 3) - inactifs sans credentials
    inpi_username: Optional[str] = None    # compte data.inpi.fr (gratuit)
    inpi_password: Optional[str] = None
    anthropic_api_key: Optional[str] = None  # cle API Claude (etape LLM de la cascade)
    claude_model: str = "claude-haiku-4-5"   # decision cout 2026-06-10 (~0,5 ct/document)

    # Cles optionnelles (sources a paliers gratuits) - non requises par defaut
    fmp_api_key: Optional[str] = None
    alphavantage_api_key: Optional[str] = None


settings = Settings()

# Indice de reference Yahoo par suffixe de place de cotation.
INDEX_BY_SUFFIX: dict[str, str] = {
    "": "^GSPC",        # USA          -> S&P 500
    "SW": "^SSMI",      # Suisse       -> SMI
    "AS": "^AEX",       # Amsterdam    -> AEX
    "L": "^FTSE",       # Londres      -> FTSE 100
    "VI": "^ATX",       # Vienne       -> ATX
    "PA": "^FCHI",      # Paris        -> CAC 40
    "DE": "^GDAXI",     # Francfort    -> DAX
    "MI": "FTSEMIB.MI", # Milan        -> FTSE MIB
    "MC": "^IBEX",      # Madrid       -> IBEX 35
    "BR": "^BFX",       # Bruxelles    -> BEL 20
    "ST": "^OMX",       # Stockholm    -> OMX Stockholm 30
}
DEFAULT_INDEX = "^GSPC"


def index_for(ticker: str) -> str:
    """Indice de reference a utiliser pour un ticker donne."""
    if settings.benchmark_unique:
        return settings.benchmark_unique
    suffix = ticker.rsplit(".", 1)[1] if "." in ticker else ""
    return INDEX_BY_SUFFIX.get(suffix, DEFAULT_INDEX)
