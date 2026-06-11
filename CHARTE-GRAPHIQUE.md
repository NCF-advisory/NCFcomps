# Charte graphique Novances Évaluation

Document de référence autoportant. Il décrit l'intégralité du système graphique du site `https://novances-evaluation.fr` (site statique HTML/CSS/JS vanille) : tokens, couleurs, typographie, layout, chrome, boutons, formulaires, cards, animations, iconographie, patterns de pages et voix éditoriale. Toutes les valeurs sont copiées verbatim des sources du site au 11 juin 2026.

## Comment utiliser ce document

Ce document est conçu pour être donné tel quel à un assistant (Claude ou autre) chargé d'appliquer cette charte à un autre site NCF / Novances. Instructions pour l'assistant qui reçoit ce document :

1. **Commencer par recopier le bloc `:root` complet** (section 1) dans le CSS global du nouveau projet. C'est la source de vérité : toute couleur, ombre ou tint doit provenir de ces tokens.
2. **Recopier ensuite les styles de base** (reset, body, halo de fond, scrollbar, focus-visible) puis le chrome (navbar, footer) et les boutons : ces blocs sont fournis complets et copy-pasteables.
3. **Respecter les interdits, non négociables** :
   - Palette « Institutionnel clair v2 » uniquement. Aucune couleur ad hoc, aucune nouvelle teinte.
   - Une seule famille typographique : Inter (Google Fonts). Pas de serif, pas de seconde famille.
   - Icônes : librairie maison ncf-icons uniquement (section 7). Jamais de Heroicons, Lucide, FontAwesome, Material, ni d'emojis dans l'interface.
   - Chaque animation doit avoir son opt-out `prefers-reduced-motion` (CSS et JS).
   - Texte : sentence case, jamais de tiret cadratin « — » dans les contenus (préférer parenthèses, virgules, deux-points).
4. **Adapter sans trahir** : les valeurs structurelles (breakpoints, paddings, radius, durées, easings) sont la signature du site. Les reprendre telles quelles ; n'ajuster que les contenus.

## Identité en cinq points

1. **Palette « Institutionnel clair v2 »** : fond ivoire bleuté `#EAF0F8`, texte navy `#061838` à `#586A8A`, accent cyan azur `#0EA5E9` (CTA en `#0369A1` pour l'accessibilité AA). Cible : sérieux, posé, légèrement chaleureux.
2. **Profondeur par halos, pas par ombres ambiantes** : double halo radial fixe sur le body (accent en haut à gauche, violet en bas à droite), radial-gradients très dilués (alphas 0.04 à 0.10) en `::before` des sections et héros. Les cards n'ont d'ombre qu'au survol (sauf pièces maîtresses).
3. **Typographie Inter unique** : titres serrés (letter-spacing négatif, line-height 1.05 à 1.15), corps aéré (1.6 à 1.75), micro-textes UI en uppercase gras avec letter-spacing large (0.08em à 0.18em).
4. **Motion sobre et signé** : reveals discrets au scroll (translateY 20px, 0.7s), lift de 1 à 6 px au hover, deux easings maison `cubic-bezier(.2,.8,.2,1)` et `cubic-bezier(0.16, 1, 0.3, 1)`, transitions couleur en 0.2s.
5. **Iconographie propriétaire** : 36 icônes line-art 24×24, trait 1.5, `currentColor`, avec la signature « équerres » en coins opposés.

---

## 1. Fondations et tokens

Source unique de vérité : le bloc `:root` de `assets/css/global.css`. Palette active : « Institutionnel clair v2 » (fond ivoire bleuté, texte navy, accent bleu, cible : sérieux, posé, légèrement chaleureux). Tout nouveau projet doit recopier ce bloc tel quel.

### 1. Bloc `:root` complet (verbatim, copy-pasteable)

```css
:root {
  /* ── 1. Fondations (page surfaces) — 4 niveaux de hiérarchie ── */
  --bg-base:       #EAF0F8;      /* fond principal — bleu pâle assumé */
  --bg-deep:       #D6DFEC;      /* niveau bas (footer) */
  --bg-elevated:   #F4F7FC;      /* sections "elevated" */
  --bg-mid:        #FFFFFF;      /* cartes blanches */
  --bg-high:       #FFFFFF;
  --bg-higher:     #E0E8F3;      /* highlight surface */

  /* Cartes — gradient top blanc / bottom légèrement bleuté */
  --card-bg:       linear-gradient(160deg, #FFFFFF 0%, #ECF1F9 100%);
  --card-bg-strong:linear-gradient(160deg, #FFFFFF 0%, #E2EAF5 100%);
  --card-bg-soft:  linear-gradient(160deg, #FBFCFE 0%, #ECF1F9 100%);

  /* Surfaces (overlays sombres sur clair) */
  --surface-low:   rgba(15, 23, 42, 0.035);
  --surface-mid:   rgba(15, 23, 42, 0.06);
  --surface-high:  rgba(15, 23, 42, 0.09);
  --surface-strong:rgba(15, 23, 42, 0.14);

  /* Scrims — voiles sur images / overlays */
  --scrim-1: rgba(10, 31, 61, 0.10);
  --scrim-2: rgba(10, 31, 61, 0.18);
  --scrim-3: rgba(10, 31, 61, 0.06);

  /* ── 2. Bordures / séparateurs ── */
  --line-1: rgba(15, 23, 42, 0.07);
  --line-2: rgba(15, 23, 42, 0.13);
  --line-3: rgba(15, 23, 42, 0.20);
  --line-4: rgba(15, 23, 42, 0.28);
  --line-5: rgba(15, 23, 42, 0.38);

  /* ── 3. Texte — hiérarchie 4 niveaux, tous ≥ AA ── */
  --text-strong:  #061838;       /* titres */
  --text-1:       #182747;       /* paragraphes */
  --text-2:       #3A4A6B;       /* secondaires */
  --text-3:       #586A8A;       /* tertiaires / muted */
  --text-on-accent: #FFFFFF;     /* texte sur surface accent (CTA) */

  /* ── 4. Accent principal — Cyan azur ── */
  --accent:        #0EA5E9;       /* CTA base */
  --accent-bright: #38BDF8;       /* hover + eyebrows */
  --accent-soft:   #BAE6FD;
  --accent-deep:   #0284C7;
  --accent-deeper: #0369A1;       /* texte/CTA accessibles : ≥4.5:1 sur blanc (WCAG AA) */
  --accent-ink:    #075985;       /* état hover des CTA accessibles */

  /* Alphas d'accent (glows / tints) */
  --accent-a-04: rgba(14, 165, 233, 0.06);
  --accent-a-06: rgba(14, 165, 233, 0.09);
  --accent-a-08: rgba(14, 165, 233, 0.11);
  --accent-a-10: rgba(14, 165, 233, 0.13);
  --accent-a-12: rgba(14, 165, 233, 0.16);
  --accent-a-15: rgba(14, 165, 233, 0.19);
  --accent-a-18: rgba(14, 165, 233, 0.22);
  --accent-a-22: rgba(14, 165, 233, 0.26);
  --accent-a-25: rgba(14, 165, 233, 0.30);
  --accent-a-30: rgba(14, 165, 233, 0.35);
  --accent-a-35: rgba(14, 165, 233, 0.40);
  --accent-a-40: rgba(14, 165, 233, 0.46);

  /* ── 5. Brand secondaire (violet) ── */
  --violet:       #532EFB;
  --violet-soft:  rgba(83, 46, 251, 0.16);
  --violet-tint:  rgba(83, 46, 251, 0.06);
  --magenta: #EC4899;
  --green:   #22C55E;

  /* ── 6. Cas d'usage (hues distincts par offre, utilisés dans /ressources) ── */
  --c-succession: #F59E0B;
  --c-litiges:    #532EFB;
  --c-croissance: #10B981;

  /* ── 6b. Personas — famille de bleus froids (cohérence cartes + pages) ── */
  --p-entrepreneur: #2563EB; --p-entrepreneur-soft: rgba(37, 99, 235, 0.14);  --p-entrepreneur-tint: rgba(37, 99, 235, 0.06);
  --p-ec:           #0EA5E9; --p-ec-soft:           rgba(14, 165, 233, 0.14); --p-ec-tint:           rgba(14, 165, 233, 0.06);
  --p-avocat:       #4F46E5; --p-avocat-soft:       rgba(79, 70, 229, 0.14);  --p-avocat-tint:       rgba(79, 70, 229, 0.06);
  --p-notaire:      #1E40AF; --p-notaire-soft:      rgba(30, 64, 175, 0.14);  --p-notaire-tint:      rgba(30, 64, 175, 0.06);

  /* ── 7. Chrome (navbar, band, mob-menu, logo) ── */
  --navbar-bg:        rgba(234, 240, 248, 0.85);
  --navbar-bg-scroll: rgba(234, 240, 248, 0.96);
  --band-bg:          rgba(6, 24, 56, 0.97);
  --band-text:        rgba(255, 255, 255, 0.94);
  --band-text-strong: #FFFFFF;
  --band-text-dim:    rgba(255, 255, 255, 0.74);
  --mob-menu-bg:      rgba(234, 240, 248, 0.98);
  --logo-filter:      none;

  /* ── 8. ALIAS LEGACY (rétrocompat — pointent sur les tokens) ── */
  --navy-deep: var(--bg-base);
  --navy:      var(--bg-mid);
  --navy-mid:  var(--bg-high);
  --navy-2:    var(--bg-higher);
  --cyan:        var(--accent);
  --cyan-bright: var(--accent-bright);
  --cyan-soft:   var(--accent-soft);
  --blue:        var(--accent);
  --blue-d:      var(--accent-deep);
  --ink:     var(--text-1);
  --ink-dim: var(--text-2);
  --muted:   var(--text-3);
  --surface-1: var(--card-bg);
  --surface-2: var(--card-bg-strong);
  --border:        var(--line-2);
  --border-strong: var(--line-3);
  --glow:          var(--accent-a-30);
  --gl: var(--navy);
  --gm: var(--ink-dim);
  --gd: var(--ink);

  /* Fonts */
  --font-sans: 'Inter', ui-sans-serif, system-ui, sans-serif;
}
```

### 2. Table des couleurs et rôles d'usage

#### Fonds (surfaces de page)

| Token | Valeur | Rôle |
|---|---|---|
| `--bg-base` | `#EAF0F8` | Fond principal de page, bleu pâle assumé (appliqué sur `html` et `body`) |
| `--bg-deep` | `#D6DFEC` | Niveau bas : footer (en bas de gradient) |
| `--bg-elevated` | `#F4F7FC` | Sections « elevated » (alternance avec le fond base) |
| `--bg-mid` | `#FFFFFF` | Cartes blanches |
| `--bg-high` | `#FFFFFF` | Idem (niveau supérieur, même blanc) |
| `--bg-higher` | `#E0E8F3` | Surface de highlight |

#### Cartes (gradients, jamais de fond plat pour les cards)

| Token | Valeur | Rôle |
|---|---|---|
| `--card-bg` | `linear-gradient(160deg, #FFFFFF 0%, #ECF1F9 100%)` | Carte standard : haut blanc, bas légèrement bleuté |
| `--card-bg-strong` | `linear-gradient(160deg, #FFFFFF 0%, #E2EAF5 100%)` | Carte plus contrastée |
| `--card-bg-soft` | `linear-gradient(160deg, #FBFCFE 0%, #ECF1F9 100%)` | Carte discrète |

#### Surfaces et scrims (alphas sombres sur fond clair)

| Token | Valeur | Rôle |
|---|---|---|
| `--surface-low` | `rgba(15, 23, 42, 0.035)` | Teinte de fond la plus légère (ex. fond de `.btn-outline`) |
| `--surface-mid` | `rgba(15, 23, 42, 0.06)` | Hover de surface |
| `--surface-high` | `rgba(15, 23, 42, 0.09)` | Surface appuyée |
| `--surface-strong` | `rgba(15, 23, 42, 0.14)` | La plus marquée (ex. pouce de scrollbar) |
| `--scrim-1` | `rgba(10, 31, 61, 0.10)` | Voile sur image, intensité moyenne |
| `--scrim-2` | `rgba(10, 31, 61, 0.18)` | Voile plus dense |
| `--scrim-3` | `rgba(10, 31, 61, 0.06)` | Voile le plus léger |

#### Bordures et séparateurs (échelle de 5)

| Token | Valeur | Rôle |
|---|---|---|
| `--line-1` | `rgba(15, 23, 42, 0.07)` | Séparateur le plus discret |
| `--line-2` | `rgba(15, 23, 42, 0.13)` | Bordure par défaut (alias legacy `--border`) |
| `--line-3` | `rgba(15, 23, 42, 0.20)` | Bordure renforcée, hover (alias `--border-strong`) |
| `--line-4` | `rgba(15, 23, 42, 0.28)` | Bordure forte |
| `--line-5` | `rgba(15, 23, 42, 0.38)` | Bordure maximale |

#### Texte (hiérarchie 4 niveaux, tous au moins AA sur les fonds clairs)

| Token | Valeur | Rôle |
|---|---|---|
| `--text-strong` | `#061838` | Titres |
| `--text-1` | `#182747` | Paragraphes (couleur par défaut du `body`) |
| `--text-2` | `#3A4A6B` | Textes secondaires (sous-titres, liens nav, footer) |
| `--text-3` | `#586A8A` | Tertiaire, muted (copyright, mentions) |
| `--text-on-accent` | `#FFFFFF` | Texte posé sur une surface accent (CTA) |

#### Accent principal (cyan azur)

| Token | Valeur | Rôle |
|---|---|---|
| `--accent` | `#0EA5E9` | Accent de base : soulignements, fines lignes décoratives |
| `--accent-bright` | `#38BDF8` | Hover et eyebrows, anneau lumineux des CTA |
| `--accent-soft` | `#BAE6FD` | Variante très claire |
| `--accent-deep` | `#0284C7` | Eyebrows de section, outline de focus clavier |
| `--accent-deeper` | `#0369A1` | Fond des CTA et textes accent accessibles : contraste au moins 4.5:1 sur blanc (WCAG AA) |
| `--accent-ink` | `#075985` | État hover des CTA accessibles |

Les 12 alphas `--accent-a-04` à `--accent-a-40` (base `rgba(14, 165, 233, …)`, opacités de 0.06 à 0.46, valeurs exactes dans le bloc ci-dessus) servent aux glows, tints et ombres colorées. Important : le suffixe numérique ne correspond pas à l'opacité réelle (ex. `--accent-a-30` vaut une opacité de 0.35), recopier les valeurs telles quelles.

#### Marque secondaire et hues cas d'usage

| Token | Valeur | Rôle |
|---|---|---|
| `--violet` | `#532EFB` | Marque secondaire (minoritaires / litiges), seul violet autorisé |
| `--violet-soft` | `rgba(83, 46, 251, 0.16)` | Fond teinté violet |
| `--violet-tint` | `rgba(83, 46, 251, 0.06)` | Tint violet très léger (utilisé dans le gradient de fond du body) |
| `--magenta` | `#EC4899` | Couleur ponctuelle existante dans les tokens |
| `--green` | `#22C55E` | Couleur ponctuelle existante dans les tokens |
| `--c-succession` | `#F59E0B` | Hue de l'offre « succession » (ambre), utilisée dans /ressources |
| `--c-litiges` | `#532EFB` | Hue de l'offre « litiges » (= violet de marque) |
| `--c-croissance` | `#10B981` | Hue de l'offre « croissance » (vert émeraude) |

#### Personas (famille de bleus froids, cartes et pages cibles)

Chaque persona a un trio : couleur pleine, `-soft` (alpha 0.14) et `-tint` (alpha 0.06).

| Persona | Token | Valeur pleine |
|---|---|---|
| Entrepreneur | `--p-entrepreneur` | `#2563EB` |
| Expert-comptable | `--p-ec` | `#0EA5E9` |
| Avocat | `--p-avocat` | `#4F46E5` |
| Notaire | `--p-notaire` | `#1E40AF` |

#### Chrome (navbar, bandeau, menu mobile)

| Token | Valeur | Rôle |
|---|---|---|
| `--navbar-bg` | `rgba(234, 240, 248, 0.85)` | Fond glass de la navbar au repos |
| `--navbar-bg-scroll` | `rgba(234, 240, 248, 0.96)` | Fond navbar une fois scrollée |
| `--band-bg` | `rgba(6, 24, 56, 0.97)` | Bandeau sombre (navy quasi opaque) |
| `--band-text` | `rgba(255, 255, 255, 0.94)` | Texte du bandeau |
| `--band-text-strong` | `#FFFFFF` | Texte fort du bandeau |
| `--band-text-dim` | `rgba(255, 255, 255, 0.74)` | Texte atténué du bandeau |
| `--mob-menu-bg` | `rgba(234, 240, 248, 0.98)` | Fond du menu mobile |
| `--logo-filter` | `none` | Filtre appliqué aux logos (aucun en palette claire) |

### 3. Règle stricte de palette

- **Palette « Institutionnel clair v2 » uniquement. Aucune couleur ad hoc.** Toute couleur utilisée dans le CSS doit provenir d'un token `:root` ci-dessus.
- Les seuls accents colorés autorisés par offre sont les hues cas d'usage `--c-succession`, `--c-litiges`, `--c-croissance`, plus `--violet: #532EFB` pour la marque secondaire (minoritaires / litiges).
- Les alias **legacy** `--navy*`, `--cyan*`, `--blue*`, `--ink*` (ainsi que `--muted`, `--surface-1/2`, `--border*`, `--glow`, `--gl/--gm/--gd`) existent uniquement pour la rétrocompatibilité : ils pointent vers les vrais tokens. **Dans tout nouveau code, utiliser les tokens sémantiques** : `--accent`, `--text-1`, `--text-strong`, `--bg-base`, `--line-2`, etc.
- Pour le texte ou les fonds de CTA en accent, privilégier `--accent-deeper` (au moins 4.5:1 sur blanc) plutôt que `--accent`, qui sert aux éléments décoratifs.

### 4. Styles de base globaux

Reset minimal, fond de page avec double halo radial fixe (accent en haut à gauche, violet en bas à droite), scrollbar custom WebKit et focus clavier visible. Bloc complet copy-pasteable :

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; background: var(--bg-base); }
body {
  font-family: var(--font-sans);
  background: var(--bg-base);
  color: var(--text-1);
  overflow-x: hidden;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  position: relative;
}
body::before {
  content: '';
  position: fixed; inset: 0;
  background:
    radial-gradient(ellipse 900px 700px at 15% 15%, var(--accent-a-06) 0%, transparent 55%),
    radial-gradient(ellipse 700px 500px at 85% 85%, var(--violet-tint) 0%, transparent 55%);
  z-index: 0; pointer-events: none;
}
body > * { position: relative; z-index: 1; }

::-webkit-scrollbar       { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--surface-strong); border-radius: 999px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent-a-35); }

/* Compense la hauteur navbar pour les ancres */
:target { scroll-margin-top: 80px; }

/* Focus clavier visible (a11y) */
a:focus-visible, button:focus-visible, summary:focus-visible, [tabindex]:focus-visible,
.nav-cta:focus-visible, .btn-primary:focus-visible, .btn-outline:focus-visible, .btn-ghost:focus-visible, .nav-link:focus-visible {
  outline: 2px solid var(--accent-deep);
  outline-offset: 2px;
  border-radius: 6px;
}
```

Points d'intention :

- **Police** : `--font-sans: 'Inter', ui-sans-serif, system-ui, sans-serif` est l'unique famille. `line-height: 1.5` par défaut sur le body, antialiasing activé.
- **Halo de fond** : le `body::before` en `position: fixed` donne la profondeur caractéristique du site (tint accent à 15% / 15%, tint violet à 85% / 85%). Tout contenu direct du body passe en `position: relative; z-index: 1` pour rester au-dessus.
- **Liens** : il n'y a pas de style global pour `a`. Chaque composant style ses liens (`.nav-link`, `.footer-link`, boutons), toujours avec `text-decoration: none` et une transition `color 0.2s` vers `--text-strong` ou `--accent-bright` au hover.
- **`::selection`** : aucune règle définie dans le site, ne pas en ajouter.
- **Mobile** : à `max-width: 640px`, le body passe à `font-size: 15px` et `:target { scroll-margin-top: 72px; }` (navbar réduite à 62px).

---

## 2. Typographie et layout

### 1. Famille typographique

Une seule famille pour tout le site : **Inter** (Google Fonts). Pas de famille secondaire, pas de serif, pas de monospace dans l'UI publique.

Import exact à placer dans le `<head>` (avec les deux preconnect) :

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet" />
```

Graisses importées : **400, 500, 600, 700, 800, 900** (pas de 300 en production).

Token et stack de fallback exacts (défini dans `:root`) :

```css
--font-sans: 'Inter', ui-sans-serif, system-ui, sans-serif;
```

Réglages de base du `body` (à reproduire tels quels, le rendu "net" d'Inter en dépend) :

```css
body {
  font-family: var(--font-sans);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
@media (max-width: 640px) {
  body { font-size: 15px; }
}
```

### 2. Échelle typographique observée

Logique générale : titres très serrés (letter-spacing négatif, line-height compact), corps de texte aéré (line-height 1.6 à 1.75), petits textes UI denses en graisse 700 avec letter-spacing positif. Les tailles de titres utilisent `clamp()` pour la fluidité.

#### Titres

| Rôle | Taille | Graisse | line-height | letter-spacing |
|---|---|---|---|---|
| H1 hero (home) | `clamp(2rem, 3.2vw, 3rem)` | 700 | 1.08 | -0.032em |
| H1 tarifs | `clamp(2rem, 3vw, 2.8rem)` | 900 | 1.08 | -0.028em |
| H1 article | `clamp(2rem, 4.5vw, 4rem)` | (héritée, 900 importée) | 1.05 | -0.035em |
| H2 de section (`.section-title`) | `clamp(1.55rem, 2.6vw, 2.3rem)` | 700 | 1.15 | -0.025em |
| H2 corps d'article | `clamp(1.5rem, 2.6vw, 2rem)` | (héritée) | 1.2 | -0.02em |
| H3 corps d'article | `1.2rem` | (héritée) | (héritée) | (aucun) |
| Titre de carte | `1.18rem` | 700 | 1.25 | -0.018em |

Couleur de tous les titres : `var(--text-strong)` (#061838).

Bloc de référence pour le titre de section, copy-pasteable :

```css
.section-title {
  font-size: clamp(1.55rem, 2.6vw, 2.3rem);
  font-weight: 700; line-height: 1.15; letter-spacing: -0.025em;
  color: var(--text-strong);
}
@media (max-width: 640px) {
  .section-title { font-size: clamp(1.35rem, 7vw, 1.9rem); }
}
```

H1 du hero home (valeurs effectives : home.css déclare deux règles `.hero-h1`, la seconde écrase la première ; la graisse 900 est en pratique réservée à la page tarifs, H1 et chiffres de prix) :

```css
.hero-h1 {
  font-size: clamp(2rem, 3.2vw, 3rem);
  font-weight: 700;
  line-height: 1.08;
  letter-spacing: -0.032em;
  color: var(--text-strong);
}
@media (max-width: 640px) { .hero-h1 { font-size: clamp(1.86rem, 9vw, 2.28rem); } }
```

Les H2 du corps d'article portent un séparateur supérieur :

```css
.article-content > h2 { border-top: 1px solid var(--line-1); padding-top: 2.2rem; }
.article-content > h2:first-child { border-top: 0; padding-top: 0; }
.article-content h2 { margin: 3rem 0 1.1rem; }
.article-content h3 { margin: 1.9rem 0 0.75rem; }
```

#### Corps de texte

| Rôle | Taille | line-height | Couleur |
|---|---|---|---|
| Paragraphe éditorial (article, `p` et `li`) | `1.06rem` | 1.75 | `var(--ink-dim)` (= `--text-2`) |
| Standfirst / chapô d'article | `1.06rem` | 1.75 | `var(--ink-dim)` |
| Sous-titre hero | `1.08rem` (weight 400) | 1.6 | texte secondaire |
| Sous-titre de section (`.section-sub`) | `0.95rem` | 1.75 | `var(--text-2)`, `max-width: 560px`, `margin-top: 0.875rem` |
| Texte de carte | `0.92rem` | 1.7 | `var(--ink-dim)` |
| Mobile (article) | `0.98rem` | 1.72 | idem |
| Mobile (`.section-sub`) | `0.92rem` | idem | idem |

Rythme des paragraphes d'article : `p + p { margin-top: 1rem; }`, `li + li { margin-top: 0.55rem; }`, listes avec `padding-left: 1.25rem`.

#### Eyebrows / kickers

Trois variantes, toutes en uppercase avec un trait décoratif `::before` de 2px de haut :

```css
/* Eyebrow de section (la plus courante) */
.section-eyebrow {
  font-size: 0.7rem; font-weight: 600; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--accent-deep); margin-bottom: 0.75rem;
  display: flex; align-items: center; gap: 8px;
}
.section-eyebrow::before {
  content: ''; width: 22px; height: 2px;
  background: linear-gradient(90deg, var(--accent), transparent);
  display: inline-block;
}
@media (max-width: 640px) {
  .section-eyebrow { font-size: 0.66rem; letter-spacing: 0.14em; }
}
```

- Eyebrow de hero : `font-size: 0.72rem; font-weight: 600; letter-spacing: 0.18em; text-transform: uppercase;` en capsule (fond `var(--accent-a-08)`, bordure `1px solid var(--accent-a-22)`, `padding: 6px 14px`, `border-radius: 100px`, trait `::before` masqué), `margin-bottom: 1.2rem`.
- Tag d'article : `font-size: 0.72rem; font-weight: 800; letter-spacing: 0.16em; text-transform: uppercase;` avec `::before` `22px × 2px` en `linear-gradient(90deg, var(--article-hue), transparent)`.

#### Petits textes UI

| Rôle | Valeurs |
|---|---|
| Lien navbar | `0.82rem`, weight 500 |
| CTA navbar | `0.78rem`, weight 700, letter-spacing `0.04em` |
| Boutons (`.btn-primary` etc.) | `0.85rem`, weight 700, letter-spacing `0.03em` |
| Lien footer | `0.85rem` |
| Titre de colonne footer | `0.72rem`, weight 700, letter-spacing `0.12em`, uppercase |
| Copyright / mentions footer | `0.78rem`, couleur `var(--text-3)` |
| Label de formulaire | `0.7rem`, weight 700, letter-spacing `0.08em`, uppercase |
| Badge / pill de catégorie | `0.65rem`, weight 700, letter-spacing `0.08em`, uppercase |
| Date / méta | `0.72rem`, couleur muted, letter-spacing `0.04em` |
| Breadcrumb article | `0.78rem` |
| Méta article (auteur, durée) | `0.85rem`, `strong` en weight 700 |

Règle d'usage : tout micro-texte structurel (label, badge, kicker, titre de colonne) est en uppercase + weight 600 à 800 + letter-spacing positif (0.08em à 0.18em). Le letter-spacing positif est réservé à ces petits textes, jamais aux titres ni aux paragraphes.

### 3. Conteneurs et grilles

Conteneur standard (sections, navbar, footer) :

```css
.section-inner { max-width: 1200px; margin: 0 auto; padding: 0 2rem; }
```

Largeurs max par contexte :

| Contexte | max-width | Padding latéral |
|---|---|---|
| Sections, navbar, footer | `1200px` | `0 2rem` |
| Hero home (`.hero-inner`) | `1400px` | `1.5rem 2rem` |
| Pages article (`.article-wrap`, `.article-layout`) | `1020px` | `0 2rem` |
| Section CTA contact | `1100px` | `0 2rem` |
| Carte partenaires | `980px` | (interne `3rem 3rem`) |
| Bloc texte centré (enjeu) | `880px` | `0 2rem` |
| Colonne de texte hero | `580px` (levé à `none` quand la grille personas est présente) | (interne) |
| Sous-titre de section | `560px` | (interne) |
| Colonne de lecture article | `68ch` | (interne) |

Padding latéral mobile (appliqué en `!important` sur tous les conteneurs) :

```css
@media (max-width: 640px) {
  .section-inner, .footer-inner, .article-wrap, .article-layout, .legal-wrap {
    padding-left: 1.15rem !important;
    padding-right: 1.15rem !important;
  }
}
@media (max-width: 380px) {
  .section-inner, .footer-inner, .article-wrap, .article-layout, .legal-wrap {
    padding-left: 1rem !important;
    padding-right: 1rem !important;
  }
}
```

Grilles types :

- Hero home : `display: grid; align-items: center;` avec, en valeurs effectives, `grid-template-columns: 1fr 540px; gap: 2rem` (règle `body:has(.cas-mini-grid--rich) .hero-inner` ; base surchargée : `1.2fr 0.8fr`, `gap: 4rem`)
- Layout article (contenu + aside) : `grid-template-columns: minmax(0, 1fr) 260px; gap: 3.25rem; align-items: start;` qui passe en `1fr` sous 960px.
- Footer : `grid-template-columns: 1.4fr 1fr 1fr 1fr; gap: 3rem;` puis `1fr 1fr` (gap `2.5rem`) sous 900px, puis `1fr` (gap `2rem`) sous 540px.
- Gouttières de cartes : généralement `gap` autour de `1.5rem` à `3rem` selon la densité; padding interne de carte typique `2.25rem 1.75rem 1.75rem` (cartes riches) ou `1.5rem` (cartes compactes).

Hauteur navbar : `68px` (desktop), `62px` (mobile sous 640px). Compensation d'ancres : `:target { scroll-margin-top: 80px; }` (72px sous 640px).

### 4. Breakpoints

Tous en `max-width` (approche desktop-first). Valeurs rencontrées dans le projet, par fréquence :

- **900px** (12 occurrences) : passage des grilles multi-colonnes en 1 colonne (cas d'usage, ressources, CTA, footer 2 colonnes).
- **980px** (8) : **bascule navbar en hamburger** (`.nav-links` masqué, `#hbg` affiché), réorganisation du hero.
- **640px** (6) : **baseline mobile globale** (body 15px, sections 3.5rem, paddings 1.15rem, navbar 62px).
- **560px** (4), **820px** (3), **720px** (3), **620px** (3), **540px** (3) : ajustements de grilles secondaires.
- **1180px** (2), **860px** (3), **760px** (2), **600px** (2), **480px** (2) : ajustements ponctuels.
- **1100px, 1040px, 1000px, 960px, 920px, 800px, 700px, 680px, 420px, 380px** (1 chacun) : cas spécifiques (960px = layout article 1 colonne, 380px = très petits écrans).

Pour un nouveau projet, retenir les quatre structurants : **1180px** (resserrage desktop), **980px** (hamburger), **900px** (grilles 1 colonne), **640px** (baseline mobile), plus **380px** en filet de sécurité.

Toujours prévoir le respect de `prefers-reduced-motion: reduce` (présent dans global.css et les pages : animations et reveals désactivés).

### 5. Rythme vertical

```css
.section { padding: 5rem 0; position: relative; }
@media (max-width: 640px) {
  .section { padding: 3.5rem 0; }
}
```

Variantes observées :

| Bloc | Padding vertical |
|---|---|
| Section standard | `5rem 0` (mobile : `3.5rem 0`) |
| Section différenciation (fond contrasté) | `6rem 0` |
| Bande logos / trust | `4rem 0` |
| Footer | `4rem 0 1.5rem` (mobile : padding-top `3rem`) |
| Hero home | `padding: 118px 0 2rem` (compense la navbar ; `min-height: 0`, le hero n'occupe pas tout l'écran) |
| Hero article | `145px 0 0` (mobile : padding-top `116px`) |
| Corps d'article | `4rem 0 5.5rem` (mobile : `3rem 0 4rem`) |
| En-tête de section avant grille | `margin-bottom: 2.75rem` |
| Couverture d'article | `margin-top: 3rem`, hauteur `min(46vw, 460px)`, min `250px` |

Intention : les sections respirent largement (5rem est la norme, jamais moins de 3.5rem en mobile), les héros compensent la navbar fixe avec un padding-top en pixels (118px sur la home, 145px sur les articles), et la hiérarchie interne d'une section suit toujours le même ordre vertical : eyebrow (margin-bottom 0.75rem), titre, sous-titre (margin-top 0.875rem), puis contenu après 2.75rem environ.

---

## 3. Chrome : navbar, footer, bandeaux

Le chrome (navbar, footer, bandeaux) est défini dans `assets/css/global.css` et partagé par toutes les pages. Il repose sur les tokens sémantiques du `:root` (voir section tokens), avec un sous-ensemble dédié :

```css
/* ── 7. Chrome (navbar, band, mob-menu, logo) ── */
--navbar-bg:        rgba(234, 240, 248, 0.85);
--navbar-bg-scroll: rgba(234, 240, 248, 0.96);
--band-bg:          rgba(6, 24, 56, 0.97);
--band-text:        rgba(255, 255, 255, 0.94);
--band-text-strong: #FFFFFF;
--band-text-dim:    rgba(255, 255, 255, 0.74);
--mob-menu-bg:      rgba(234, 240, 248, 0.98);
--logo-filter:      none;
```

### 1. Navbar (verre dépoli, fixe)

**Intention** : barre fixe en haut de page, effet « glass » clair (fond ivoire bleuté semi-transparent + blur), qui se densifie au scroll. Un seul CTA à droite (« Parler à un expert »), liens centraux vers les 4 pages personas + Publications + Tarifs.

**Structure HTML type** (copiée de `index.html`) :

```html
<nav id="navbar">
  <div class="nav-inner">
    <a href="/" class="nav-logo" aria-label="Novances Évaluation, accueil">
      <img class="nav-logo-mark" src="/assets/img/brand/logo-novances-evaluation.png" alt="Novances Évaluation" />
    </a>
    <div class="nav-links">
      <a href="/entrepreneurs/" class="nav-link">Entrepreneurs</a>
      <a href="/experts-comptables/" class="nav-link">Experts-comptables</a>
      <a href="/avocats/" class="nav-link">Avocats</a>
      <a href="/notaires/" class="nav-link">Notaires</a>
      <a href="/ressources/" class="nav-link">Publications</a>
      <a href="/tarifs/" class="nav-link">Tarifs</a>
    </div>
    <div class="nav-cta-wrap">
      <a href="#contact" class="nav-cta">
        Parler à un expert
        <svg aria-hidden="true" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
      </a>
    </div>
    <button id="hbg" aria-label="Menu" aria-expanded="false">
      <span id="b1"></span><span id="b2"></span><span id="b3"></span>
    </button>
  </div>
</nav>
<div id="mob-menu">
  <a href="/entrepreneurs/">Entrepreneurs</a>
  <a href="/experts-comptables/">Experts-comptables</a>
  <a href="/avocats/">Avocats</a>
  <a href="/notaires/">Notaires</a>
  <a href="/ressources/">Publications</a>
  <a href="/tarifs/">Tarifs</a>
  <a href="#contact" class="nav-cta">Parler à un expert</a>
</div>
```

**Caractéristiques clés** :
- Hauteur : `68px` desktop, `62px` sous 640px. Logo `height: 32px` (28px mobile).
- Fond : `var(--navbar-bg)` = `rgba(234, 240, 248, 0.85)` avec `backdrop-filter: blur(24px) saturate(140%)`. Bordure basse `1px solid var(--border)` (= `--line-2`).
- État scrollé : classe `.scrolled` ajoutée par JS quand `window.scrollY > 40`. Fond passe à `rgba(234, 240, 248, 0.96)` + ombre `0 8px 32px -12px rgba(0, 0, 0, 0.6)`. Transition `box-shadow 0.3s ease, background 0.3s ease`.
- Liens : `0.82rem`, `font-weight: 500`, couleur `var(--text-2)`. Hover et état actif : couleur `var(--text-strong)` + soulignement `2px` couleur `var(--accent)` (apparition par `opacity`, `transition: opacity 0.2s`). Détail signature : au survol, le soulignement prend la couleur persona de la page de destination (`--p-entrepreneur`, `--p-ec`, `--p-avocat`, `--p-notaire`). Le lien actif ajoute un glow `box-shadow: 0 0 8px var(--accent-a-30)`.
- CTA navbar (`.nav-cta`) : fond `var(--accent-deeper)` (#0369A1), texte blanc `0.78rem` `font-weight: 700` `letter-spacing: 0.04em`, `border-radius: 8px`, padding `10px 22px`, liseré `box-shadow: 0 0 0 1px var(--accent-bright)` + glow. Hover : fond `var(--accent-ink)` (#075985) + `translateY(-1px)`.
- Mobile (breakpoint `980px`) : les `.nav-links` et `.nav-cta-wrap` disparaissent, le burger `#hbg` (3 barres de `22px × 1.5px`, couleur `var(--text-1)`, gap `5px`) s'affiche. Le menu `#mob-menu` est un overlay plein écran sous la navbar (`inset: 0; top: 68px`, `62px` sous 640px), fond `rgba(234, 240, 248, 0.98)` + `blur(20px)`, liens empilés `1.05rem` `font-weight: 500` couleur `var(--text-1)`, hover `var(--accent-bright)`.
- Compensation d'ancres : `:target { scroll-margin-top: 80px; }` (72px sous 640px). Le JS de scroll doux applique un offset de `-118px`.

**JS de comportement** (extrait exact de `assets/js/site.js`, à reproduire) :

```js
const navbar = document.getElementById('navbar');
if (navbar) {
  const updateNavbar = () => navbar.classList.toggle('scrolled', window.scrollY > 40);
  updateNavbar();
  window.addEventListener('scroll', updateNavbar, { passive: true });
}

let navOpen = false;
const hbg = document.getElementById('hbg');
const mob = document.getElementById('mob-menu');
const bars = ['b1', 'b2', 'b3'].map((id) => document.getElementById(id));

const setNavOpen = (open) => {
  navOpen = open;
  mob?.classList.toggle('open', navOpen);
  hbg?.setAttribute('aria-expanded', String(navOpen));

  if (bars[0]) bars[0].style.transform = navOpen ? 'translateY(6.5px) rotate(45deg)' : '';
  if (bars[1]) bars[1].style.opacity = navOpen ? '0' : '';
  if (bars[2]) bars[2].style.transform = navOpen ? 'translateY(-6.5px) rotate(-45deg)' : '';
};

window.closeNav = () => setNavOpen(false);

hbg?.addEventListener('click', () => setNavOpen(!navOpen));
mob?.querySelectorAll('a').forEach((link) => link.addEventListener('click', window.closeNav));
```

**CSS navbar complet** (copié de `global.css`) :

```css
/* ─────────── NAVBAR (glass) ─────────── */
#navbar {
  position: fixed; top: 0; left: 0; right: 0; z-index: 200;
  background: var(--navbar-bg, rgba(5, 13, 29, 0.7));
  backdrop-filter: blur(24px) saturate(140%);
  -webkit-backdrop-filter: blur(24px) saturate(140%);
  border-bottom: 1px solid var(--border);
  transition: box-shadow 0.3s ease, background 0.3s ease;
}
#navbar.scrolled {
  background: var(--navbar-bg-scroll, rgba(5, 13, 29, 0.88));
  box-shadow: 0 8px 32px -12px rgba(0, 0, 0, 0.6);
}

.nav-inner {
  max-width: 1200px; margin: 0 auto; padding: 0 2rem;
  display: flex; align-items: center; justify-content: space-between;
  height: 68px;
}
.nav-logo {
  flex-shrink: 0;
  display: inline-flex; flex-direction: column; align-items: flex-start;
  gap: 3px; text-decoration: none; line-height: 1;
}
.nav-logo-mark { height: 32px; width: auto; display: block; filter: var(--logo-filter, none); }

.nav-links { display: flex; align-items: center; gap: 1.5rem; }
.nav-link {
  font-size: 0.82rem; font-weight: 500;
  color: var(--text-2); text-decoration: none;
  white-space: nowrap;
  transition: color 0.2s;
  position: relative;
  padding: 6px 0;
}
.nav-link:hover, .nav-link.active { color: var(--text-strong); }
.nav-link::after {
  content: ''; position: absolute; bottom: -2px; left: 0; right: 0;
  height: 2px; background: var(--accent);
  border-radius: 2px;
  opacity: 0;
  transition: opacity 0.2s;
}
.nav-link:hover::after { opacity: 1; }
/* Au survol, le soulignement prend la couleur de la page de destination (= sa couleur une fois active). */
.nav-link[href="/entrepreneurs/"]:hover::after      { background: var(--p-entrepreneur); }
.nav-link[href="/experts-comptables/"]:hover::after { background: var(--p-ec); }
.nav-link[href="/avocats/"]:hover::after            { background: var(--p-avocat); }
.nav-link[href="/notaires/"]:hover::after           { background: var(--p-notaire); }
.nav-link.active::after {
  opacity: 1;
  box-shadow: 0 0 8px var(--accent-a-30);
}

.nav-cta {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 10px 22px; background: var(--accent-deeper); color: var(--text-on-accent);
  font-size: 0.78rem; font-weight: 700; letter-spacing: 0.04em;
  text-decoration: none; border-radius: 8px;
  transition: background 0.2s, transform 0.15s, box-shadow 0.2s;
  white-space: nowrap;
  box-shadow: 0 0 0 1px var(--accent-bright), 0 6px 24px -6px var(--accent-a-30);
}
.nav-cta:hover {
  background: var(--accent-ink);
  transform: translateY(-1px);
  box-shadow: 0 0 0 1px var(--accent-bright), 0 10px 32px -6px var(--accent-a-30);
}

/* Hamburger */
#hbg { display: none; flex-direction: column; gap: 5px; background: none; border: none; cursor: pointer; padding: 4px; }
#hbg span { display: block; width: 22px; height: 1.5px; background: var(--text-1); transition: transform 0.3s, opacity 0.3s; }

#mob-menu {
  display: none; position: fixed; inset: 0; top: 68px;
  background: var(--mob-menu-bg, rgba(5, 13, 29, 0.97));
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  z-index: 199;
  flex-direction: column; align-items: center; justify-content: flex-start; gap: 1.2rem;
  padding: 1.5rem 1rem 2rem;
  border-top: 1px solid var(--border);
}
#mob-menu.open { display: flex; }
#mob-menu a { font-size: 1.05rem; font-weight: 500; color: var(--text-1); text-decoration: none; }
#mob-menu a:hover { color: var(--accent-bright); }

@media (max-width: 980px) {
  #hbg { display: flex; }
  .nav-links, .nav-cta-wrap { display: none !important; }
}

/* Compense la hauteur navbar pour les ancres */
:target { scroll-margin-top: 80px; }
```

Ajustements mobile (extrait du bloc `@media (max-width: 640px)` de `global.css`) :

```css
@media (max-width: 640px) {
  .nav-inner { height: 62px; padding: 0 1rem; }
  .nav-logo-mark { height: 28px; }
  #mob-menu { top: 62px; gap: 1.1rem; padding: 1.5rem 1rem 2rem; overflow-y: auto; }
  #mob-menu a { width: min(320px, 100%); max-width: 100%; text-align: center; font-size: 1rem; }
  #mob-menu .nav-cta { justify-content: center; }
  :target { scroll-margin-top: 72px; }
}
```

### 2. Footer

**Intention** : pied de page clair (pas de footer sombre), dans le prolongement du fond de page : dégradé vertical de l'ivoire bleuté (`--bg-base` #EAF0F8) vers le niveau bas (`--bg-deep` #D6DFEC), avec un halo radial d'accent très discret en haut. Quatre colonnes : marque + baseline + affiliation, puis trois colonnes de liens. Barre basse : copyright à gauche, liens légaux à droite.

**Structure HTML type** (copiée de `index.html`) :

```html
<footer class="footer">
  <div class="footer-inner">
    <div class="footer-top">
      <div class="footer-brand">
        <img src="/assets/img/brand/logo-novances-evaluation.png" alt="Novances Évaluation" loading="lazy" />
        <p class="footer-brand-tag">Cabinet d'évaluation d'entreprise pour les dirigeants de PME en préparation de transmission.</p>
        <div class="footer-novances"><img src="/assets/img/brand/Moore_Global.svg.png" alt="Moore Global" loading="lazy" /><span>Réseau international <strong>Moore Global</strong></span></div>
      </div>
      <div>
        <div class="footer-col-title">Pour qui ?</div>
        <div class="footer-links">
          <a href="/entrepreneurs/" class="footer-link">Entrepreneurs</a>
          <a href="/experts-comptables/" class="footer-link">Experts-comptables</a>
          <a href="/avocats/" class="footer-link">Avocats</a>
          <a href="/notaires/" class="footer-link">Notaires</a>
        </div>
      </div>
      <div>
        <div class="footer-col-title">Cabinet</div>
        <div class="footer-links">
          <a href="/equipe/" class="footer-link">L'équipe</a>
          <a href="/equipe/#novances" class="footer-link">Groupe Novances</a>
          <a href="/partenaires/" class="footer-link">Partenaires</a>
          <a href="/tarifs/" class="footer-link">Tarifs</a>
        </div>
      </div>
      <div>
        <div class="footer-col-title">Publications</div>
        <div class="footer-links">
          <a href="/ressources/" class="footer-link">Publications</a>
          <a href="#contact" class="footer-link">Contact</a>
          <a href="#contact" class="footer-link">Formulaire de contact</a>
        </div>
      </div>
    </div>
    <div class="footer-bottom">
      <div class="footer-copy">© 2026 Novances Évaluation, Tous droits réservés.</div>
      <div class="footer-legal">
        <a href="/mentions-legales/">Mentions légales</a>
        <a href="/confidentialite/">Confidentialité</a>
      </div>
    </div>
  </div>
</footer>
```

**Caractéristiques clés** :
- Grille : `grid-template-columns: 1.4fr 1fr 1fr 1fr; gap: 3rem` (la colonne marque est plus large). Passe à `1fr 1fr` sous 900px, `1fr` sous 540px.
- Logos : logo marque `height: 28px`, logo affiliation `height: 22px` avec `opacity: 0.9`. Les deux passent par `filter: var(--logo-filter, ...)` (token à `none` en palette claire).
- Titres de colonnes : `0.72rem`, `font-weight: 700`, `letter-spacing: 0.12em`, `text-transform: uppercase`, couleur `var(--text-strong)`.
- Liens : `0.85rem`, couleur `var(--text-2)`, hover `var(--accent-bright)` (transition `color 0.2s`).
- Bloc affiliation (`.footer-novances`) : micro-typographie capitale (`0.72rem`, `letter-spacing: 0.05em`, uppercase, `var(--text-3)`), séparé de la baseline par une bordure `1px solid var(--line-2)`.
- Barre basse : copyright et liens légaux en `0.78rem` couleur `var(--text-3)`.

**CSS footer complet** (copié de `global.css`) :

```css
/* ─────────── FOOTER (glass) ─────────── */
.footer {
  background: linear-gradient(180deg, var(--bg-base) 0%, var(--bg-deep) 100%);
  color: var(--text-2);
  padding: 4rem 0 1.5rem;
  margin-top: 0;
  border-top: 1px solid var(--line-2);
  position: relative;
}
.footer::before {
  content: '';
  position: absolute; inset: 0;
  background: radial-gradient(1200px 400px at 50% 0%, var(--accent-a-04) 0%, transparent 60%);
  pointer-events: none;
}
.footer > * { position: relative; }
.footer-inner { max-width: 1200px; margin: 0 auto; padding: 0 2rem; }

.footer-top {
  display: grid; grid-template-columns: 1.4fr 1fr 1fr 1fr; gap: 3rem;
  padding-bottom: 3rem; border-bottom: 1px solid var(--line-3);
}
@media (max-width: 900px) { .footer-top { grid-template-columns: 1fr 1fr; gap: 2.5rem; } }
@media (max-width: 540px) { .footer-top { grid-template-columns: 1fr; gap: 2rem; } }

.footer-brand img { height: 28px; filter: var(--logo-filter, brightness(0) invert(1)); margin-bottom: 1rem; }
.footer-brand-tag {
  font-size: 0.85rem; line-height: 1.7; color: var(--text-2);
  max-width: 320px;
}
/* Affiliation Moore Global (sous le séparateur porté par le bas de .footer-brand-tag). */
.footer-brand-tag { padding-bottom: 1.25rem; border-bottom: 1px solid var(--line-2); }
.footer-novances {
  margin-top: 1.25rem;
  display: inline-flex; flex-direction: column; align-items: flex-start;
  width: 100%; gap: 8px;
  font-size: 0.72rem; letter-spacing: 0.05em; text-transform: uppercase;
  color: var(--text-3);
}
.footer-novances strong { color: var(--text-strong); font-weight: 600; }
.footer-novances img {
  height: 22px; width: auto; display: block;
  filter: var(--logo-filter, brightness(0) invert(1));
  opacity: 0.9; margin-bottom: 0;
}

.footer-col-title {
  font-size: 0.72rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--text-strong); margin-bottom: 1rem;
}
.footer-links { display: flex; flex-direction: column; gap: 0.625rem; }
.footer-link {
  font-size: 0.85rem; color: var(--text-2); text-decoration: none;
  transition: color 0.2s;
}
.footer-link:hover { color: var(--accent-bright); }

.footer-bottom {
  margin-top: 2rem;
  display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;
}
.footer-copy { font-size: 0.78rem; color: var(--text-3); }
.footer-legal { display: flex; gap: 1.25rem; }
.footer-legal a { font-size: 0.78rem; color: var(--text-3); text-decoration: none; }
.footer-legal a:hover { color: var(--accent-bright); }
```

Ajustements mobile (extrait du bloc `@media (max-width: 640px)`) :

```css
@media (max-width: 640px) {
  .footer { padding-top: 3rem; }
  .footer-bottom { flex-direction: column; align-items: flex-start; }
  .footer-legal { flex-wrap: wrap; gap: 0.85rem; }
}
```

### 3. Bandeaux et CTA récurrents

Trois mécanismes distincts, à ne pas confondre :

**a. Tokens « band » (bandeau sombre, réservés)**. Le `:root` définit des tokens chrome pour un bandeau sombre sur fond clair : `--band-bg: rgba(6, 24, 56, 0.97)` (navy quasi opaque), `--band-text: rgba(255, 255, 255, 0.94)`, `--band-text-strong: #FFFFFF`, `--band-text-dim: rgba(255, 255, 255, 0.74)`. Ils constituent la recette officielle de tout bandeau sombre : fond navy à 97 pour cent d'opacité, texte blanc à trois niveaux de hiérarchie (strong, normal, dim). Au moment du relevé, aucune règle CSS de production ne les consomme : si vous créez un bandeau sombre, utilisez ces tokens, n'inventez pas d'autres valeurs.

**b. Bandeau réassurance `.novances-band` (clair, pages personas)**. Bandeau récurrent sur 3 des 4 pages cibles (entrepreneurs, avocats, notaires ; absent de experts-comptables), défini dans `assets/css/pages/parcours.css`. C'est une `<section class="section novances-band">` standard (donc `padding: 5rem 0`, conteneur `.section-inner` à 1200px). Fond : surface élevée teintée par la couleur persona de la page :

```css
.novances-band {
  background:
    radial-gradient(900px 520px at 50% 0%, rgba(var(--persona-rgb) / 0.06), transparent 65%),
    var(--bg-elevated);
}
```

Composition en deux colonnes (`grid-template-columns: minmax(0, 1fr) minmax(0, 1.05fr); gap: 2.5rem 3rem`) : texte éditorial à gauche (eyebrow + titre + 2 paragraphes + logo groupe `height: 38px` + lien externe), grille de 5 cartes statistiques à droite (cartes `var(--card-bg)`, bordure `var(--line-2)`, `border-radius: 14px`, filet supérieur de `3px` en dégradé persona, chiffre en `font-weight: 800` couleur persona). Usage : bloc de réassurance institutionnelle, placé en fin de page, avant la FAQ et le CTA final, jamais comme CTA.

**c. Bloc CTA final + formulaire (`.cta-section`, page d'accueil, `assets/css/pages/home.css`)**. Section `id="contact"` qui sert de cible à tous les liens `#contact` du site (navbar, footer, boutons). Fond `var(--navy-deep)` : attention, c'est un alias legacy qui pointe sur `--bg-base` (#EAF0F8), le bloc est donc clair dans la palette actuelle malgré son commentaire « dark » d'origine. Padding `5rem 0`, halo décoratif en `::before` :

```css
.cta-section {
  background: var(--navy-deep);
  padding: 5rem 0;
  position: relative;
  overflow: hidden;
}
.cta-section::before {
  content: '';
  position: absolute; inset: 0;
  background:
    radial-gradient(700px 400px at 20% 30%, var(--accent-a-08), transparent 60%),
    radial-gradient(600px 400px at 90% 80%, rgba(83, 46, 251, 0.06), transparent 60%);
  pointer-events: none;
}
.cta-inner {
  max-width: 1100px; margin: 0 auto; padding: 0 2rem;
  display: grid; grid-template-columns: 0.9fr 1.1fr; gap: 4rem; align-items: start;
  position: relative;
}
@media (max-width: 900px) { .cta-inner { grid-template-columns: 1fr; gap: 2.5rem; } }
```

**Règle d'usage générale des halos de fond** : le chrome utilise systématiquement des radial-gradients très dilués (tokens `--accent-a-04` à `--accent-a-08` d'accent cyan (alphas réels 0.06 à 0.11), 0.06 de violet) posés en `::before` avec `pointer-events: none`, jamais de couleur pleine. Le `body` lui-même porte un double halo fixe (`--accent-a-06` en haut à gauche, `--violet-tint` en bas à droite), ce qui donne la profondeur d'ensemble du site.

---

## 4. Boutons et formulaires

Cette section décrit tous les composants interactifs du site : les variantes de boutons, le formulaire de contact et la checkbox personnalisée. Les valeurs sont copiées exactement des sources (`assets/css/global.css`, `assets/css/pages/home.css`, `assets/css/pages/tarifs.css`, `assets/js/site.js`, `assets/js/pages/home.js`).

### Tokens requis

Les composants ci-dessous consomment ces variables CSS (à définir dans `:root`) :

```css
:root {
  --text-strong:  #061838;                 /* titres, valeurs fortes */
  --text-1:       #182747;                 /* texte courant (boutons outline/ghost) */
  --text-2:       #3A4A6B;                 /* labels secondaires */
  --text-3:       #586A8A;                 /* placeholders, notes */
  --text-on-accent: #FFFFFF;               /* texte sur fond accent */

  --accent:        #0EA5E9;                /* focus ring des champs, checkbox cochée */
  --accent-bright: #38BDF8;                /* anneau lumineux des CTA, hover ghost */
  --accent-deep:   #0284C7;                /* outline focus clavier */
  --accent-deeper: #0369A1;                /* fond des CTA (contraste AA sur blanc) */
  --accent-ink:    #075985;                /* fond des CTA au hover */
  --accent-a-15: rgba(14, 165, 233, 0.19); /* halo focus des champs */
  --accent-a-22: rgba(14, 165, 233, 0.26); /* ombre de la carte formulaire */
  --accent-a-30: rgba(14, 165, 233, 0.35); /* glow des CTA */

  --surface-low:   rgba(15, 23, 42, 0.035);
  --surface-mid:   rgba(15, 23, 42, 0.06);
  --line-1: rgba(15, 23, 42, 0.07);
  --line-2: rgba(15, 23, 42, 0.13);
  --line-3: rgba(15, 23, 42, 0.20);
  --line-4: rgba(15, 23, 42, 0.28);

  --card-bg-strong: linear-gradient(160deg, #FFFFFF 0%, #E2EAF5 100%);
  --muted: var(--text-3); /* alias legacy utilisé par .form-note */
}
```

### 1. Boutons

Trois variantes partagent une base commune, plus un CTA spécifique à la navbar. Logique d'usage :

- `.btn-primary` : action principale (une seule par écran idéalement), fond bleu marine profond avec anneau lumineux. Sert aussi de bouton submit du formulaire.
- `.btn-outline` : action secondaire (lien « Voir toutes les publications », second bouton du hero). Surface quasi transparente, bordure fine.
- `.btn-ghost` : lien d'action discret sans fond ni bordure, avec flèche qui glisse au hover. Défini dans le système mais pas utilisé dans les pages de production actuelles.
- `.nav-cta` : CTA de la navbar, version compacte du primaire (padding et taille de police réduits).

```css
/* Base commune aux trois variantes */
.btn-primary, .btn-outline, .btn-ghost {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 13px 26px;
  font-size: 0.85rem; font-weight: 700; letter-spacing: 0.03em;
  text-decoration: none; border-radius: 8px;
  transition: background 0.2s, transform 0.15s, border-color 0.2s, color 0.2s, box-shadow 0.2s;
  cursor: pointer; border: none; font-family: inherit; white-space: nowrap;
}

/* Variante primaire */
.btn-primary {
  background: var(--accent-deeper); color: var(--text-on-accent);
  box-shadow: 0 0 0 1px var(--accent-bright), 0 8px 28px -8px var(--accent-a-30);
}
.btn-primary:hover {
  background: var(--accent-ink);
  transform: translateY(-1px);
  box-shadow: 0 0 0 1px var(--accent-bright), 0 12px 36px -8px var(--accent-a-30);
}

/* Variante outline */
.btn-outline {
  background: var(--surface-low);
  color: var(--text-1);
  border: 1px solid var(--line-2);
}
.btn-outline:hover {
  background: var(--surface-mid);
  border-color: var(--line-3);
  color: var(--text-strong);
}

/* Variante ghost */
.btn-ghost { background: transparent; color: var(--text-1); padding: 10px 0; }
.btn-ghost:hover { color: var(--accent-bright); }
.btn-ghost svg { transition: transform 0.2s; }
.btn-ghost:hover svg { transform: translateX(3px); }

/* CTA navbar (version compacte du primaire) */
.nav-cta {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 10px 22px; background: var(--accent-deeper); color: var(--text-on-accent);
  font-size: 0.78rem; font-weight: 700; letter-spacing: 0.04em;
  text-decoration: none; border-radius: 8px;
  transition: background 0.2s, transform 0.15s, box-shadow 0.2s;
  white-space: nowrap;
  box-shadow: 0 0 0 1px var(--accent-bright), 0 6px 24px -6px var(--accent-a-30);
}
.nav-cta:hover {
  background: var(--accent-ink);
  transform: translateY(-1px);
  box-shadow: 0 0 0 1px var(--accent-bright), 0 10px 32px -6px var(--accent-a-30);
}
```

Signature visuelle du primaire : le `box-shadow` combine un anneau de 1px en `--accent-bright` (plus clair que le fond, effet de liseré lumineux) et une ombre portée diffuse teintée accent. Le hover étend l'ombre (même teinte, géométrie plus diffuse), assombrit le fond et lève le bouton de 1px.

**Focus clavier (accessibilité)**, appliqué globalement :

```css
a:focus-visible, button:focus-visible, summary:focus-visible, [tabindex]:focus-visible,
.nav-cta:focus-visible, .btn-primary:focus-visible, .btn-outline:focus-visible, .btn-ghost:focus-visible, .nav-link:focus-visible {
  outline: 2px solid var(--accent-deep);
  outline-offset: 2px;
  border-radius: 6px;
}
```

**Adaptations mobiles** (les boutons passent en pleine largeur) :

```css
@media (max-width: 640px) {
  .btn-primary, .btn-outline, .btn-ghost, .nav-cta {
    max-width: 100%;
    white-space: normal;
    text-align: center;
    justify-content: center;
  }
  .btn-primary, .btn-outline {
    width: 100%;
    padding: 12px 18px;
  }
  .btn-ghost { width: auto; }
}
@media (max-width: 380px) {
  .btn-primary, .btn-outline {
    font-size: 0.78rem;
    padding: 11px 14px;
  }
}
```

#### Effet magnétique (CTA importants)

Les CTA majeurs (hero, sections de conversion) reçoivent la classe additionnelle `.btn-magnetic` avec un wrapper interne `.btn-content`. Le bouton suit légèrement le curseur, le contenu suit avec un facteur réduit (effet de parallaxe). Désactivé si `prefers-reduced-motion`, si l'appareil n'a pas de hover, ou sous 981px de large.

```css
.btn-magnetic {
  will-change: transform;
  transition: transform 0.3s cubic-bezier(.2,.8,.2,1), background 0.2s;
}
.btn-magnetic .btn-content {
  display: inline-flex; align-items: center; gap: 8px;
  transition: transform 0.3s cubic-bezier(.2,.8,.2,1);
  pointer-events: none;
}
```

```js
if (!reducedMotion && window.matchMedia('(hover: hover) and (min-width: 981px)').matches) {
  document.querySelectorAll('.btn-magnetic').forEach((btn) => {
    const content = btn.querySelector('.btn-content') || btn;

    btn.addEventListener('pointermove', (event) => {
      const rect = btn.getBoundingClientRect();
      const x = event.clientX - rect.left - rect.width / 2;
      const y = event.clientY - rect.top - rect.height / 2;
      btn.style.transform = `translate(${(x * 0.25).toFixed(1)}px, ${(y * 0.4).toFixed(1)}px)`;
      if (content !== btn) {
        content.style.transform = `translate(${(x * 0.12).toFixed(1)}px, ${(y * 0.18).toFixed(1)}px)`;
      }
    });

    btn.addEventListener('pointerleave', () => {
      btn.style.transform = '';
      if (content !== btn) content.style.transform = '';
    });
  });
}
```

#### Markup HTML type

La flèche est un SVG inline (jamais d'icône externe) : 14x14 (13x13 dans la navbar), `stroke="currentColor"`, `stroke-width="2.5"`, path `M5 12h14M12 5l7 7-7 7`.

```html
<!-- Primaire simple -->
<a href="/partenaires/" class="btn-primary">
  Parler à un expert
  <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
</a>

<!-- Primaire magnétique (CTA hero / conversion) : le contenu DOIT être dans .btn-content -->
<a href="/#contact" class="btn-primary btn-magnetic">
  <span class="btn-content">
    Parler à un expert
    <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
  </span>
</a>

<!-- Secondaire -->
<a href="/ressources/" class="btn-outline">Voir toutes les publications</a>

<!-- CTA navbar -->
<a href="#contact" class="nav-cta">
  Parler à un expert
  <svg aria-hidden="true" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
</a>
```

### 2. Formulaire de contact

Le formulaire vit dans une carte (`.form-card`) posée sur le gradient de carte fort, avec une grande ombre teintée accent. Les champs sont blancs sur fond clair, avec un focus ring en halo de 3px. Les labels sont en uppercase miniature au-dessus du champ. Champs sur deux colonnes via `.form-row` (une colonne sous 480px).

```css
.form-card {
  background: var(--card-bg-strong);
  border: 1px solid var(--line-2);
  border-radius: 18px;
  padding: 2rem;
  box-shadow: 0 30px 60px -28px var(--accent-a-22);
}
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
@media (max-width: 480px) { .form-row { grid-template-columns: 1fr; } }
.form-field { margin-bottom: 1rem; }
.form-label {
  display: block; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--text-2); margin-bottom: 6px;
}
.form-input, .form-select, .form-textarea {
  width: 100%; padding: 12px 14px;
  background: #FFFFFF;
  border: 1px solid var(--line-3);
  border-radius: 8px;
  font-family: 'Inter', sans-serif; font-size: 0.875rem; color: var(--text-strong);
  outline: none; transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
}
.form-input::placeholder, .form-textarea::placeholder { color: var(--text-3); }
.form-input:hover, .form-select:hover, .form-textarea:hover {
  border-color: var(--line-4);
}
.form-input:focus, .form-select:focus, .form-textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-a-15);
  background: #FFFFFF;
}
.form-textarea { resize: vertical; min-height: 90px; }
.form-submit {
  width: 100%; justify-content: center; padding: 14px; font-size: 0.9rem; margin-top: 0.5rem;
}
.form-note {
  font-size: 0.74rem; color: var(--muted); margin-top: 0.75rem; text-align: center;
}
.form-error {
  display: none;
  margin-top: 0.75rem;
  font-size: 0.78rem;
  line-height: 1.5;
  color: #FCA5A5;
  text-align: center;
}
#form-success {
  display: none; padding: 2rem;
  background: rgba(34,197,94,0.08);
  border: 1px solid rgba(34,197,94,0.3);
  border-radius: 12px; text-align: center;
  color: var(--text-strong);
}
#form-success svg { display: block; margin: 0 auto 1rem; }

/* Mobile : 16px évite le zoom automatique iOS au focus */
@media (max-width: 640px) {
  .form-card { padding: 1.3rem; }
  .form-input, .form-select, .form-textarea { font-size: 16px; }
}
```

Points d'intention :

- Le bouton submit est un `.btn-primary` étendu par `.form-submit` (pleine largeur, centré).
- Anti-spam : champ honeypot caché `name="website"` positionné hors écran, jamais via `display:none` (les bots le rempliraient quand même, les lecteurs d'écran l'ignorent grâce à `aria-hidden` et `tabindex="-1"`).
- Le message d'erreur (`role="alert"`) et le bloc succès (`role="status"`) sont présents dans le DOM mais masqués (`display: none`), affichés par JS.
- Succès : le formulaire entier est masqué et remplacé par le bloc vert `#form-success` (vert `#22C55E` pour l'icône, fond `rgba(34,197,94,0.08)`, bordure `rgba(34,197,94,0.3)`).

#### Markup HTML complet

```html
<div class="form-card">
  <form id="contact-form" onsubmit="handleForm(event)">
    <input type="text" name="website" tabindex="-1" autocomplete="off" aria-hidden="true" style="position:absolute; left:-9999px; opacity:0;" />
    <div class="form-row">
      <div class="form-field">
        <label class="form-label" for="f-prenom">Prénom *</label>
        <input class="form-input" type="text" id="f-prenom" name="prenom" required placeholder="Jean" />
      </div>
      <div class="form-field">
        <label class="form-label" for="f-nom">Nom *</label>
        <input class="form-input" type="text" id="f-nom" name="nom" required placeholder="Dupont" />
      </div>
    </div>
    <div class="form-row">
      <div class="form-field">
        <label class="form-label" for="f-email">Email *</label>
        <input class="form-input" type="email" id="f-email" name="email" required placeholder="jean.dupont@entreprise.fr" />
      </div>
      <div class="form-field">
        <label class="form-label" for="f-tel">Téléphone</label>
        <input class="form-input" type="tel" id="f-tel" name="telephone" placeholder="06 XX XX XX XX" />
      </div>
    </div>
    <div class="form-field">
      <label class="form-label" for="f-msg">Message</label>
      <textarea class="form-textarea" id="f-msg" name="message" placeholder="Décrivez brièvement votre projet…"></textarea>
    </div>
    <button type="submit" id="f-submit" class="btn-primary form-submit">
      Je souhaite être rappelé
      <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
    </button>
    <p id="form-error" class="form-error" role="alert"></p>
    <p class="form-note">Vos informations restent strictement confidentielles.</p>
  </form>
  <div id="form-success" role="status">
    <svg aria-hidden="true" width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color:#22C55E;"><path d="M 1 4 L 1 1 L 4 1" stroke-width="1"/><path d="M 20 23 L 23 23 L 23 20" stroke-width="1"/><circle cx="12" cy="10" r="5"/><circle cx="12" cy="10" r="1.5" fill="currentColor" stroke="none"/><path d="M 9.5 14.5 L 8 20 L 12 18 L 16 20 L 14.5 14.5"/></svg>
    <div style="font-weight:700; color:#fff; margin-bottom:4px;">Message envoyé.</div>
    <div style="font-size:0.85rem; color:var(--ink-dim);">Un membre de l'équipe NCF vous recontacte sous 24 h ouvrées.</div>
  </div>
</div>
```

#### Comportement JS (états envoi / erreur / succès)

Pendant l'envoi, le bouton est désactivé et son libellé devient « Envoi en cours... ». En cas d'échec, le bouton est restauré et le message d'erreur affiché. En cas de succès, le formulaire est masqué et le bloc succès affiché.

```js
(() => {
  async function handleForm(event) {
    event.preventDefault();

    const form = event.currentTarget;
    const btn = document.getElementById('f-submit');
    const error = document.getElementById('form-error');
    const originalHtml = btn?.innerHTML || '';

    if (error) {
      error.style.display = 'none';
      error.textContent = '';
    }

    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Envoi en cours...';
    }

    try {
      const data = Object.fromEntries(new FormData(form).entries());
      data.page_url = window.location.href;
      data.referrer = document.referrer;

      const response = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (!response.ok) throw new Error('Form submission failed');

      const contactForm = document.getElementById('contact-form');
      const success = document.getElementById('form-success');
      if (contactForm) contactForm.style.display = 'none';
      if (success) success.style.display = 'block';
    } catch {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
      }

      if (error) {
        error.textContent = "L'envoi n'a pas abouti. Vous pouvez réessayer ou appeler le 06 67 10 46 98.";
        error.style.display = 'block';
      }
    }
  }

  window.handleForm = handleForm;
})();
```

### 3. Checkbox personnalisée (simulateur tarifs)

Seul autre contrôle de formulaire du site : une checkbox stylée définie dans tarifs.css pour le configurateur d'options. Attention : la page tarifs publiée affiche des lignes statiques ; ce markup n'est utilisé aujourd'hui que dans le prototype `_work/tarifs-variants/variant-c.html` (bac à sable non déployé). Le pattern reste la référence pour toute future checkbox. L'input natif est masqué, la coche est dessinée dans un carré de 20px qui passe au cyan accent quand coché. Le label entier (ligne en grid 3 colonnes : case, libellé, prix) est cliquable.

```css
.tp-addon-item {
  display: grid;
  grid-template-columns: 24px 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 0.55rem 0;
  border-bottom: 1px dashed var(--line-1);
  cursor: pointer;
  user-select: none;
}
.tp-addon-item:last-child { border-bottom: 0; }
.tp-addon-check {
  width: 20px;
  height: 20px;
  border: 1.5px solid var(--line-3);
  border-radius: 5px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  transition: background 0.2s, border-color 0.2s;
}
.tp-addon-check svg {
  opacity: 0;
  transition: opacity 0.2s;
  width: 12px;
  height: 12px;
  color: #fff;
}
.tp-addon-item input { display: none; }
.tp-addon-item input:checked ~ .tp-addon-check {
  background: var(--accent);
  border-color: var(--accent);
}
.tp-addon-item input:checked ~ .tp-addon-check svg { opacity: 1; }
.tp-addon-label {
  font-size: 0.88rem;
  color: var(--text-1);
  font-weight: 500;
}
.tp-addon-price {
  font-size: 0.88rem;
  font-weight: 700;
  color: var(--text-strong);
  font-variant-numeric: tabular-nums;
}
```

Les prix utilisent `font-variant-numeric: tabular-nums` pour aligner les chiffres en colonne, à reprendre pour tout affichage de montants.

---

## 5. Cards et composants de contenu

Source : `assets/css/pages/home.css`, `assets/css/pages/ressources.css`, `assets/css/pages/tarifs.css`, `assets/css/pages/equipe.css`, `assets/css/pages/partenaires.css`, `assets/css/components/autocycle.css`. Les tokens cités (`--card-bg`, `--line-2`, `--accent`, etc.) sont définis dans le `:root` de `global.css` (voir la section tokens de cette charte).

Principe directeur : au repos, une card est définie par son fond dégradé et sa bordure fine, presque jamais par une ombre. L'élévation (ombre + translateY négatif + bordure qui prend l'accent) est une récompense du survol. Les exceptions qui portent une ombre au repos sont les éléments "posés" sur le fond de page : formulaire de contact, bento équipe, tableau tarifaire, photos de profil, panneau autocycle.

### 1. Inventaire des patterns de cards

#### A. Card offre / cas d'usage (`.cas-card`, page d'accueil)

Le pattern le plus riche du site. C'est une card cliquable en lien, color-codée par persona.

| Propriété | Valeur exacte |
|---|---|
| Fond | `var(--card-bg)` (dégradé `linear-gradient(160deg, #FFFFFF 0%, #ECF1F9 100%)`) |
| Bordure | `1px solid var(--border)` (= `--line-2`, `rgba(15, 23, 42, 0.13)`) |
| Radius | `18px` |
| Padding | `2.25rem 1.75rem 1.75rem` |
| Effet verre | `backdrop-filter: blur(14px)` |
| Transition | `transform 0.35s cubic-bezier(.2,.8,.2,1), box-shadow 0.35s, border-color 0.3s, background 0.3s` |
| Hover | `transform: translateY(-6px)` ; `box-shadow: 0 24px 48px -14px rgba(0, 0, 0, 0.6), 0 0 0 1px var(--cas-accent) inset` ; `border-color: var(--cas-accent)` |

Trois détails signature à reproduire :

1. **Voile dégradé au survol** (`::before`) : `linear-gradient(160deg, var(--cas-soft), transparent 55%)`, `opacity: 0` au repos, `1` au hover, transition `0.35s`.
2. **Barre supérieure qui se dessine** (`::after`) : barre de `3px` en haut, `linear-gradient(90deg, var(--cas-pop), transparent)`, `transform: scaleX(0)` avec `transform-origin: left`, passe à `scaleX(1)` au hover en `0.5s cubic-bezier(.2,.8,.2,1)`.
3. **Icône qui réagit** (`.cas-icon`) : conteneur `52px × 52px`, `border-radius: 12px`, fond teinté (`--cas-pop-soft`), bordure `1px solid color-mix(in srgb, var(--cas-pop) 25%, transparent)` ; au hover de la card : `transform: scale(1.08) rotate(-2deg)` et glow `box-shadow: 0 0 24px color-mix(in srgb, var(--cas-pop) 40%, transparent)`.

Contenu type : numéro `.cas-num` en haut à droite (`0.7rem`, `font-weight: 700`, uppercase, `letter-spacing: 0.12em`, précédé d'un tiret décoratif `18px × 1.5px`), titre `1.18rem / 700 / line-height 1.25 / letter-spacing -0.018em`, corps `0.92rem / line-height 1.7`, lien fléché `0.82rem / 700` dont la flèche fait `translateX(4px)` au hover (`transition: transform 0.3s`).

Color-coding : la card pose `--cas-accent: var(--accent)` partout, et `--cas-pop` varie par persona (`--p-entrepreneur: #2563EB`, `--p-ec: #0EA5E9`, `--p-avocat: #4F46E5`, `--p-notaire: #1E40AF`).

#### B. Card article / publication (`.pub-card` page ressources, `.res-card` teaser accueil)

Card éditoriale avec image en tête, color-codée par thématique via `--pub-hue`.

`.pub-card` (le modèle de référence) :

| Propriété | Valeur exacte |
|---|---|
| Fond | `var(--card-bg)` |
| Bordure | `1px solid var(--line-2)` |
| Radius | `14px`, `overflow: hidden` |
| Image | `aspect-ratio: 16 / 10`, `object-fit: cover` |
| Body | padding `1.35rem 1.5rem 1.5rem`, `flex: 1` en colonne |
| Transition | `transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.25s ease, box-shadow 0.25s ease` |
| Hover | `translateY(-3px)` ; `border-color: color-mix(in srgb, var(--pub-hue) 45%, transparent)` ; `box-shadow: 0 20px 44px -22px color-mix(in srgb, var(--pub-hue) 30%, transparent)` |
| Zoom image hover | `transform: scale(1.04)` en `0.5s cubic-bezier(0.16, 1, 0.3, 1)` |

Hues par thème : `transmission` → `var(--c-succession)` (#F59E0B), `litiges` → `var(--c-litiges)` (#532EFB), `croissance` → `var(--c-croissance)` (#10B981), `fiscalite` → `var(--p-entrepreneur)` (#2563EB). Défaut : `var(--accent)`.

Contenu : tag uppercase coloré (`0.72rem / 800 / letter-spacing 0.12em`), titre `clamp(1.05rem, 1.45vw, 1.25rem) / 600 / line-height 1.3`, extrait `0.93rem / line-height 1.62` tronqué à 3 lignes (`-webkit-line-clamp: 3`), méta date `0.82rem`.

Variante mise en avant `.pub-card--feature` : occupe toute la largeur de la grille (`grid-column: 1 / -1`), passe en 2 colonnes `minmax(0, 1.1fr) minmax(0, 1fr)` (image à gauche, `min-height: 320px`), body `2.5rem 2.75rem`, titre `clamp(1.5rem, 2.6vw, 2.2rem) / 700`, extrait clampé à 4 lignes.

`.res-card` (teaser accueil) : même logique avec fond `var(--card-bg-soft)`, radius `14px`, image `16/9` avec zoom `scale(1.05)` en `0.45s cubic-bezier(.2,.8,.2,1)` et léger traitement (`filter: saturate(0.85) contrast(1.05)` au repos, `saturate(1) contrast(1.08)` au hover), hover `translateY(-4px)` + `box-shadow: 0 20px 40px -16px rgba(0,0,0,0.6)` + `border-color: var(--cyan)`.

#### C. Card tarif (`.tc-card`, page tarifs)

| Propriété | Valeur exacte |
|---|---|
| Fond | `var(--card-bg)` |
| Bordure | `1px solid var(--line-2)` |
| Radius | `16px` |
| Padding | `1.6rem 1.5rem 1.4rem` |
| Transition | `transform 0.3s, box-shadow 0.3s, border-color 0.3s` |
| Hover | `translateY(-4px)` ; `border-color: var(--accent-a-30)` ; `box-shadow: 0 22px 44px -20px var(--accent-a-25)` |

Anatomie interne : tag uppercase (`0.62rem / 800 / letter-spacing 0.16em`, couleur accent), nom du segment (`1.35rem / 800 / letter-spacing -0.022em`), critère séparé par un filet `border-bottom: 1px solid var(--line-1)`, prix en très gras (`2rem / 900 / letter-spacing -0.028em`, couleur `var(--accent)`), liste d'options avec séparateurs `border-bottom: 1px dashed var(--line-1)` et prix en `font-variant-numeric: tabular-nums`, CTA plein accent (`padding: 12px 16px`, `border-radius: 8px`, hover `background: var(--accent-deep)` + `translateY(-1px)`).

Le tableau matriciel `.tarif-matrix` (variante A) porte une ombre au repos : `box-shadow: 0 18px 40px -20px rgba(15, 23, 42, 0.18)`, radius `14px`, en-tête sur fond `var(--accent)` plein avec texte blanc.

#### D. Card membre d'équipe (`.profile-photo`, page équipe)

Portrait vertical cliquable vers LinkedIn :

| Propriété | Valeur exacte |
|---|---|
| Format | `aspect-ratio: 4 / 5`, `overflow: hidden` |
| Radius | `18px` |
| Ombre (au repos) | `0 30px 80px -30px rgba(0, 184, 255, 0.18), 0 1px 0 rgba(255,255,255,0.04) inset` |
| Image | `object-fit: cover; object-position: center top`, `filter: saturate(1.05) contrast(1.02)` |
| Hover image | `transform: scale(1.03)` en `0.6s cubic-bezier(0.16, 1, 0.3, 1)` |
| Scrim bas (`::after`) | `linear-gradient(180deg, transparent 55%, rgba(5, 13, 29, 0.45) 100%)` |

Bandeau LinkedIn (`.profile-photo-linkedin`) : caché par `transform: translateY(100%)`, glisse à `translateY(0)` au hover/focus en `0.4s cubic-bezier(0.16, 1, 0.3, 1)`, fond `linear-gradient(180deg, rgba(10,102,194,0.78) 0%, rgba(10,102,194,0.96) 100%)`, `backdrop-filter: blur(6px)`, padding `0.95rem 1.25rem`. Sur écran tactile (`@media (hover: none)`), le bandeau reste visible en permanence.

Variante compacte : le bento équipe du hero (`.hv-bento-card`) reprend la même logique en grille 3 × 2 (radius `14px`, ombre repos `0 14px 28px -18px rgba(0,0,0,0.45)`, hover `translateY(-3px)` + `border-color: var(--accent-a-30)` + `0 22px 38px -16px rgba(0,0,0,0.55)`, overlay nom/rôle qui remonte de `translateY(40%)` ou `translateY(102%)` selon la taille de la cellule, entrée animée `hv-rise 0.75s cubic-bezier(.2,.8,.2,1)` avec délai par card via `--d`).

#### E. Cards partenaires (`.partner-panel`, `.partner-type-card`, `.workflow-step`, `.standard-card`)

Registre volontairement plus dense et technique : radius réduit à `8px`, pas d'effet hover.

```css
.partner-type-card,
.workflow-step,
.standard-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: rgba(255,255,255,0.035);
  padding: 1.25rem;
}
```

Le panneau principal `.partner-panel` : fond `var(--card-bg)`, padding `1.4rem`, ombre au repos `0 30px 70px -34px rgba(0,0,0,0.75)`. Icône de catégorie `.partner-type-icon` : `38px × 38px`, radius `8px`, fond `rgba(0, 184, 255, 0.1)`, bordure `1px solid rgba(0, 184, 255, 0.22)`.

#### F. Patterns secondaires récurrents

- **Card témoignage** (`.testi-card`) : `var(--card-bg-soft)`, radius `14px`, padding `1.75rem 1.5rem`, `backdrop-filter: blur(14px)`, hover sobre sans ombre : `border-color: var(--border-strong)` + `translateY(-3px)`.
- **Pilier à filet accent** (`.solution-pillar`) : radius `14px`, `border-left: 3px solid var(--cyan)`, hover `translateY(-2px)` + `box-shadow: 0 12px 28px -12px rgba(0,0,0,0.6)`.
- **Bandeau note à filet épais** (`.hero-equipe-note`, `.tarifs-bottom-cta`) : radius `12px`, `border-left: 4px solid var(--accent)`, fond blanc ou `var(--card-bg)`. La note porte `box-shadow: 0 18px 36px -18px rgba(0, 0, 0, 0.22)` au repos, hover `translateY(-2px)` + `0 22px 44px -18px rgba(0, 0, 0, 0.3)`. C'est le pattern pour une mention secondaire reliée à la marque (groupe, renvoi contact).
- **Card formulaire** (`.form-card`) : `var(--card-bg-strong)`, radius `18px`, padding `2rem`, ombre teintée accent au repos : `0 30px 60px -28px var(--accent-a-22)`.
- **Tuile logo défilante** (`.trust-logo`) : hauteur `72px`, padding `12px 20px`, fond `rgba(255, 255, 255, 0.92)`, radius `10px`, `opacity: 0.82` au repos ; hover `opacity: 1`, fond `#fff`, `translateY(-2px)`, `box-shadow: 0 8px 24px -8px rgba(0, 0, 0, 0.5)`.

### 2. Système d'élévation (ombres)

Inventaire des principales `box-shadow` rencontrées dans ces fichiers (non exhaustif : s'y ajoutent quelques variantes locales, par exemple les ombres du médaillon autocycle, le halo du point terminal de la barre de progression et les halos de focus) :

| Valeur | Usage |
|---|---|
| `0 14px 28px -18px rgba(0,0,0,0.45)` | bento équipe, repos |
| `0 18px 40px -20px rgba(15, 23, 42, 0.18)` | tableau tarifaire, repos |
| `0 18px 40px -20px rgba(15, 23, 42, 0.15)` | sélecteur tarif interactif, repos |
| `0 18px 36px -18px rgba(0, 0, 0, 0.22)` | bandeau note, repos |
| `0 18px 36px -18px rgba(6, 24, 56, 0.45)` | portrait CTA |
| `0 8px 24px -8px rgba(0, 0, 0, 0.5)` | tuile logo, hover |
| `0 12px 28px -12px rgba(0,0,0,0.6)` | pilier, hover |
| `0 20px 40px -16px rgba(0,0,0,0.6)` | res-card, hover |
| `0 20px 44px -22px color-mix(in srgb, var(--pub-hue) 30%, transparent)` | pub-card, hover |
| `0 22px 44px -20px var(--accent-a-25)` | tc-card, hover |
| `0 22px 44px -18px rgba(0, 0, 0, 0.3)` | bandeau note, hover |
| `0 22px 38px -16px rgba(0,0,0,0.55)` | bento, hover |
| `0 24px 48px -14px rgba(0, 0, 0, 0.6), 0 0 0 1px var(--cas-accent) inset` | cas-card, hover |
| `0 16px 30px -16px var(--accent-a-40)` / `0 22px 40px -16px var(--accent-a-40)` | tuile brand bento, repos / hover |
| `0 20px 40px -18px rgba(0, 0, 0, 0.5)` | partners-card (teaser accueil), repos |
| `0 30px 60px -28px var(--accent-a-22)` | form-card, repos |
| `0 30px 70px -34px rgba(0,0,0,0.75)` | partner-panel, repos |
| `0 30px 80px -30px rgba(0, 184, 255, 0.18), 0 1px 0 rgba(255,255,255,0.04) inset` | photo profil équipe, repos |
| `0 40px 100px -30px rgba(0, 184, 255, 0.32)` | logo Novances, hover |
| `0 1px 0 rgba(255, 255, 255, .7) inset, 0 24px 60px -32px rgba(6, 24, 56, .35), 0 4px 14px -8px rgba(6, 24, 56, .18)` | panneau autocycle, repos |
| `0 4px 12px -4px var(--accent-a-40)` | pouce de slider |
| `0 0 24px color-mix(in srgb, var(--cas-pop) 40%, transparent)` | glow d'icône, hover |
| `0 0 0 2px var(--line-2)` | anneau avatar témoignage |
| `0 0 0 4px rgba(var(--persona-rgb) / .14)` | halo de dot active (autocycle) |

**Recette commune** : décalage vertical marqué (14 à 30px), flou environ égal à 2 fois le décalage, et surtout un spread fortement négatif (-14 à -34px) qui resserre l'ombre sous la card. Jamais d'ombre ambiante diffuse. La teinte est soit un noir/navy translucide, soit un alpha de l'accent quand la card est liée à un CTA ou à la marque.

**Trois niveaux canoniques** à retenir :

```css
/* Niveau 1 : repos discret (card posée sur le fond) */
box-shadow: 0 18px 40px -20px rgba(15, 23, 42, 0.18);

/* Niveau 2 : hover standard (avec translateY(-3px) à translateY(-4px)) */
box-shadow: 0 22px 44px -20px var(--accent-a-25);

/* Niveau 3 : pièce maîtresse (formulaire, panneau hero) */
box-shadow: 0 30px 60px -28px var(--accent-a-22);
```

### 3. Border-radius : inventaire et convention

Valeurs rencontrées : `999px`, `100px`, `50%`, `28%`, `22px`, `18px`, `16px`, `14px`, `12px`, `10px`, `8px`, `6px`, `5px`, `4px`, `3px`, `2px`.

Convention par usage :

| Radius | Usage |
|---|---|
| `22px` | conteneur composant majeur (panneau autocycle `.tabs`) |
| `18px` | cards "héros" : cas-card, form-card, partners-card, photo profil, logo Novances |
| `16px` | cards de niveau intermédiaire : tc-card, tarif-pick, iframe rapport |
| `14px` | radius par défaut des cards de grille : pub-card, res-card, testi-card, solution-pillar, bento, tarif-matrix, portrait CTA |
| `12px` | sous-blocs et bandeaux : conteneur d'icône de card (cas-icon), notes à filet (`hero-equipe-note`, `tarifs-bottom-cta`), encart résultat, message succès formulaire |
| `10px` | petits conteneurs : tuile logo, chip autocycle, icône de contact |
| `8px` | boutons, inputs, onglets, et les cards denses de la page partenaires |
| `999px` ou `100px` | pills : filtres, tags, eyebrow pill |
| `50%` | cercles (dots, avatars, anneaux) |

Règle simple : plus l'élément est grand et important, plus le radius est grand. `14px` est la valeur de croisière d'une card de grille, `18px` celle d'une card vedette, `8px` celle du registre fonctionnel (boutons, inputs, contenus techniques).

### 4. Composant autocycle (bloc « Pourquoi nous »)

Fichiers : `assets/css/components/autocycle.css` + `assets/js/autocycle.js`. Pattern : un panneau à onglets qui défile automatiquement entre 3 (ou 4) arguments différenciants, avec barre de progression, panneaux en cross-fade et animations d'ambiance continues. La couleur d'accent est héritée de la page via `var(--persona)` et `var(--persona-rgb)` (posées par une classe `body.is-<persona>`).

Structure markup :

```
section.why
└── .why__inner (max-width: 1080px)
    ├── .why__head : .eyebrow + .why__title (le span du titre prend var(--persona))
    └── .tabs#tabs (radius 22px, var(--card-bg), bordure --line-2)
        ├── .tabs__nav : N boutons .tab (.tab__idx + .tab__label),
        │   grid repeat(var(--tab-count, 3), minmax(0, 1fr))
        │   └── .tabs__track (3px) > .tabs__fill (progression)
        ├── .tabs__stage : N .panel empilés (grid-area: 1 / 1)
        │   └── .panel : .panel__body (.panel__tag + .panel__title + .panel__text
        │       + .panel__chips) + .panel__media (anneaux + pulse + médaillon icône)
        └── .tabs__foot : .tabs__dots (boutons .dot) + .tabs__state (compteur zéro-paddé « 01 / 03 · défilement automatique »)
```

Tempo et easings (variables locales sur `.why`) :

```css
--cycle: 4500ms;                       /* durée d'un onglet */
--xfade: 640ms;                        /* durée du cross-fade entre panneaux */
--ease-out: cubic-bezier(.22, 1, .36, 1);
--ease-soft: cubic-bezier(.4, 0, .2, 1);
```

Mécanique de la barre de progression (`.tabs__fill`) : largeur `calc(100% / var(--tab-count, 3))`, dégradé `linear-gradient(90deg, rgba(var(--persona-rgb) / .5), var(--persona))`, glow `box-shadow: 0 0 12px -2px rgba(var(--persona-rgb) / .5)`, point terminal de `8px` avec halo. Le `left` (saut d'onglet) est animé par le JS avec `transition: left var(--xfade) var(--ease-out)` ; le remplissage est piloté par la classe `.is-running` : `transform: scaleX(0)` → `scaleX(1)` avec `transition: transform var(--cycle) linear`. La classe `.is-paused` fige la progression.

Transition de panneau : panneau inactif `opacity: 0; visibility: hidden; transform: translateY(10px)`, panneau `.is-active` revient à `translateY(0)` en `var(--xfade) var(--ease-out)`. Entrée échelonnée du contenu actif :

```css
.panel.is-active .panel__tag   { animation: itemIn 540ms var(--ease-out) both 80ms; }
.panel.is-active .panel__title { animation: itemIn 580ms var(--ease-out) both 170ms; }
.panel.is-active .panel__text  { animation: itemIn 620ms var(--ease-out) both 260ms; }
.panel.is-active .chip         { animation: itemIn 560ms var(--ease-out) both calc(360ms + var(--i, 0) * 80ms); }

@keyframes itemIn {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

Colonne visuelle (`.panel__media`, carré max `300px`) : deux anneaux concentriques qui respirent (`border: 1px solid`, alpha persona `.28` pour le premier, `.35` pour le second), une onde de pulsation, et un médaillon central (`38%` de la scène, `border-radius: 28%`) qui flotte. Animations d'ambiance, actives en continu sur le panneau visible :

```css
.panel.is-active .panel__ring--1 { animation: breathe 5.4s var(--ease-soft) infinite; }
.panel.is-active .panel__ring--2 { animation: breathe 5.4s var(--ease-soft) infinite .9s; }
.panel.is-active .panel__medal   { animation: float 4.6s ease-in-out infinite; }
.panel.is-active .panel__pulse   { animation: pulse 4.5s var(--ease-soft) infinite; }

@keyframes breathe {
  0%, 100% { transform: translate(-50%, -50%) scale(1);    opacity: var(--o, .5); }
  50%      { transform: translate(-50%, -50%) scale(1.06); opacity: calc(var(--o, .5) * .55); }
}
@keyframes float {
  0%, 100% { transform: translateY(-4%) rotate(-1.2deg); }
  50%      { transform: translateY(4%)  rotate(1.2deg); }
}
@keyframes pulse {
  0%   { transform: translate(-50%, -50%) scale(.92); opacity: 0; }
  18%  { opacity: .55; }
  80%  { opacity: 0; }
  100% { transform: translate(-50%, -50%) scale(2.05); opacity: 0; }
}
```

Dots de navigation : `9px`, fond `var(--line-3)` ; état actif `background: var(--persona)`, `transform: scale(1.25)`, halo `box-shadow: 0 0 0 4px rgba(var(--persona-rgb) / .14)`.

Accessibilité : `prefers-reduced-motion: reduce` désactive toutes les animations, masque la barre de progression et la pulsation, et n'affiche que le panneau actif. Sous `820px`, le panneau passe en 1 colonne avec le visuel au-dessus du texte.

### 5. Chips, badges et tags

| Composant | Style exact | Usage |
|---|---|---|
| `.pub-filter` (filtre pill) | `font-size: 0.85rem; font-weight: 600`, `padding: 9px 18px`, `border-radius: 999px`, fond `var(--surface-low)`, bordure `1px solid var(--line-2)` ; état actif : texte `#fff`, fond et bordure `var(--text-strong)` | filtres de liste cliquables |
| `.res-tag` (tag sur image) | `font-size: 0.65rem; font-weight: 700`, uppercase, `letter-spacing: 0.08em`, `padding: 4px 10px`, `border-radius: 100px`, fond `var(--accent-a-15)`, bordure `1px solid var(--accent-a-30)`, `backdrop-filter: blur(8px)`, positionné `top: 14px; left: 14px` | catégorie en surimpression d'un visuel |
| `.pub-card-tag` (tag texte nu) | `font-size: 0.72rem; font-weight: 800`, uppercase, `letter-spacing: 0.12em`, couleur `var(--pub-hue)` | thématique en tête de card, sans fond |
| `.panel__tag` (pill autocycle) | `font-size: .68rem; font-weight: 700`, uppercase, `letter-spacing: .14em`, `padding: .42em .85em`, `border-radius: 999px`, fond `rgba(var(--persona-rgb) / .08)`, bordure `1px solid rgba(var(--persona-rgb) / .18)`, point rond de `5px` en préfixe | label de panneau, teinté persona |
| `.chip` (puce interlocuteur) | `font-size: .82rem; font-weight: 600`, `padding: .5em .9em`, `border-radius: 10px`, fond `var(--bg-mid)`, bordure `1px solid var(--line-2)`, carré de `6px` (radius `2px`) teinté persona en préfixe | énumération de personnes/objets dans un panneau |
| `.cas-num` (numéro de card) | `font-size: 0.7rem; font-weight: 700`, uppercase, `letter-spacing: 0.12em`, couleur `--cas-pop`, `opacity: 0.85`, tiret décoratif `18px × 1.5px` en préfixe | numérotation "01, 02, 03" en coin de card |
| `.todo` (badge interne) | `padding: 0.15rem 0.55rem`, `border-radius: 4px`, fond `rgba(245, 158, 11, 0.15)`, texte `#F59E0B`, `0.7rem / 700 / letter-spacing 0.1em` | marqueur de contenu provisoire |

Convention : un tag est toujours en uppercase avec letter-spacing large (0.08em à 0.16em) et une graisse forte (700 ou 800). La forme pill (`999px`/`100px`) sert au filtre et au label flottant ; le tag de card est le plus souvent du texte nu coloré, sans fond.

### 6. Card canonique (copy-pasteable)

Synthèse du pattern dominant (pub-card et tc-card), autoportante avec les tokens requis :

```css
/* Tokens requis (valeurs exactes du :root de global.css) */
:root {
  --card-bg: linear-gradient(160deg, #FFFFFF 0%, #ECF1F9 100%);
  --line-1: rgba(15, 23, 42, 0.07);
  --line-2: rgba(15, 23, 42, 0.13);
  --text-strong: #061838;
  --text-2: #3A4A6B;
  --text-3: #586A8A;
  --accent: #0EA5E9;
  --accent-a-25: rgba(14, 165, 233, 0.30);
  --accent-a-30: rgba(14, 165, 233, 0.35);
}

/* Card canonique : fond dégradé + bordure fine au repos,
   élévation accentuée uniquement au survol */
.card {
  --card-hue: var(--accent); /* surcharger par offre/persona si besoin */
  display: flex;
  flex-direction: column;
  background: var(--card-bg);
  border: 1px solid var(--line-2);
  border-radius: 14px;
  overflow: hidden;
  text-decoration: none;
  color: inherit;
  transition:
    transform 0.3s cubic-bezier(0.16, 1, 0.3, 1),
    border-color 0.25s ease,
    box-shadow 0.25s ease;
}
.card:hover {
  transform: translateY(-3px);
  border-color: color-mix(in srgb, var(--card-hue) 45%, transparent);
  box-shadow: 0 20px 44px -22px color-mix(in srgb, var(--card-hue) 30%, transparent);
}

/* Visuel en tête (optionnel) */
.card-img {
  position: relative;
  aspect-ratio: 16 / 10;
  overflow: hidden;
}
.card-img img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
.card:hover .card-img img { transform: scale(1.04); }

/* Corps */
.card-body {
  padding: 1.35rem 1.5rem 1.5rem;
  display: flex;
  flex-direction: column;
  flex: 1;
}
.card-tag {
  color: var(--card-hue);
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-bottom: 0.75rem;
}
.card-title {
  color: var(--text-strong); /* la pub-card de référence utilise var(--text-1) ; les deux existent selon la card */
  font-size: clamp(1.05rem, 1.45vw, 1.25rem);
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: -0.01em;
  margin: 0 0 0.7rem;
}
.card-excerpt {
  color: var(--text-2);
  font-size: 0.93rem;
  line-height: 1.62;
  margin: 0 0 1.1rem;
  flex: 1;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-3);
  font-size: 0.82rem;
}
```

Variantes à appliquer sur cette base, en gardant tout le reste :
- **Card vedette / offre** : `border-radius: 18px`, padding `2.25rem 1.75rem 1.75rem`, hover plus marqué `translateY(-6px)` avec `box-shadow: 0 24px 48px -14px rgba(0, 0, 0, 0.6), 0 0 0 1px var(--card-hue) inset` et la barre supérieure de 3px en `scaleX(0)` → `scaleX(1)` (`0.5s cubic-bezier(.2,.8,.2,1)`).
- **Card tarif / comparaison** : `border-radius: 16px`, hover `translateY(-4px)`, `border-color: var(--accent-a-30)`, `box-shadow: 0 22px 44px -20px var(--accent-a-25)`.
- **Card dense / technique** : `border-radius: 8px`, padding `1.25rem`, fond `rgba(255,255,255,0.035)`, sans hover.

---

## 6. Animations et interactions

Le site privilégie un motion sobre et institutionnel : reveals discrets au scroll, micro-interactions au survol, et un seul composant fortement animé (l'autocycle « Pourquoi nous » des pages cibles). Tout est gouverné par `prefers-reduced-motion`.

### 1. Reveal au scroll (système `.rv` / `.in`)

Mécanisme unique pour tout le site, défini dans `assets/js/site.js` (JS) et `assets/css/global.css` (CSS).

**Principe** : on pose la classe `rv` sur un élément dans le HTML. Un `IntersectionObserver` ajoute la classe `in` à la première intersection, puis cesse d'observer l'élément (le reveal ne se rejoue jamais). Les classes `d1` à `d4` ajoutent un délai en escalier pour les groupes d'éléments.

**JS exact (copy-pasteable, extrait de `site.js`)** :

```js
if ('IntersectionObserver' in window) {
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in');
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('.rv').forEach((el) => revealObserver.observe(el));
} else {
  document.querySelectorAll('.rv').forEach((el) => el.classList.add('in'));
}
```

Paramètres à reproduire tels quels : `threshold: 0.08`, `rootMargin: '0px 0px -40px 0px'` (l'élément doit avoir dépassé de 40 px le bas du viewport avant de se révéler). Fallback sans `IntersectionObserver` : tout est révélé immédiatement.

**CSS exact (copy-pasteable, extrait de `global.css`)** :

```css
/* ─────────── REVEAL ON SCROLL ─────────── */
.rv { opacity: 0; transform: translateY(20px); transition: opacity 0.7s ease, transform 0.7s ease; }
.rv.in { opacity: 1; transform: none; }
.rv.d1 { transition-delay: 0.08s; }
.rv.d2 { transition-delay: 0.16s; }
.rv.d3 { transition-delay: 0.24s; }
.rv.d4 { transition-delay: 0.32s; }
@media (prefers-reduced-motion: reduce) {
  .rv { opacity: 1; transform: none; transition: none; }
}
```

États : initial `opacity: 0; translateY(20px)`, final `opacity: 1; transform: none`, durée 0.7s, easing `ease`, stagger par pas de 0.08s.

**Variante renforcée (page équipe)** : les profils surchargent `.rv` avec une translation plus ample et un easing expressif, plus un zoom subtil de la photo (extrait de `assets/css/pages/equipe.css`) :

```css
.profile.rv { opacity: 0; transform: translateY(80px); transition: opacity 0.9s cubic-bezier(0.16, 1, 0.3, 1), transform 0.9s cubic-bezier(0.16, 1, 0.3, 1); }
.profile.rv.in { opacity: 1; transform: none; }
.profile.rv .profile-photo { transform: scale(0.96); transition: transform 1s cubic-bezier(0.16, 1, 0.3, 1); }
.profile.rv.in .profile-photo { transform: scale(1); }
```

**Exceptions connues (décisions volontaires)** : les cartes de contenu de la page d'accueil (cartes cas d'usage, cartes publications) et les cards de la page Publications (`.pub-card`) ne portent PAS la classe `rv` : elles s'affichent immédiatement. Le reveal est réservé aux en-têtes de section, intros et wrappers (eyebrow, titre, sous-titre, CTA), jamais aux grilles de cards de contenu. Intention : ne pas retarder l'accès au contenu utile.

### 2. Toutes les @keyframes (verbatim) et leur usage

**`global.css`** : aucune keyframe (le chrome commun n'utilise que des transitions).

**`assets/css/pages/home.css`** :

Soulignement du mot accentué du H1 hero (se dessine de gauche à droite, 0.6s après le chargement) :

```css
.hero-h1 .accent::after {
  content: '';
  position: absolute; left: 0; right: 0; bottom: 0.04em;
  height: 0.08em;
  background: var(--blue);
  opacity: 0.25;
  transform: scaleX(0); transform-origin: left;
  animation: hero-accent-draw 1s 0.6s cubic-bezier(.2,.8,.2,1) forwards;
}
@keyframes hero-accent-draw {
  to { transform: scaleX(1); }
}
```

Note : une seconde règle de home.css surcharge le rendu final de ce trait : `background: linear-gradient(90deg, var(--accent) 0%, var(--accent-bright) 70%, transparent 100%)`, `opacity: 1`, `height: 0.055em`. La mécanique du tracé (scaleX(0) vers scaleX(1), 1s, délai 0.6s) reste celle du bloc ci-dessus.

Pictogrammes animés des « proof points » du hero (SVG décoratifs en boucle infinie) :

```css
.hp-orbit { transform-box: view-box; transform-origin: 40px 40px; animation: hp-spin 18s linear infinite; }
@keyframes hp-spin { to { transform: rotate(360deg); } }
.hp-core { transform-box: view-box; transform-origin: 40px 41px; animation: hp-breathe 4s ease-in-out infinite; }
@keyframes hp-breathe { 0%,100% { transform: scale(1); } 50% { transform: scale(1.06); } }
.hp-bar { transform-box: fill-box; transform-origin: left center; animation: hp-bar-fill 3.6s ease-in-out infinite; }
.hp-bar--2 { animation-delay: .22s; }
.hp-bar--3 { animation-delay: .44s; }
@keyframes hp-bar-fill { 0%,8% { transform: scaleX(0); opacity:.4; } 38%,66% { transform: scaleX(1); opacity:1; } 92%,100% { transform: scaleX(0); opacity:.4; } }
.hp-check { stroke-dasharray: 22; stroke-dashoffset: 22; animation: hp-check 3.6s ease-in-out infinite; }
@keyframes hp-check { 0%,58% { stroke-dashoffset: 22; } 74%,92% { stroke-dashoffset: 0; } 100% { stroke-dashoffset: 22; } }
.hp-beam { transform-box: view-box; transform-origin: 40px 24px; animation: hp-rock 6.5s ease-in-out infinite; }
@keyframes hp-rock { 0%,100% { transform: rotate(0deg); } 18% { transform: rotate(7deg); } 46% { transform: rotate(-7deg); } 72% { transform: rotate(3deg); } 88% { transform: rotate(-1.5deg); } }
.hp-sign { stroke-dasharray: 82; stroke-dashoffset: 82; animation: hp-sign 4.4s ease-in-out infinite; }
@keyframes hp-sign { 0%,6% { stroke-dashoffset: 82; } 52%,80% { stroke-dashoffset: 0; } 97%,100% { stroke-dashoffset: 82; } }
.hp-seal { transform-box: view-box; transform-origin: 57px 55px; animation: hp-breathe 4.4s ease-in-out infinite; }
```

Marquee infini des logos clients (bande « confiance », duplication du contenu puis translation de moitié) :

```css
.trust-track {
  display: flex; gap: 4rem; align-items: center;
  animation: scroll-x 40s linear infinite;
  width: max-content;
}
@keyframes scroll-x {
  from { transform: translateX(0); }
  to   { transform: translateX(-50%); }
}
```

Sur mobile (max-width 980px env.), la durée passe à `animation-duration: 32s` et le mask de fondu latéral est retiré.

Entrée du bento équipe du hero (5 cartes, délais individuels via la variable inline `--d` posée dans le HTML : 0.05s, 0.15s, 0.25s, 0.35s, 0.45s) :

```css
@keyframes hv-rise {
  from { opacity: 0; transform: translateY(14px) scale(0.985); }
  to   { opacity: 1; transform: translateY(0)   scale(1); }
}
.hv-bento-card {
  opacity: 0;
  animation: hv-rise 0.75s cubic-bezier(.2,.8,.2,1) var(--d, 0s) forwards;
  transition: transform 0.4s cubic-bezier(.2,.8,.2,1), box-shadow 0.4s, border-color 0.3s;
  will-change: transform;
}
```

```html
<a href="/equipe/" class="hv-bento-card hv-bento-card--a" style="--d:0.05s;">
```

**`assets/css/components/autocycle.css`** (animations d'ambiance du médaillon, actives uniquement sur le panneau `.is-active`) :

```css
.panel.is-active .panel__ring--1 { animation: breathe 5.4s var(--ease-soft) infinite; }
.panel.is-active .panel__ring--2 { animation: breathe 5.4s var(--ease-soft) infinite .9s; }
.panel.is-active .panel__medal   { animation: float 4.6s ease-in-out infinite; }
.panel.is-active .panel__pulse   { animation: pulse 4.5s var(--ease-soft) infinite; }

@keyframes breathe {
  0%, 100% { transform: translate(-50%, -50%) scale(1);    opacity: var(--o, .5); }
  50%      { transform: translate(-50%, -50%) scale(1.06); opacity: calc(var(--o, .5) * .55); }
}
@keyframes float {
  0%, 100% { transform: translateY(-4%) rotate(-1.2deg); }
  50%      { transform: translateY(4%)  rotate(1.2deg); }
}
@keyframes pulse {
  0%   { transform: translate(-50%, -50%) scale(.92); opacity: 0; }
  18%  { opacity: .55; }
  80%  { opacity: 0; }
  100% { transform: translate(-50%, -50%) scale(2.05); opacity: 0; }
}

/* Entrée du médaillon au changement d'onglet */
.panel.is-active .panel__media { animation: medalIn var(--xfade) var(--ease-out) both; }
@keyframes medalIn {
  0%   { opacity: 0; transform: translateY(10px) scale(.92); }
  100% { opacity: 1; transform: translateY(0) scale(1); }
}

/* Animation d'entrée échelonnée des éléments texte du panneau actif */
.panel.is-active .panel__tag   { animation: itemIn 540ms var(--ease-out) both 80ms; }
.panel.is-active .panel__title { animation: itemIn 580ms var(--ease-out) both 170ms; }
.panel.is-active .panel__text  { animation: itemIn 620ms var(--ease-out) both 260ms; }
.panel.is-active .chip         { animation: itemIn 560ms var(--ease-out) both calc(360ms + var(--i, 0) * 80ms); }

@keyframes itemIn {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

**`assets/css/pages/parcours.css`** (reflet lumineux qui parcourt la ligne du cheminement méthode) :

```css
.ch-flow::after { content:''; position:absolute; top:36px; left:9%; width:16%; height:3px; border-radius:3px;
  background:linear-gradient(90deg, transparent, rgba(255,255,255,.9), transparent); animation:ch-sheen 3.2s ease-in-out infinite; }
@keyframes ch-sheen { 0%{ left:7%; opacity:0; } 18%{opacity:1;} 82%{opacity:1;} 100%{ left:77%; opacity:0; } }
```

### 3. Transitions canoniques (la convention maison)

Trois registres, à appliquer selon la nature du changement :

1. **Couleurs et états de liens/boutons : `0.2s` avec l'easing par défaut (`ease`)**. C'est LA convention dominante du site pour `color`, `background`, `border-color`, `box-shadow`, `opacity`. Exemples canoniques : `.nav-link { transition: color 0.2s; }`, boutons `transition: background 0.2s, transform 0.15s, border-color 0.2s, color 0.2s, box-shadow 0.2s;`. Le `transform` des boutons est volontairement plus court : **`0.15s`** (le `translateY(-1px)` au hover doit être quasi instantané).

2. **Cards au survol : `0.3s` à `0.35s`** pour `transform`, `box-shadow`, `border-color` (lift de -2 à -4 px). Exemple : `.trust-logo { transition: transform 0.3s, box-shadow 0.3s, background 0.3s; }`.

3. **Mouvements expressifs (transform de grande amplitude) : easing maison `cubic-bezier(.2,.8,.2,1)`**, durées 0.3s à 0.6s selon l'amplitude. C'est la courbe « signature » du site (sortie rapide puis amorti) :
   - `.btn-magnetic { transition: transform 0.3s cubic-bezier(.2,.8,.2,1), background 0.2s; }`
   - `.hv-bento-card { transition: transform 0.4s cubic-bezier(.2,.8,.2,1), box-shadow 0.4s, border-color 0.3s; }`
   - images de cards : `transition: transform 0.5s cubic-bezier(.2,.8,.2,1);` (zoom au hover)

Deuxième courbe expressive utilisée sur les pages équipe et publications : **`cubic-bezier(0.16, 1, 0.3, 1)`** (ease-out-quint très amorti), ex. `.pub-card { transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.25s ease, box-shadow 0.25s ease; }` et image `transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);`.

Micro-détail récurrent : les flèches SVG des liens glissent de 3 px au hover, en 0.2s :

```css
.btn-ghost svg { transition: transform 0.2s; }
.btn-ghost:hover svg { transform: translateX(3px); }
```

### 4. Navbar au scroll, smooth scroll et autres comportements JS

**Navbar (glass) au scroll**. JS : la classe `scrolled` est posée dès que `window.scrollY > 40` (listener `scroll` passif, état appliqué aussi au chargement) :

```js
const navbar = document.getElementById('navbar');
if (navbar) {
  const updateNavbar = () => navbar.classList.toggle('scrolled', window.scrollY > 40);
  updateNavbar();
  window.addEventListener('scroll', updateNavbar, { passive: true });
}
```

CSS associé : `#navbar { transition: box-shadow 0.3s ease, background 0.3s ease; }` et `#navbar.scrolled { background: var(--navbar-bg-scroll, rgba(5, 13, 29, 0.88)); box-shadow: 0 8px 32px -12px rgba(0, 0, 0, 0.6); }`.

**Smooth scroll**. Double mécanisme : `html { scroll-behavior: smooth; }` en CSS, plus un handler JS sur tous les `a[href^="#"]` qui compense la hauteur de la navbar avec un offset fixe de **118 px** :

```js
window.scrollTo({
  top: target.getBoundingClientRect().top + window.pageYOffset - 118,
  behavior: 'smooth',
});
```

Complément CSS pour les ancres atteintes par URL : `:target { scroll-margin-top: 80px; }`.

**Hamburger mobile (morphing en croix)**. Les trois barres (`#b1`, `#b2`, `#b3`) sont transformées en JS, transition CSS `transform 0.3s, opacity 0.3s` :

```js
if (bars[0]) bars[0].style.transform = navOpen ? 'translateY(6.5px) rotate(45deg)' : '';
if (bars[1]) bars[1].style.opacity = navOpen ? '0' : '';
if (bars[2]) bars[2].style.transform = navOpen ? 'translateY(-6.5px) rotate(-45deg)' : '';
```

Le menu mobile `#mob-menu` s'ouvre par bascule de classe `open` (`display: none` vers `display: flex`, sans animation). Chaque lien du menu le referme au clic.

**Boutons magnétiques (`.btn-magnetic`)**. Le bouton suit légèrement le curseur, son contenu interne (`.btn-content`) suit avec un facteur moindre (effet de parallaxe). Activé uniquement si : pas de reduced motion, pointeur capable de hover, viewport d'au moins 981 px. Utilisé sur les CTAs des pages cibles (entrepreneurs, experts-comptables, avocats, notaires, équipe, ressources) :

```js
if (!reducedMotion && window.matchMedia('(hover: hover) and (min-width: 981px)').matches) {
  document.querySelectorAll('.btn-magnetic').forEach((btn) => {
    const content = btn.querySelector('.btn-content') || btn;

    btn.addEventListener('pointermove', (event) => {
      const rect = btn.getBoundingClientRect();
      const x = event.clientX - rect.left - rect.width / 2;
      const y = event.clientY - rect.top - rect.height / 2;
      btn.style.transform = `translate(${(x * 0.25).toFixed(1)}px, ${(y * 0.4).toFixed(1)}px)`;
      if (content !== btn) {
        content.style.transform = `translate(${(x * 0.12).toFixed(1)}px, ${(y * 0.18).toFixed(1)}px)`;
      }
    });

    btn.addEventListener('pointerleave', () => {
      btn.style.transform = '';
      if (content !== btn) content.style.transform = '';
    });
  });
}
```

CSS compagnon (le retour à la position de repos est animé par la transition) :

```css
.btn-magnetic {
  will-change: transform;
  transition: transform 0.3s cubic-bezier(.2,.8,.2,1), background 0.2s;
}
.btn-magnetic .btn-content {
  display: inline-flex; align-items: center; gap: 8px;
  transition: transform 0.3s cubic-bezier(.2,.8,.2,1);
  pointer-events: none;
}
```

**Formulaire de contact** (`assets/js/pages/home.js`) : pas d'animation, uniquement des états : bouton désactivé avec le texte `'Envoi en cours...'` pendant le POST, puis bascule `display: none` / `display: block` entre formulaire et message de succès ; en erreur, restauration du bouton et affichage du message d'erreur.

**Filtres Publications** (`assets/js/pages/ressources.js`) : filtrage instantané, sans animation. Bascule de la classe `is-active` et de `aria-pressed` sur les boutons `.pub-filter`, et de l'attribut `hidden` sur les `.pub-card` selon `data-theme`.

### 5. Gestion de prefers-reduced-motion

Règle de la maison : **chaque animation a son opt-out explicite**, côté CSS et côté JS.

Côté JS (`site.js` et `autocycle.js`), le flag est lu une fois :

```js
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
```

Il désactive : l'effet magnétique des boutons (site.js) et tout l'autoplay de l'autocycle (pas de timer, pas d'animation de remplissage, `pause()`/`resume()` deviennent inopérants).

Côté CSS, quatre blocs :

```css
/* global.css : reveal neutralisé */
@media (prefers-reduced-motion: reduce) {
  .rv { opacity: 1; transform: none; transition: none; }
}

/* home.css : soulignement hero figé à l'état final */
@media (prefers-reduced-motion: reduce) {
  .hero-h1 .accent::after { animation: none; transform: scaleX(1); }
}

/* home.css : pictos hero et bento gelés */
@media (prefers-reduced-motion: reduce) {
  .hp-orbit, .hp-core, .hp-bar, .hp-check, .hp-beam, .hp-sign, .hp-seal { animation: none; }
  .hp-bar { transform: scaleX(1); opacity: 1; }
  .hp-check, .hp-sign { stroke-dashoffset: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .hv-bento-card { animation: none !important; opacity: 1 !important; }
}
```

Et le bloc complet de l'autocycle (tout révélé, seul le panneau actif visible, barre de progression masquée) :

```css
@media (prefers-reduced-motion: reduce) {
  .tabs__fill,
  .panel,
  .panel.is-active .panel__media,
  .panel.is-active .panel__ring--1,
  .panel.is-active .panel__ring--2,
  .panel.is-active .panel__medal,
  .panel.is-active .panel__pulse,
  .panel.is-active .panel__tag,
  .panel.is-active .panel__title,
  .panel.is-active .panel__text,
  .panel.is-active .chip {
    animation: none !important;
    transition: opacity .2s ease !important;
    transform: none !important;
  }
  .panel__ring,
  .panel__medal { transform: translate(-50%, -50%) !important; }
  .panel__medal { left: 50%; top: 50%; position: absolute; }
  .panel__pulse { display: none; }
  .tabs__fill { display: none; }
  .panel {
    opacity: 1;
    visibility: visible;
  }
  .panel:not(.is-active) { display: none; }
}
```

Le bento du hero utilise aussi la forme inverse : l'animation d'entrée `hv-rise` et sa mise en pause au hover (`animation-play-state: paused`) sont re-déclarées dans `@media (prefers-reduced-motion: no-preference) { ... }`.

### 6. Composant autocycle (onglets « Pourquoi nous » auto-cyclés)

Fichiers : `assets/js/autocycle.js` + `assets/css/components/autocycle.css`. Couleur d'accent héritée de la page via `var(--persona)`.

**Tempo (tokens CSS sur `.why`, source de vérité unique)** :

```css
.why {
  --cycle: 4500ms;   /* durée d'un onglet */
  --xfade: 640ms;    /* durée du cross-fade entre panneaux */
  --ease-out: cubic-bezier(.22, 1, .36, 1);
  --ease-soft: cubic-bezier(.4, 0, .2, 1);
}
```

Le JS lit `--cycle` dans le CSS (pas de durée codée en dur, fallback 4500) :

```js
var cycleMs = parseFloat(getComputedStyle(root).getPropertyValue("--cycle")) || 4500;
```

**Logique de cycle** :
- Autoplay : `setInterval(next, cycleMs)`, qui appelle `activate(index + 1)` en boucle.
- L'autoplay ne tourne que si le composant est **visible** : un `IntersectionObserver` dédié avec `threshold: 0.4` met `inView` à jour et appelle `start()` / `stop()`. État initial : `activate(0, { silent: true })`, le timer démarre à l'entrée dans le viewport.
- **Pause au hover et au focus : oui.** `mouseenter` et `focusin` appellent `pause()` ; `mouseleave` et `focusout` (si le focus sort vraiment du composant) appellent `resume()`. À la pause, le JS fige la barre de progression à sa position courante en calculant le ratio rempli et en posant `fill.style.transform = "scaleX(" + ratio + ")"` ; à la reprise, il rend la main au CSS (`fill.style.transform = ""`) et relance un cycle complet.
- Saut manuel (clic onglet, clic dot, clavier) : `jump(i)` active le panneau et **réinitialise le timer** si l'autoplay était en cours. Navigation clavier complète : ArrowRight/ArrowDown (suivant), ArrowLeft/ArrowUp (précédent), Home, End.
- Barre de progression : positionnée sous l'onglet actif via `left` (animé en `var(--xfade) var(--ease-out)`), remplissage par `transform: scaleX(0)` vers `scaleX(1)` en `var(--cycle) linear` quand la classe `is-running` est posée sur `.tabs`. Le redémarrage du remplissage force un reflow (`void fill.offsetWidth;`) entre le retrait et la repose de la classe.

CSS clé du remplissage :

```css
.tabs.is-running .tabs__fill {
  transform: scaleX(1);
  transition:
    left var(--xfade) var(--ease-out),
    transform var(--cycle) linear;
}
.tabs.is-paused .tabs__fill {
  transition: left var(--xfade) var(--ease-out);
}
```

**Transition entre panneaux** (cross-fade superposé, les panneaux partagent `grid-area: 1 / 1`) :

```css
.panel {
  opacity: 0;
  visibility: hidden;
  transform: translateY(10px);
  transition:
    opacity var(--xfade) var(--ease-out),
    transform var(--xfade) var(--ease-out),
    visibility 0s linear var(--xfade);
  pointer-events: none;
}
.panel.is-active {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
  transition:
    opacity var(--xfade) var(--ease-out),
    transform var(--xfade) var(--ease-out),
    visibility 0s;
  pointer-events: auto;
}
```

À chaque activation, les éléments du panneau entrent en cascade (`itemIn`, voir section 2) : tag à 80 ms, titre à 170 ms, texte à 260 ms, chips à partir de 360 ms avec +80 ms par chip (`calc(360ms + var(--i, 0) * 80ms)`, l'index `--i` étant posé en style inline). Les dots du pied de scène ont une transition `background .3s ease, transform .3s ease, box-shadow .3s ease` et le dot courant passe à `transform: scale(1.25)`.

---

## 7. Iconographie

### 1. Principe : librairie maison ncf-icons, rien d'autre

Toute l'iconographie du site provient d'une librairie propriétaire unique : **ncf-icons v2.0** (36 icônes SVG line-art, 24×24). Elle vit dans `assets/ncf-icons/` et se compose de :

- `icons-sprite.svg` : sprite SVG regroupant les 36 icônes en `<symbol id="...">` (une seule requête HTTP, méthode recommandée en production) ;
- `svg/` : les 36 icônes individuelles (`ncf-icon-{categorie}-{nom}.svg`) pour usage inline, `<img>` ou background CSS ;
- `icons.css` : classes utilitaires (taille, couleur, états) ;
- `ICON_GUIDELINES.md` et `README.md` : règles de création et d'usage ;
- `preview.html` : page d'aperçu visuel.

**Interdiction stricte** de toute icône externe : pas de Heroicons, pas de Lucide, pas de FontAwesome, pas d'icônes Material, et **jamais d'emojis dans l'UI**. Si une icône manque, on la crée selon les guidelines (section 2 ci-dessous), on ne l'importe pas.

### 2. Style de dessin (pour créer de nouvelles icônes cohérentes)

Spécifications exactes, non négociables :

- **Canvas / grille** : 24×24 px, `viewBox="0 0 24 24"`.
- **Style** : line-art moderne. `fill="none"` par défaut (seuls de petits points internes peuvent être remplis, disque de validation 1 px max).
- **Trait principal** : `stroke-width="1.5"` partout, sauf équerres.
- **Terminaisons** : `stroke-linecap="round"` et `stroke-linejoin="round"`.
- **Couleur** : toujours `stroke="currentColor"`, jamais de couleur en dur dans le SVG.
- **Géométrie** : strictement orthogonale, angles à 0°, 45° ou 90° uniquement (arcs circulaires libres autorisés : cercles complets ou demi-cercles). Coordonnées sur entiers ou demi-pixels uniquement (5.847 ou 12.331 sont interdits).
- **Densité** : entre 2 et 5 éléments graphiques par icône (hors équerres). 7+ éléments = trop chargé. Espacement minimal entre deux éléments parallèles : 2 px.

**La signature équerre (obligatoire)** : chaque icône porte deux équerres en L de 3 px de côté, en coins opposés (haut-gauche et bas-droite), avec un trait plus fin (`stroke-width="1"`). C'est ce qui distingue une icône NCF d'une icône générique. Code à copier-coller en premier dans chaque SVG :

```xml
<!-- Signature NCF : équerres aux coins opposés -->
<path d="M 1 4 L 1 1 L 4 1" stroke-width="1"/>
<path d="M 20 23 L 23 23 L 23 20" stroke-width="1"/>
```

**Zone utile du dessin** : à cause des équerres, l'objet se dessine dans un carré 16×16 px centré (entre x=4 et x=20, entre y=4 et y=20), avec au minimum 1 px de respiration entre le dessin et chaque équerre. Le dessin ne doit jamais toucher les équerres.

**Template d'une nouvelle icône** :

```xml
<!-- NCF Icon · {categorie}/{nom} · v2.0 · 24×24 · moderne + équerres -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">

  <!-- 1. Signature NCF : équerres aux coins opposés -->
  <path d="M 1 4 L 1 1 L 4 1" stroke-width="1"/>
  <path d="M 20 23 L 23 23 L 23 20" stroke-width="1"/>

  <!-- 2. Dessin de l'objet, contenu dans la zone utile 16×16 (4,4 → 20,20) -->
  <!-- ... -->

</svg>
```

**Nommage** : fichier `ncf-icon-{categorie}-{nom}.svg`, catégories autorisées : `evaluation`, `process`, `value`, `team`, `business`, `nav`. Nom en kebab-case anglais, court.

**Métaphores autorisées** (vocabulaire métier littéral d'un cabinet d'évaluation) : feuille, dossier, rapport, sceau ; balance, règle, jauge, courbe ; flèche directionnelle, silhouettes ; enveloppe scellée, cadenas, coffre ; bulle de dialogue ; trois colonnes, formule stylisée ; horloge, calendrier, sablier. **Interdits** : ampoule, fusée, cible, poignée de main, émoticônes et visages stylisés, logos, symboles politiques ou religieux. Test de validation éditorial ("test de Lyon") : si l'icône paraîtrait enfantine ou marketing dans un rapport remis à un dirigeant de PME de 60 ans, on la refait.

**Checklist de cohérence avant ajout** (les 6 réponses doivent être oui, sinon rejet) :
1. Équerres présentes et au bon endroit ?
2. Objet dans la zone utile 16×16 ?
3. Poids visuel comparable aux autres icônes ?
4. Trait principal à 1.5 ?
5. Équerres à 1 (plus fines) ?
6. Signature lisible à 24 px ?

**Anti-patterns** : équerres oubliées ou à la mauvaise taille (strictement 3 px de long, trait 1), équerres aux 4 coins (2 en angle opposé suffisent), trait principal à 2 ou plus, coordonnées à 3 décimales, couleur en dur, plus de 5 éléments, icône affichée sous 20 px.

Variante rare autorisée : équerres en couleur or (`var(--gold)`, valeur `#C9A961`) pour des contextes premium, fichier suffixé `-gold.svg`. Par défaut, on reste en `currentColor`.

### 3. Usage : markup, tailles, couleur

**Méthode recommandée en production : le sprite.** Les `id` des symboles sont les noms courts SANS préfixe de catégorie (`#balance`, pas `#evaluation-balance`) :

```html
<svg class="ncf-icon ncf-icon--md" aria-hidden="true">
  <use href="assets/ncf-icons/icons-sprite.svg#balance"/>
</svg>
```

Autres méthodes possibles : SVG inline (copier le contenu du fichier `svg/`, utile pour animer), `<img src=".../svg/ncf-icon-evaluation-balance.svg" width="24" height="24" alt="Balance">` (couleur figée), ou background CSS pour les décors non cliquables.

**Couleur** : toutes les icônes utilisent `stroke="currentColor"`, donc elles héritent de la couleur de texte du parent. C'est le mécanisme central : on ne colore jamais l'icône directement, on colore son conteneur. Les variables `--ncf-*` définies dans `icons.css` ne sont qu'un fallback ; dans la pratique les `.ncf-icon` prennent la couleur du texte parent, ce qui les aligne automatiquement sur la palette du site.

**Tailles** (ne jamais descendre sous 20 px : les équerres deviennent illisibles et l'icône perd sa signature) :

| Contexte | Taille | Classe |
|---|---|---|
| Inline texte | 20 px | `.ncf-icon--xs` |
| Bouton / nav | 24 px | `.ncf-icon--sm` |
| Carte feature | 32 px | `.ncf-icon--md` |
| Carte large | 48 px | `.ncf-icon--lg` |
| Hero | 64 px | `.ncf-icon--xl` |

**Accessibilité** : icône décorative = `aria-hidden="true"` sur le SVG ; icône porteuse de sens sans texte adjacent = `aria-label` sur le SVG.

**CSS complet d'`icons.css` (à copier verbatim)** :

```css
/* ============================================================
   NCF Icons · v2.0 · Feuille de styles utilitaires
   ============================================================
   À importer dans ton CSS global :
       @import url('./ncf-icons/icons.css');

   Ou en lien direct dans le HTML :
       <link rel="stylesheet" href="ncf-icons/icons.css">
   ============================================================ */

/* Variables de couleur (à reprendre dans ta charte globale si pas déjà fait) */
:root {
  --ncf-marine: #050D1D;
  --ncf-paper: #F7F4ED;
  --ncf-accent: #E8503F;
  --ncf-gold: #C9A961;
  --ncf-ink-soft: #4A5470;
}

/* ============================================================
   CLASSE DE BASE
   ============================================================ */

.ncf-icon {
  display: inline-block;
  vertical-align: middle;
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  /* La couleur de stroke suit la couleur du texte (currentColor) */
  color: var(--ncf-marine);
}

/* ============================================================
   TAILLES
   ============================================================ */

.ncf-icon--xs { width: 20px; height: 20px; }   /* Inline texte (minimum) */
.ncf-icon--sm { width: 24px; height: 24px; }   /* Bouton, nav */
.ncf-icon--md { width: 32px; height: 32px; }   /* Carte feature */
.ncf-icon--lg { width: 48px; height: 48px; }   /* Carte large */
.ncf-icon--xl { width: 64px; height: 64px; }   /* Hero */

/* ============================================================
   COULEURS
   ============================================================ */

.ncf-icon--marine { color: var(--ncf-marine); }
.ncf-icon--paper  { color: var(--ncf-paper); }   /* sur fond sombre */
.ncf-icon--accent { color: var(--ncf-accent); }  /* hover, focus */
.ncf-icon--gold   { color: var(--ncf-gold); }    /* premium */
.ncf-icon--soft   { color: var(--ncf-ink-soft); } /* désactivé */

/* ============================================================
   ÉTATS INTERACTIFS
   ============================================================ */

.ncf-icon--interactive {
  transition: color 0.3s ease, transform 0.3s ease;
  cursor: pointer;
}
.ncf-icon--interactive:hover {
  color: var(--ncf-accent);
  transform: translateY(-1px);
}

/* L'icône suit la couleur du lien parent au hover */
a:hover .ncf-icon,
button:hover .ncf-icon {
  color: var(--ncf-accent);
}

/* ============================================================
   COMPOSITION INLINE (icône + texte)
   ============================================================ */

.ncf-icon-text {
  display: inline-flex;
  align-items: center;
  gap: 0.6em;
}

.ncf-icon-text--left .ncf-icon { order: 0; }
.ncf-icon-text--right .ncf-icon { order: 2; }

/* ============================================================
   ACCESSIBILITÉ
   ============================================================ */

/* Les icônes décoratives doivent être ignorées par les lecteurs d'écran.
   Si l'icône est porteuse de sens (sans texte adjacent), ajouter aria-label sur le SVG.
   Par défaut on masque : */
.ncf-icon[aria-hidden="true"] {
  pointer-events: none;
}

/* Respect des préférences réduites */
@media (prefers-reduced-motion: reduce) {
  .ncf-icon--interactive {
    transition: none;
  }
  .ncf-icon--interactive:hover {
    transform: none;
  }
}
```

Note : sur le site Novances Évaluation, les variables `--ncf-*` ci-dessus servent uniquement de fallback. Les icônes héritent en pratique de `currentColor` du parent, donc de la palette institutionnelle du site (texte navy, accent bleu marine). Ne pas utiliser `--ncf-accent` (#E8503F, orange) comme couleur d'accent du site : c'est la palette interne de la librairie, pas celle de la charte.

### 4. Inventaire complet du sprite (36 icônes)

Les `id` ci-dessous sont ceux du sprite (`icons-sprite.svg#<id>`). Le fichier individuel correspondant est `svg/ncf-icon-{categorie}-{id}.svg`.

**Évaluation et méthodes** (`evaluation/`) :
- `balance` : balance d'évaluation
- `document` : rapport / livrable
- `methods` : trois méthodes (DCF, multiples, ANC)
- `chart` : courbe d'analyse
- `growth` : croissance / tendance
- `calculator` : calcul
- `data` : base de données
- `comparable` : comparable sectoriel
- `transmission` : transmission entre dirigeants
- `holding` : structure holding

**Process et livraison** (`process/`) :
- `clock` : délai
- `pdf` : téléchargement
- `signature` : signature
- `steps` : étapes
- `calendar` : calendrier
- `timeline` : timeline

**Valeur et garanties** (`value/`) :
- `seal` : opposable
- `lock` : confidentiel
- `independence` : indépendant
- `certification` : certification
- `quality` : qualité

**Équipe** (`team/`) :
- `conversation` : conseil
- `expert` : expert
- `meeting` : réunion
- `support` : support
- `phone` : téléphone
- `mail` : email / message
- `family` : famille / lignée (arbre généalogique)
- `staff` : salariés / effectif

**Business** (`business/`) :
- `company` : entreprise
- `finance` : finance (€)
- `contract` : contrat
- `location` : adresse / localisation
- `tower` : autre entreprise / tour corporate

**Navigation** (`nav/`) :
- `search` : recherche
- `arrow` : flèche d'action

### 5. Portage vers un autre site

**Option A (recommandée) : copier le dossier tel quel.** Copier l'intégralité de `assets/ncf-icons/` (sprite, dossier `svg/`, `icons.css`, les deux fichiers markdown, `preview.html`) dans le nouveau projet, lier `icons.css` dans le `<head>`, et référencer le sprite via `<use href=".../ncf-icons/icons-sprite.svg#nom">`. Ajuster au besoin les variables `--ncf-*` de `:root` dans `icons.css` pour les aligner sur la palette du nouveau site (les icônes suivront automatiquement grâce à `currentColor`).

**Option B : recréer des icônes au même style.** Si le dossier n'est pas disponible, reproduire le système à partir des règles de la section 2 : viewBox 24×24, trait 1.5, linecap/linejoin round, `stroke="currentColor"`, `fill="none"`, zone utile 16×16 (de 4,4 à 20,20), géométrie sur entiers et demi-pixels, angles 0°/45°/90°, 2 à 5 éléments, et surtout les deux équerres signature en coins opposés (trait 1, segments en L de 3 px) :

```xml
<path d="M 1 4 L 1 1 L 4 1" stroke-width="1"/>
<path d="M 20 23 L 23 23 L 23 20" stroke-width="1"/>
```

Sans ces équerres, l'icône n'appartient pas au système. Pour générer une nouvelle icône avec un LLM, utiliser le prompt template de la section 11 d'`ICON_GUIDELINES.md` (reproduit en synthèse dans la section 2 ci-dessus : structure, signature obligatoire, zone utile, géométrie, métaphore, commentaire d'en-tête `<!-- NCF Icon · {cat}/{nom} · v2.0 · 24×24 · moderne + équerres -->`). Chaque nouvelle icône s'ajoute au sprite en l'entourant d'une balise `<symbol id="...">`, puis se vérifie visuellement dans `preview.html`.

Règles d'évolution : partir d'un besoin réel dans une page (pas d'icône spéculative), refuser les doublons, mettre à jour la démo HTML à chaque ajout, incrémenter la version dans le commentaire si on modifie une icône existante, documenter la métaphore retenue.

---

## 8. Patterns de pages, héros, imagerie et voix éditoriale

Police unique : `Inter` (Google Fonts, graisses chargées 400;500;600;700;800;900). Largeur de contenu standard : `.section-inner { max-width: 1200px; padding: 0 2rem; }` (1280px pour les grilles larges de la home et des publications, 1020px pour les articles, 820px pour FAQ et CTA finaux).

### 1. Anatomie des héros

Tous les héros partagent trois constantes :
- **Padding-top compensant la navbar fixe** (68px de haut) : `118px` (home, tarifs) ou `138px` (pages cibles, ressources) ou `145px` (articles).
- **Fond construit en deux pseudo-éléments** : `::before` porte des `radial-gradient` d'accent très dilués ; sur la home et les pages cibles, `::after` ajoute une grille de points (`radial-gradient(circle, ... 1px, transparent 1px)` avec `background-size: 28px 28px`) masquée par une ellipse (les héros ressources, tarifs et articles n'ont que le `::before`). C'est la signature visuelle des héros du site.
- **Un span `.accent` dans le h1** qui isole le segment clé de la promesse (home, pages cibles, ressources, tarifs ; jamais dans les h1 d'articles).

#### Hero home (split 2 colonnes)

Page d'accueil uniquement (`#hero`, `assets/css/pages/home.css`). Grille effective `1fr 540px`, `gap: 2rem` (règle `body:has(.cas-mini-grid--rich)` ; base surchargée : `1.2fr 0.8fr`, `gap: 4rem`), conteneur `.hero-inner` `max-width: 1400px`, `padding: 1.5rem 2rem`, fond `var(--bg-base)` (surcharge `!important`) rehaussé de deux halos radiaux (`--accent-a-10` en haut à gauche, `--accent-a-06` en bas à droite).

Colonne gauche, dans l'ordre :
1. **Eyebrow pill** : `.hero-eyebrow` en capsule (`color: var(--accent-deeper); background: var(--accent-a-08); border: 1px solid var(--accent-a-22); padding: 6px 14px; border-radius: 100px;` sur une base `font-size: 0.72rem; font-weight: 600; letter-spacing: 0.18em; text-transform: uppercase;`).
2. **H1** : `clamp(2rem, 3.2vw, 3rem)`, `font-weight: 700`, `line-height: 1.08`, `letter-spacing: -0.032em`, couleur `var(--text-strong)`. Le `.accent` est en texte dégradé : `background: linear-gradient(135deg, var(--accent-deep) 0%, var(--accent) 100%); background-clip: text; -webkit-text-fill-color: transparent;` avec un soulignement animé qui se trace :

```css
.hero-h1 .accent::after {
  content: '';
  position: absolute; left: 0; right: 0; bottom: 0.04em;
  height: 0.08em;
  background: var(--blue);
  opacity: 0.25;
  transform: scaleX(0); transform-origin: left;
  animation: hero-accent-draw 1s 0.6s cubic-bezier(.2,.8,.2,1) forwards;
}
@keyframes hero-accent-draw { to { transform: scaleX(1); } }
@media (prefers-reduced-motion: reduce) {
  .hero-h1 .accent::after { animation: none; transform: scaleX(1); }
}
```

Note : une seconde règle de home.css surcharge le rendu final du trait : `background: linear-gradient(90deg, var(--accent) 0%, var(--accent-bright) 70%, transparent 100%)`, `opacity: 1`, `height: 0.055em`.

3. **Sous-titre** : `1.08rem`, `line-height: 1.6`, `margin-top: 1.4rem`, couleur `var(--text-2)`.
4. **Router visuel** : 4 icônes SVG animées (une par persona) liées aux pages cibles, plutôt que des boutons.
5. **Ligne de réassurance** `.hero-trust-inline` : `0.78rem; font-weight: 500`, 3 items avec coche SVG verte (`stroke-width: 2.8`) séparés par des points de 3px ("PME 1 – 10 M€ de CA", "Premier échange confidentiel", "Cabinet basé à Lyon").

Colonne droite : **bento équipe** de 5 cartes (`.hv-bento`, grille `1.4fr 1fr 1fr` × 2 rangées, `aspect-ratio: 1.45 / 1`, `max-width: 540px`, `gap: 10px`, `border-radius: 14px`), 4 portraits + 1 tuile marque en dégradé accent. Entrée en cascade pilotée par une variable inline `style="--d:0.05s"` (puis 0.15s, 0.25s, 0.35s, 0.45s) :

```css
@keyframes hv-rise {
  from { opacity: 0; transform: translateY(14px) scale(0.985); }
  to   { opacity: 1; transform: translateY(0)   scale(1); }
}
.hv-bento-card {
  opacity: 0;
  animation: hv-rise 0.75s cubic-bezier(.2,.8,.2,1) var(--d, 0s) forwards;
}
```

Intention : la home vend une promesse (gauche) incarnée par des humains (droite), jamais par une illustration abstraite.

#### Hero des pages cibles (entrepreneurs, experts-comptables, avocats, notaires)

Pattern partagé `.parcours-hero` (`assets/css/pages/parcours.css`). Une seule colonne alignée à gauche, pas de visuel. La couleur d'accent est pilotée par une classe persona sur `<body>` (`<body class="parcours-page is-entrepreneurs">`) qui définit `--persona`, `--persona-soft`, `--persona-rgb`.

```css
.parcours-hero {
  padding: 138px 0 4.5rem;
  position: relative; overflow: hidden; isolation: isolate;
  background: var(--navy-deep);
}
.parcours-hero::before {
  content: '';
  position: absolute; inset: 0; z-index: -1;
  background:
    radial-gradient(900px 600px at 15% 20%, rgba(var(--persona-rgb) / 0.10), transparent 60%),
    radial-gradient(700px 500px at 85% 80%, rgba(0, 184, 255, 0.04), transparent 65%);
}
.hero-s-eyebrow {
  font-size: 0.72rem; font-weight: 700; letter-spacing: 0.2em;
  text-transform: uppercase; color: var(--persona);
  display: inline-flex; align-items: center; gap: 12px;
}
.hero-s-eyebrow::before {
  content: ''; width: 32px; height: 2px;
  background: linear-gradient(90deg, var(--persona), transparent);
}
.hero-s-h1 {
  font-size: clamp(2rem, 4.6vw, 3.4rem);
  font-weight: 800; line-height: 1.08; letter-spacing: -0.028em;
  color: var(--text-strong); max-width: 960px; margin-top: 1.1rem;
}
.hero-s-h1 .accent { color: var(--persona); position: relative; }
.hero-s-h1 .accent::after {
  content: '';
  position: absolute; left: 0; right: 0; bottom: 0.08em;
  height: 0.32em;
  background: rgba(var(--persona-rgb) / 0.18);
  z-index: -1; border-radius: 2px;
}
.hero-s-sub {
  font-size: 1.08rem; color: var(--ink-dim); line-height: 1.7;
  max-width: 720px; margin-top: 1.35rem;
}
.hero-s-ctas { display: flex; gap: 1rem; margin-top: 2rem; flex-wrap: wrap; }
.hero-s-reassure {
  margin-top: 1.4rem; font-size: 0.82rem; color: var(--muted);
  display: inline-flex; align-items: center; gap: 10px;
}
```

Ordre canonique : eyebrow persona, h1 avec `.accent` surligné façon stabilo (le `::after` de `0.32em` derrière le texte), sous-titre, deux CTA (`.btn-primary.btn-magnetic` + `.btn-outline`), ligne de réassurance avec icône bouclier : "Rappel sous 24 h ouvrées · Cadrage sans engagement".

#### Héros centrés (ressources, tarifs)

Pages de catalogue : texte centré, pas de CTA dans le hero (le contenu EST l'appel).
- `/ressources/` (`#hero-ressources`) : `padding: 138px 0 2.5rem`, eyebrow sans tiret (`inline-block`, `0.78rem`), h1 `clamp(2.2rem, 5vw, 3.8rem); font-weight: 700; line-height: 1.05`, sous-titre centré `max-width: 720px`.
- `/tarifs/` (`#hero-tarifs`) : fond `#fff` + un seul radial accent, eyebrow encadré de deux tirets (`::before` ET `::after` de `24px × 2px`), h1 `clamp(2rem, 3vw, 2.8rem); font-weight: 900`.

#### Hero d'article

`.article-hero` (`assets/css/pages/article.css`), `padding: 145px 0 0`, conteneur `1020px`. Séquence stricte :
1. Fil d'Ariane (`0.78rem`, séparateur `›`) : Accueil › Publications › Thème.
2. Tag thématique `.article-tag` : `0.72rem; font-weight: 800; letter-spacing: 0.16em; uppercase`, couleur `var(--article-hue)` (pilotée par classe body `theme-transmission`, `theme-litiges`, `theme-croissance`, `theme-valorisation`, `theme-fiscalite`), précédé d'un tiret dégradé `22px × 2px`.
3. H1 : `clamp(2rem, 4.5vw, 4rem); line-height: 1.05; letter-spacing: -0.035em; max-width: 850px`.
4. Chapeau `.article-standfirst` : `1.06rem; line-height: 1.75; max-width: 780px`.
5. Méta : "Par **Frédéric Lemonnier** · 6 min de lecture · Mis à jour le 6 mai 2026" (`0.85rem`, séparateur `·`).
6. Image de couverture `.article-cover` : `height: min(46vw, 460px); min-height: 250px; border-radius: 14px; border: 1px solid var(--border)`, image en `object-fit: cover`.

### 2. Structure type d'une page

#### Squelette commun à toutes les pages

```
navbar fixe (glass, 68px) + menu mobile
hero
[sections de contenu]
CTA final
footer (4 colonnes : marque + Moore Global / Pour qui ? / Cabinet / Publications)
```

Chaque page charge `global.css` + un seul CSS de page (`assets/css/pages/<page>.css`), `site.js` commun, et un JS de page optionnel.

#### Enchaînements par type de page

**Home** (narration enjeu → solution → preuve → action) :
1. Hero (promesse + équipe)
2. "Pour qui ?" : 4 cartes personas numérotées 01 à 04
3. "Enjeu" : manifeste centré (`max-width: 880px`, texte seul)
4. "La solution" : piliers en grille (1 pilier groupe pleine largeur + 3 piliers)
5. "Notre livrable" : démo du rapport (iframe coverflow)
6. "Références" : marquee de logos clients (boucle infinie, `animation: scroll-x 40s linear infinite`, contenu dupliqué)
7. "Avis clients" : 4 cartes témoignages Google (avatar initiales + 5 étoiles `#FBBF24` / étoile vide `#E5E7EB`)
8. "Prescripteurs" : carte teaser partenaires
9. "Publications" : 3 cartes articles
10. "Contact" : CTA final en 2 colonnes (portrait de l'associé + coordonnées à gauche, formulaire à droite)

**Page cible persona** (entrepreneurs, etc.) :
1. Hero persona
2. "Pourquoi nous" : composant autocycle (3 panneaux à défilement automatique)
3. "Notre méthode" : cheminement par les outils (5 étapes reliées par une ligne avec reflet animé `ch-sheen 3.2s ease-in-out infinite`) + encart bases de données + encart Teams/téléphone
4. Avis Google (1 témoignage en carte large)
5. "Notre groupe" : bandeau Novances (texte + 5 cartes statistiques chiffrées)
6. "Questions fréquentes" : FAQ en `<details>/<summary>` (croix animée en `::after`, max-width 820px)
7. CTA final centré (eyebrow "Prochaine étape", h2 avec `.accent` persona, 2 boutons, ligne d'engagement)

Le pattern timeline `.process-timeline` (pastilles numérotées 72px, bordure `2px solid var(--persona)`, ligne verticale dégradée entre les étapes) existe dans `parcours.css` mais est actuellement masqué (`#process { display: none; }`), de même que le cas d'école `.case-panel`. Ils restent disponibles comme patterns.

**Ressources** : hero centré → filtres en pills (`border-radius: 999px`, état actif fond `var(--text-strong)` texte blanc) → grille 3 colonnes avec 1 carte "feature" pleine largeur en 2 colonnes (image | texte) → section CTA finale centrée sur fond `var(--bg-elevated)`.

**Article** : hero → corps en 2 colonnes `minmax(0, 1fr) 260px`, contenu limité à `68ch`, aside sticky (`top: 125px`) avec cartes "À retenir", "À lire aussi", "Sources utiles" → encart CTA en fin de corps (`.article-cta`). Les h2 du corps sont séparés par un filet supérieur (`border-top: 1px solid var(--line-1); padding-top: 2.2rem`). Encart `.article-callout` : `border: 1px solid var(--accent-a-22); border-left: 3px solid var(--article-hue); background: var(--accent-a-08); border-radius: 10px`.

#### Alternance de fonds et rythme

Le rythme vertical vient de l'alternance de fonds très proches (jamais de contraste brutal) :
- `var(--bg-base)` `#EAF0F8` : fond par défaut (alias legacy `--navy-deep`).
- `var(--bg-elevated)` `#F4F7FC` : sections "remontées".
- `#fff` : héros tarifs (le héros home est en `var(--bg-base)` via une surcharge `!important`).
- Transitions douces par dégradés : `linear-gradient(180deg, var(--navy-deep) 0%, var(--bg-elevated) 100%)` (sections avis, ressources de la home).
- Sur les pages cibles : `.sec-dark { background: var(--navy-deep); }`, `.sec-soft { background: linear-gradient(180deg, var(--navy-deep), var(--bg-deep) 50%, var(--navy-deep)); }`, `.sec-raised { background: radial-gradient(800px 500px at 50% 0%, rgba(var(--persona-rgb) / 0.04), transparent 65%), var(--navy-deep); }`.

Chaque section suit le même en-tête :

```css
.section { padding: 5rem 0; position: relative; }   /* 3.5rem 0 à ≤640px */
.section-inner { max-width: 1200px; margin: 0 auto; padding: 0 2rem; }

.section-eyebrow {
  font-size: 0.7rem; font-weight: 600; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--accent-deep); margin-bottom: 0.75rem;
  display: flex; align-items: center; gap: 8px;
}
.section-eyebrow::before {
  content: ''; width: 22px; height: 2px;
  background: linear-gradient(90deg, var(--accent), transparent);
}
.section-title {
  font-size: clamp(1.55rem, 2.6vw, 2.3rem);
  font-weight: 700; line-height: 1.15; letter-spacing: -0.025em;
  color: var(--text-strong);
}
.section-sub {
  font-size: 0.95rem; color: var(--text-2); line-height: 1.75;
  margin-top: 0.875rem; max-width: 560px;
}
```

L'en-tête est aligné à gauche par défaut, centré pour les sections de preuve sociale (via `style="text-align:center"` et `style="justify-content:center"` inline sur l'eyebrow).

Apparition au scroll : classes `.rv` (+ `.d1` à `.d4` pour le décalage), activées en `.in` par `site.js` :

```css
.rv { opacity: 0; transform: translateY(20px); transition: opacity 0.7s ease, transform 0.7s ease; }
.rv.in { opacity: 1; transform: none; }
.rv.d1 { transition-delay: 0.08s; }
.rv.d2 { transition-delay: 0.16s; }
.rv.d3 { transition-delay: 0.24s; }
.rv.d4 { transition-delay: 0.32s; }
@media (prefers-reduced-motion: reduce) {
  .rv { opacity: 1; transform: none; transition: none; }
}
```

Note : le hero de la home et les cartes Publications sont volontairement affichés sans reveal (décision récente du projet) ; réserver `.rv` aux sections sous la ligne de flottaison.

### 3. Traitement des images

**Formats réellement utilisés** : `.jpg` pour toutes les photos (portraits équipe, visuels d'articles), `.png` pour les logos (marque, clients, outils Microsoft, Moore Global), un seul `.avif` (`logo-novances.avif`). Pas de WebP. Lazy-loading systématique (`loading="lazy" decoding="async"`) sauf l'image LCP du hero (`fetchpriority="high"`) et la cover d'article (`loading="eager"`).

**Visuels d'articles** : nommage `assets/img/articles/<slug>.jpg` (+ `<slug>-body{n}.jpg` pour le corps). Ratios :
- Cartes Publications : `aspect-ratio: 16 / 10`.
- Cartes teaser home : `aspect-ratio: 16 / 9`.
- Cover d'article : bandeau `height: min(46vw, 460px)`.
- Toujours `object-fit: cover`, jamais de déformation.

**Traitement signature des images de cartes** : légère désaturation au repos qui se ravive au survol, plus zoom lent, plus voile navy (scrim) pour asseoir le tag :

```css
.res-img img {
  filter: saturate(0.85) contrast(1.05);
  transition: transform 0.45s cubic-bezier(.2,.8,.2,1), filter 0.3s;
}
.res-card:hover .res-img img { transform: scale(1.05); filter: saturate(1) contrast(1.08); }
.res-img::after {
  content: ''; position: absolute; inset: 0;
  background:
    linear-gradient(to top, rgba(5, 13, 29, 0.42), transparent 58%),
    linear-gradient(135deg, rgba(10, 31, 61, 0.28), rgba(5, 13, 29, 0.08));
}
```

(Variante Publications : zoom `scale(1.04)` en `0.5s cubic-bezier(0.16, 1, 0.3, 1)`, sans filtre.)

**Radius** : 14px pour les cartes et covers, 18px pour les grands panneaux (case-panel, partners-card, form-card ; les cartes du bento sont à 14px), 10px pour les figures dans le corps d'article et les logos clients.

**Portraits** : photos jpg cadrées `object-position: center 20%` dans le bento ; portrait CTA `104px × 128px; border-radius: 14px; border: 3px solid #fff; box-shadow: 0 18px 36px -18px rgba(6, 24, 56, 0.45)`.

**Logos clients** : posés sur pastilles blanches (`background: rgba(255, 255, 255, 0.92); border-radius: 10px; height: 72px`, image `max-height: 44px; max-width: 130px`) dans un marquee masqué en fondu latéral (`mask-image: linear-gradient(90deg, transparent 0, #000 100px, #000 calc(100% - 100px), transparent)`).

**Tags sur image** : capsule en haut à gauche (`top: 14px; left: 14px; font-size: 0.65rem; font-weight: 700; letter-spacing: 0.08em; uppercase; padding: 4px 10px; border-radius: 100px; backdrop-filter: blur(8px)`).

### 4. Ton éditorial appliqué à l'UI

Cible : dirigeants de PME. Posture : expert posé et pédagogue, jamais "agence".

- **Casse des titres : sentence case strict**, jamais de Title Case ni de tout-majuscules (les majuscules sont réservées aux eyebrows et micro-labels). Les h1/h2 se terminent très souvent par un **point final**, y compris courts : "Parler à un expert.", "Ils nous ont fait confiance.", "Nous sommes des experts de l'évaluation.". C'est un marqueur fort de la voix.
- **Le `.accent` du h1 porte le bénéfice**, pas un mot décoratif : "besoin d'une évaluation.", "opposable et acceptée.", "transparents et lisibles.", "sans engagement.".
- **Eyebrows** : 1 à 3 mots, nominaux, parfois interrogatifs : "L'enjeu", "Pour qui ?", "La solution", "Notre livrable", "Références", "Avis clients", "Prescripteurs", "Publications", "Pourquoi nous", "Notre méthode", "Cas d'école", "Notre groupe", "Questions fréquentes", "Prochaine étape", "Contact".
- **CTA courts (2 à 5 mots)**, verbe d'action à l'infinitif ou première personne : "Parler à un expert" (CTA principal, répété navbar + héros + CTA finaux), "Découvrir la méthode", "Lire l'article", "Voir toutes les publications", "Passer par le formulaire", "Je souhaite être rappelé", "Cadrer ma transmission". Le CTA primaire embarque presque toujours la flèche SVG inline : `width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"` avec `path d="M5 12h14M12 5l7 7-7 7"`.
- **Adressage direct au "vous"**, titres qui nomment le lecteur : "Vous êtes dirigeant d'entreprise et…", "Vous êtes entrepreneur", "Travaillons-nous avec vos conseils ?".
- **Pédagogie immédiate** : tout terme technique est expliqué dans la phrase, entre parenthèses ou par apposition : "la rentabilité future actualisée (méthode DCF)", "réserve d'usufruit (vous donnez la propriété mais gardez les revenus)", "Pacte Dutreil, dispositif qui permet une exonération de 75 % des droits de mutation…", "le ROCE, la rentabilité des capitaux employés".
- **Réassurance ritualisée** : la triade "Rappel sous 24 h ouvrées · Échange confidentiel · Sans engagement" revient sous chaque CTA. Chiffres précis plutôt qu'adjectifs : "PME 1 – 10 M€ de CA", "+8 000 clients accompagnés", "à partir de 4 000 € HT".
- **Ponctuation** : séparateur point médian `·` pour toutes les métadonnées ("Article · Avril 2026", "Associé · Cabinet NCF", "6 min de lecture"), guillemets français « » pour les citations, jamais de tiret cadratin (préférer parenthèses, virgules, deux-points). Espaces insécables devant `?`, `:` et dans les nombres ("+8 000", "40 M€").
- **Vocabulaire de marque** : "opposable", "défendable", "argumenté", "indépendant", "lisible", "vos conseils" (pour désigner notaire/avocat/expert-comptable). Éviter "tient face au contrôle" et "résister au contrôle" dans les nouveaux contenus.

### 5. Où vivent les styles (inline vs fichiers)

**Aucune page publique n'embarque de bloc `<style>`** : tout vit dans `assets/css/global.css` (chrome + tokens + sections + boutons + footer + reveal) et `assets/css/pages/<page>.css`. Le commentaire d'en-tête de `global.css` ("Spécificités page = inline `<style>`") est obsolète : ne pas le reproduire. Les seuls fichiers avec `<style>` sont des artefacts hors pages publiques : `assets/embeds/coverflow_rapport.html` (iframe de démo du rapport), `assets/ncf-icons/preview.html` (non déployé en pratique) et les dumps LinkedIn bruts de `ressources/Linkedin/*.html` (non indexés).

En revanche, des **attributs `style=""` ponctuels** servent de micro-utilitaires dans le HTML (23 occurrences sur la home), à reproduire tels quels :
- Centrage d'en-têtes de section : `style="text-align:center; max-width:680px; margin:0 auto;"` sur le wrapper et `style="justify-content:center;"` sur `.section-eyebrow`.
- Délais d'animation du bento : `style="--d:0.05s;"` (0.05 / 0.15 / 0.25 / 0.35 / 0.45).
- Couleurs d'avatars de témoignages (initiales sur fond plein) : `style="background:#1A56DB;"`, `#047857`, `#BE185D`, `#B45309` (seuls écarts tolérés à la palette, car ils imitent les avatars Google).
- Honeypot du formulaire : `style="position:absolute; left:-9999px; opacity:0;"`.
- Grille tarifaire : `style="display: contents;"` sur les rangées de la matrice.

---

## 9. Checklist d'application à un nouveau site

Ordre de mise en œuvre recommandé pour appliquer cette charte à un autre projet :

1. **Fondations** : créer le CSS global, y coller le bloc `:root` complet (section 1), le reset et les styles de base (body avec halo, scrollbar, focus-visible, `:target`).
2. **Police** : ajouter les deux `preconnect` et le lien Google Fonts Inter (graisses 400 à 900) dans le `<head>` de chaque page (section 2).
3. **Chrome** : intégrer la navbar glass et le footer en dégradé (HTML + CSS complets en section 3), puis le JS commun (navbar scrolled, burger, reveal, smooth scroll, boutons magnétiques : section 6).
4. **Composants** : boutons (`.btn-primary` / `.btn-outline` / `.btn-ghost` / `.nav-cta`), formulaire, card canonique et ses variantes (sections 4 et 5).
5. **Icônes** : copier le dossier `assets/ncf-icons/` complet depuis le site source, ou recréer des icônes selon les règles de la section 7 (équerres signature obligatoires).
6. **Pages** : construire chaque page selon les patterns de la section 8 (hero avec padding-top compensant la navbar, sections en `5rem 0`, en-tête eyebrow + titre + sous-titre, alternance de fonds proches, CTA final, footer).
7. **Motion** : poser `.rv` sur les en-têtes de section uniquement (pas sur les grilles de cards de contenu), vérifier chaque opt-out `prefers-reduced-motion`.
8. **Contrôle final** :
   - aucune couleur hors tokens (rechercher les hex orphelins dans le CSS) ;
   - contraste AA : texte accent et fonds de CTA en `--accent-deeper`, jamais `--accent` ;
   - focus clavier visible sur tous les éléments interactifs ;
   - titres en sentence case (souvent terminés par un point), CTA de 2 à 5 mots, métadonnées séparées par « · », aucun tiret cadratin dans les contenus ;
   - mobile : boutons pleine largeur sous 640px, navbar 62px, sections `3.5rem 0`.

## Sources

Document généré depuis le dépôt du site Novances Évaluation (NCF-Test-Website), le 11 juin 2026. Fichiers sources : `assets/css/global.css`, `assets/css/pages/*.css`, `assets/css/components/autocycle.css`, `assets/js/site.js`, `assets/js/autocycle.js`, `assets/js/pages/*.js`, `assets/ncf-icons/*`, et les HTML des pages publiques. En cas de doute ou d'évolution du site, ces fichiers font foi.
