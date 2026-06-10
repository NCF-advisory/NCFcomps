"""Extraction des comptes annuels INPI (lot 3) : cascade XBRL/PDF/OCR/LLM -> CA, EBE, EBIT.

Modules purs et testables ; le seul point réseau est `inpi_client` (API RNE, credentials
requis) et `llm` (API Claude, clé requise) — tous deux inactifs sans configuration.
"""
