# Déploiement VPS (lot 4) — API + site + HTTPS

Stack : `api` (FastAPI/uvicorn), `front` (Next.js standalone), `caddy` (HTTPS automatique).
Un seul volume `data/` partagé : caches (cours, fondamentaux, HTTP), historisation
(`history.sqlite`, qui porte aussi les jobs persistés) et référentiels locaux.

## Première mise en service

1. **DNS** : pointer le domaine (cf. `Caddyfile`) vers l'IP du VPS (enregistrement A).
2. **Secrets** : à la racine du repo sur le VPS, créer `.env` de prod :
   - `AUTH_ENABLED=true` et `AUTH_COOKIE_KEY=<clé forte>` (générer :
     `python -m comparables.auth genkey`) ;
   - `INPI_USERNAME` / `INPI_PASSWORD` (comptes annuels) ;
   - éventuellement `ANTHROPIC_API_KEY` (cascade OCR/LLM, optionnelle).
3. **Comptes analystes** : `auth_config.yaml` (modèle `auth_config.example.yaml`,
   hash : `python -m comparables.auth hash`).
4. **Lancer** :

   ```bash
   docker compose -f deploy/docker-compose.yml up -d --build
   ```

5. **Référentiels locaux** (recherches cessions en secondes au lieu de minutes) :

   ```bash
   docker compose -f deploy/docker-compose.yml exec api \
       python -m comparables.fr.referentiels refresh
   ```

   À répéter ~mensuellement (cron sur le VPS). ~2-3 Go sur disque dans `data/`.

## Mise à jour

```bash
git pull
docker compose -f deploy/docker-compose.yml up -d --build
```

Les analyses enregistrées, jobs et caches survivent (volume `data/`).

## Notes

- Aucun port applicatif n'est exposé directement : tout passe par Caddy (80/443).
- L'ancienne stack Streamlit (`docker-compose.yml` à la racine) reste indépendante.
- Sauvegarde : copier `data/history.sqlite` (analyses + jobs) suffit ; le reste est du cache.
