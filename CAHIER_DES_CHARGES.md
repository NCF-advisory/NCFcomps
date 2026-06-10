# Cahier des charges — Plateforme d'évaluation NCF

> Validé le 2026-06-10 avec l'utilisateur. Ce document cadre l'évolution de NCFcomps
> vers un site web interne complet. Il complète `CLAUDE.md` (règles de code) et
> `AMELIORATIONS.md` (backlog détaillé issu de l'audit du 2026-06-07).

## 1. Objectif et décisions de cadrage

Site web **interne** au cabinet d'évaluation (analystes uniquement) couvrant deux besoins :

- **Module 1 — Comparables boursiers** : bêtas endettés/désendettés et multiples de
  valorisation d'un échantillon de sociétés cotées.
- **Module 2 — Cessions de fonds de commerce (France)** : prix de cession en **% du CA**
  et en **multiple d'EBE**, à partir des sources publiques gratuites.

Décisions actées :

| Question | Décision |
|---|---|
| Audience | **Interne cabinet uniquement** (pas de vitrine publique, pas de SaaS) |
| Interface | **Vrai site web** : backend FastAPI + frontend Next.js (référence d'ambition : caudia.fr) |
| Hébergement | **VPS du cabinet** (docker-compose + Caddy HTTPS) |
| Extraction comptes INPI | **Dès le départ**, via une cascade majoritairement gratuite (voir §5) |
| Base existante | **On garde le moteur `comparables/`** (cœur financier testé) ; on rebâtit l'enveloppe. Pas de réécriture from scratch. |

## 2. Architecture cible

```
NCFcomps/  (monorepo)
├── comparables/        # moteur existant : calculs purs (finance/*) + sources + fr/
├── backend/            # NOUVEAU — API FastAPI
│   ├── api/            # endpoints REST : auth, comparables, cessions, runs, exports
│   ├── worker/         # tâches longues : batch tickers, extraction comptes INPI
│   └── db/             # SQLAlchemy (SQLite WAL au départ, migrable Postgres)
├── frontend/           # NOUVEAU — Next.js + Tailwind
└── deploy/             # docker-compose : caddy (HTTPS) + api + front + worker
```

- Les calculs longs (lot de tickers, extraction) passent par une file de tâches avec
  progression consultable depuis l'UI.
- Auth : comptes internes (bcrypt, migration des utilisateurs `auth_config.yaml`),
  sessions par cookie. Exposition réseau uniquement via Caddy en HTTPS.
- L'app Streamlit existante reste utilisable pendant la transition, puis sera retirée.

## 3. Module 1 — Comparables boursiers

- Saisie par tickers ou noms de sociétés ; paramètres : période, fréquence, taux d'IS.
- Par société : bêta publié, bêta de régression + R² + n_obs, bêta ajusté Blume,
  gearing, bêta désendetté (Hamada), re-endettement à structure cible, multiples
  (VE/CA, VE/EBITDA, VE/EBIT, PER, P/B).
- Sélection/exclusion de comparables **sans recalcul réseau** (stats recalculées en direct).
- Fiabilité visible : R² faible signalé, couverture par ligne (✓/⚠/✗), source affichée.
- Export Excel formaté ; historisation des runs + comparaison entre deux dates.
- Sources : **Yahoo Finance** (retry/backoff + caches disque), contrôle via bêtas
  sectoriels Damodaran ; **SEC EDGAR** en extension ultérieure (fondamentaux US).

## 4. Module 2 — Cessions de fonds de commerce France

- Recherche par activité (NAF), zone géographique, période (fenêtre 10 ans).
- Résultats : % du CA et × EBE, médiane/quartiles/n par activité, indicateur de
  fiabilité par ligne, liens de vérification (annonce BODACC, annuaire-entreprises).
- Sources : **BODACC** (cessions + prix), **ratios INPI/BCE** (CA/EBE),
  **Recherche d'entreprises** data.gouv (identité/NAF) — l'existant, fiabilisé
  (dédoublonnage des annonces, correction du SIREN cédant).
- Limite structurelle assumée : comptes confidentiels (~45 % des dépôts) hors de portée.

### 4 bis. Fraîcheur des comptes (convention et garde-fous) — décidé le 2026-06-10

**Convention de référence** : le CA/EBE rapporté au prix est celui du **dernier exercice
clos avant la date de cession** — c'est sur ces comptes que le prix a été négocié, et
c'est avec la même convention que le barème sera appliqué à une cible (cohérence
échantillon ↔ usage). Un décalage de 6-18 mois est donc normal et ne dégrade pas la
fiabilité. Exiger « la même année » est méthodologiquement faux (exercice non clos au
moment du deal) et viderait l'échantillon.

**Le problème à traiter est le décalage excessif** (2-3 ans), causé par : le délai légal
de dépôt (~7 mois après clôture, incompressible), le retard de publication du dataset
ratios INPI/BCE (6-12 mois de plus), et le fallback silencieux de `pick_for_date` (faute
d'exercice antérieur, il prend le plus récent sans le signaler). Garde-fous à implémenter :

1. **Indicateur de fraîcheur par ligne** : écart en mois entre clôture de l'exercice et
   date de cession, affiché dans le tableau (vert ≤ 18 mois, orange 18-30, rouge au-delà).
2. **Filtre « écart maximum »** dans le formulaire (défaut ~24-30 mois) : les lignes
   au-delà sortent des médianes mais restent visibles (l'analyste arbitre
   fraîcheur/volume).
3. **Signalement du fallback** : marquer explicitement les lignes dont l'exercice retenu
   est postérieur à la cession ou très ancien.

L'**accès API INPI/RNE (lot 3)** améliore directement la fraîcheur : les comptes déposés
sont disponibles dès le dépôt, 6-12 mois avant leur apparition dans le dataset ratios
(ex. exercice 2024 récupérable mi-2025 au lieu de se rabattre sur 2023/2022). Il ne
contourne ni les comptes confidentiels ni le délai légal de dépôt — aucune source ne le
permet légalement.

## 5. Extraction des comptes annuels INPI (cascade)

Quand le CA/EBE manque dans le dataset ratios INPI/BCE, le worker récupère les comptes
déposés via l'**API INPI/RNE** (compte gratuit requis) et les traite en cascade :

1. **XBRL / dépôt structuré** → parsing Python direct (gratuit, fiabilité max).
2. **PDF avec couche texte** → extraction par position (`pdfplumber`/`PyMuPDF`) sur la
   liasse fiscale standardisée CERFA 2050-2053 (gratuit).
3. **PDF scanné** → OCR **Tesseract** + lecture du formulaire (gratuit).
4. **API Claude en dernier recours** (Haiku + Batch API −50 %, ~0,4 ct €/document) pour
   les documents que la cascade n'a pas su lire.

Chaque document n'est extrait **qu'une fois** (cache définitif en base). Budget API
estimé : ~10-20 € au démarrage, quelques €/mois ensuite. L'abonnement Claude ne couvre
pas l'API : prévoir une clé API dédiée avec petit budget.

## 6. Exigences non fonctionnelles

- **Déploiement** : docker-compose sur VPS, Caddy frontal HTTPS, sauvegardes
  automatiques de la base, logs.
- **Quotas / CGU** : tout appel Yahoo derrière cache + retry borné ; respect du quota
  API INPI ; User-Agent conforme partout ; sources strictement gratuites (règle CLAUDE.md).
- **Secrets** : `.env` non versionné (clé Claude API, jeton INPI, clé cookie).
- **Qualité** : CI GitHub Actions (pytest + ruff), tests obligatoires sur tout calcul
  financier, cœur `finance/*` pur (aucune I/O).
- **RGPD** : données d'entreprises publiques uniquement ; registre minimal pour les
  comptes utilisateurs internes.

## 7. Phasage

| Lot | Contenu | Statut |
|---|---|---|
| **0 — Fiabilisation du moteur** | Bug Excel `_stats`, retry Yahoo + cache fondamentaux, parallélisation du lot, dédoublonnage BODACC, fix SIREN cédant, CI GitHub Actions, `.gitattributes` | **fait** (2026-06-10) |
| **1 — Backend API** | FastAPI (`backend/`), auth cookie signé, endpoints des 2 modules (jobs + progression), stats de sélection sans re-fetch, runs + ré-export Excel. Lancement : `uvicorn backend.main:app` (1 worker, file en mémoire). | **fait** (2026-06-10) |
| **2 — Frontend** | Next.js 15 + Tailwind 4 (`frontend/`) : login, comparables (sélection/exclusion sans re-fetch, stats vivantes), cessions FR (synthèse + barème par activité + liens de vérification), historique, exports .xlsx. Proxy `/api` vers FastAPI (même origine, cookies sans CORS). Design « registre de banque privée » (papier/encre verte/laiton, Newsreader + IBM Plex). | **fait** (2026-06-10) |
| **3 — Extraction comptes INPI** | **Préparé sans credentials** (2026-06-10) : `comparables/fr/comptes/` — lecture de liasse 2052/2033-B (CA/EBE/EBIT recalculés, convention BdF), extraction PDF texte (pdfplumber, colonnes N/N-1), OCR Tesseract optionnel, extracteur Claude (inactif sans clé, Haiku par défaut), client API RNE, fallback branché dans `build_cessions` (inactif sans credentials). **Reste à faire une fois compte INPI + clé Claude fournis** : valider les schémas RNE réels, vérifier les codes 2033-B sur liasse réelle, cache définitif des extractions (un document = une extraction), Batch API. **+ Garde-fous fraîcheur (§4 bis)** : indicateur d'écart clôture/cession par ligne, filtre « écart maximum » (défaut 24-30 mois), signalement du fallback d'exercice. | partiel |
| **4 — Déploiement VPS** | docker-compose complet, Caddy, backups, recette | à faire |

Prérequis côté cabinet pour le lot 3 : compte INPI (data.inpi.fr, gratuit) + clé API
Claude avec petit budget.
