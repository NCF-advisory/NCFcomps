# Reprendre le projet sur une nouvelle machine

Recette de démarrage quand tu clones le dépôt sur un autre ordinateur.
Pour la doc générale (tickers, déploiement Docker, sources), voir [`README.md`](README.md).

## Principe : les secrets ne sont **jamais** dans Git

Le dépôt contient **tout le code** et des **modèles** de configuration (`.env.example`,
`auth_config.example.yaml`), mais **aucun secret**. C'est volontaire (règle n°4 du projet) :
un secret commité reste pour toujours dans l'historique Git. Les fichiers sensibles sont
exclus par `.gitignore` et se **recréent** localement.

| Élément | Dans Git ? | Sur la nouvelle machine |
|---|---|---|
| Code, tests, modèles `*.example` | ✅ oui | récupérés par `git clone` |
| `.env` (config + `AUTH_COOKIE_KEY`) | ❌ non | à recréer depuis `.env.example` |
| `auth_config.yaml` (identifiants, hash bcrypt) | ❌ non | à recréer depuis `auth_config.example.yaml` |
| `data/cache.sqlite`, `data/prices/` | ❌ non | rien à faire — cache reconstruit tout seul |
| `data/history.sqlite` (analyses sauvegardées) | ❌ non | à copier **seulement** si tu veux ton historique |
| `.venv/` (environnement Python) | ❌ non | à recréer avec `uv` |

## Démarrage rapide

> Exemples en PowerShell (Windows). Sur macOS/Linux : `cp` au lieu de `Copy-Item`,
> et `source .venv/bin/activate` pour activer l'environnement.

```powershell
# 1. Récupérer le code
git clone https://github.com/NCF-advisory/NCFcomps.git
cd NCFcomps

# 2. Recréer l'environnement Python (Python >= 3.11, uv installé)
uv venv
uv pip install -e ".[dev]"

# 3. Recréer la config locale à partir des modèles
Copy-Item .env.example .env
python -m comparables.auth genkey        # -> coller le résultat dans AUTH_COOKIE_KEY (.env)

Copy-Item auth_config.example.yaml auth_config.yaml
python -m comparables.auth hash "TonMotDePasse"   # -> coller le hash dans auth_config.yaml

# 4. Lancer
streamlit run app/streamlit_app.py
```

Pour développer/tester sans authentification, mettre `AUTH_ENABLED=false` dans `.env`.

> Sous Windows, appeler les outils via `python -m <outil>` (ex. `python -m pytest`,
> `python -m ruff check .`) : les *shims* `.exe` du `.venv` peuvent être bloqués par
> la politique de contrôle applicatif.

## Migrer une config / des données existantes (optionnel)

Si tu veux retrouver **exactement** les mêmes identifiants ou ton **historique d'analyses**
plutôt que d'en recréer, transfère ces fichiers depuis l'ancienne machine :

- `.env`
- `auth_config.yaml`
- `data/history.sqlite` (uniquement si tu veux tes runs sauvegardés)

**Toujours de manière sécurisée et hors-bande** : clé USB chiffrée, gestionnaire de mots de
passe (note/fichier sécurisé), ou partage de fichiers interne NCF.
**Jamais** via Git, ni par e-mail en clair, ni dans un message de chat.

> Note : `AUTH_COOKIE_KEY` ne sert qu'à signer le cookie de session. Une clé différente
> sur chaque machine est sans conséquence (il faudra juste se reconnecter). Pour se
> connecter, seul un `auth_config.yaml` valide compte.

## Rappel de sécurité

Ne **jamais** `git add` les fichiers `.env`, `auth_config.yaml` ou `data/*.sqlite`. Ils sont
déjà couverts par `.gitignore` ; en cas de doute, vérifier avant un commit :

```powershell
git status                       # ces fichiers ne doivent PAS apparaître
git check-ignore .env auth_config.yaml data/history.sqlite   # doit les lister (= ignorés)
```

## Authentification GitHub (pousser depuis la nouvelle machine)

Le dépôt appartient à l'organisation **NCF-advisory**. Pour pousser, s'authentifier avec un
compte ayant un accès **Write** à `NCF-advisory/NCFcomps` (le compte `ncf@ncf-advisory.fr`,
pas un compte personnel). Au premier `git push`, une fenêtre de connexion GitHub s'ouvre :
se connecter avec le bon compte. En cas d'erreur **403** (mauvais compte mémorisé), purger
l'identifiant puis recommencer :

```powershell
"protocol=https`nhost=github.com`n`n" | git credential reject
git push
```
