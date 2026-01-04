# Plan d’adaptation SVG → LVGL 8.3 (rendu fidèle + animation)

Document explicatif et démonstratif, non normatif.

## A) Socle commun (factorisé)

### A1) Constat LVGL

* Le decodeur `lv_svg` (si utilisé) **ne joue pas** les animations SMIL (`animate`, `animateTransform`).
* Le support SVG (gradients/strokes/AA) dépend du build → si tu veux **100% identique**, la voie robuste est **raster par calques** + animation LVGL.

### A2) Stratégie “100%” (référence)

1. **Découper** l’icône en calques logiques (ce qui doit bouger séparément).
2. **Rasteriser** chaque calque en PNG (alpha), **sans animation SMIL**.
3. Convertir en assets LVGL (`lv_img_conv`, `CF_TRUE_COLOR_ALPHA` ou format cible).
4. Recomposer en runtime (`lv_img` superposés dans un conteneur taille icône).
5. Refaire l’animation via `lv_anim` (angle, position, opacité, éventuellement swap de frames).

### A3) Tailles / packs

* Exporter plusieurs tailles (ex: 64 / 96 / 128) pour éviter les resizes runtime.
* Un pack = `*_64.c` (ou `*_96.c`, etc.) + un `create_icon(parent, size)`.

### A4) Règles d’or (qualité)

* PNG plein cadre = composition simple (tout à `0,0`) + animations uniquement sur les calques animés.
* Pivot/offset: **figer** une convention (viewBox → pixels) et la garder pour tous les exports.
* Si un transform SVG n’est pas supportable en LVGL (ex: scale non uniforme), **pré-baker** des frames PNG et animer le **swap** (opacité/visibilité).

### A5) Livrables standards

* Assets: `*.c/*.h` par calque et par taille.
* Code: `weather_icon_<name>.c/.h` (composition + anims).

---

## Exemples de référence

## B) Icônes traitées

### B1) partly-cloudy-day-rain.svg

**Analyse SVG**

* `viewBox`: `0 0 64 64`
* Calques logiques:

  * Soleil + rayons (circle + path)
  * Nuage (path)
  * 3 gouttes (3× line)
* Peinture:

  * 3 gradients principaux (soleil/nuage/goutte) + réutilisation via `xlink:href`
  * strokes sur rayons/contours
* Animations SMIL:

  * Rayons: rotation `0→360` autour `(19,24)` sur **45s** (loop)
  * Gouttes: translate `(+1,-5) → (-2,+10)` sur **0.7s** + opacité `0→1→1→0` avec déphasage

**Adaptation LVGL**

* Raster calques: `sun.png`, `cloud.png`, `drop.png` (une goutte), puis 3 instances.
* Animations:

  * soleil: `lv_img_set_pivot()` + `lv_img_set_angle()` (0..3600) sur 45000ms loop.
  * gouttes: position + opacity sur 700ms loop, déphasées (0 / 200 / 400ms).

---

### B2) raindrop.svg

**Analyse SVG**

* `viewBox`: `0 0 64 64`
* Primitives:

  * 1× `path` (goutte)
* Peinture:

  * `linearGradient id=a` (bleu → bleu → bleu foncé) + `stroke` `#2885c7` (0.5)
* Animation SMIL:

  * `animateTransform` type **scale** avec valeurs: `1 1; 1 0.9; 1 1`
  * durée **5s**, `calcMode=spline` (ease in/out), loop

**Point dur LVGL**

* Le scale est **non uniforme** (X=1, Y=0.9). LVGL 8.x ne fournit pas un scale X/Y séparé pour `lv_img` (zoom uniforme uniquement).

**Adaptation LVGL (100% fidèle)**

* Rasteriser **2 frames** (plein cadre 64×64, même alignement):

  * `drop_norm.png` (scale 1,1)
  * `drop_squash.png` (scale 1,0.9 appliqué au path avant export)
* Composition:

  * 2 objets `lv_img`: `img_norm`, `img_squash` superposés
* Animation:

  * Crossfade (opacité) pour reproduire la courbe `1→0.9→1`:

    * `img_norm`: opa 255 → 0 → 255
    * `img_squash`: opa 0 → 255 → 0
  * Timing: 5000ms loop.
  * Easing: utiliser `lv_anim_set_path_cb(&a, lv_anim_path_ease_in_out)` (approx spline). Si besoin, affiner via une fonction path custom.

**Adaptation LVGL (plus simple, moins exacte)**

* Un seul PNG + `lv_img_set_zoom()` (zoom uniforme) autour de ~0.95 pour simuler le “pulse”.
* Visuellement proche mais pas identique (car X devrait rester à 1).

---

## B3) barometer.svg

**Analyse SVG**

* `viewBox`: `0 0 64 64`
* Primitives:

  * Cercle principal (corps du baromètre)
  * Arc / aiguille (path)
  * Détails internes (traits, cercle central)
* Peinture:

  * Dégradés radiaux/linéaires (fond métallique)
  * Strokes fins pour graduations
* Animation SMIL:

  * Rotation de l’aiguille autour du centre (pression variable)

**Adaptation LVGL (factorisée)**

* Raster calques:

  * `dial.png` (fond + graduations, statique)
  * `needle.png` (aiguille seule, fond transparent)
* Composition:

  * conteneur 64×64
  * `img_dial` en base
  * `img_needle` au-dessus
* Animation:

  * `lv_img_set_pivot(img_needle, cx, cy)` (centre du cadran)
  * `lv_img_set_angle()` piloté par `lv_anim` ou valeur runtime (pression → angle)
  * Option: animation douce avec `lv_anim_path_ease_in_out`

**Notes fidélité**

* Dégradés complexes → raster obligatoire pour rendu strict.
* Aiguille séparée = animation parfaite sans artefact.

---

## B4) clear-day.svg

**Analyse SVG**

* `viewBox`: `0 0 64 64`
* Primitives:

  * Disque central (soleil)
  * Rayons multiples (paths)
* Peinture:

  * Dégradé radial/linéaire chaud (jaune → orangé)
  * Strokes nets sur les rayons
* Animation SMIL:

  * Rotation continue des rayons autour du centre (cycle long, fluide)

**Adaptation LVGL (factorisée)**

* Raster calques:

  * `sun_core.png` (disque seul)
  * `sun_rays.png` (rayons seuls, fond transparent)
* Composition:

  * conteneur 64×64
  * `img_sun_core` (statique)
  * `img_sun_rays` (au-dessus)
* Animation:

  * `lv_img_set_pivot(img_sun_rays, cx, cy)` (centre exact)
  * `lv_img_set_angle()` animé de `0→3600` (dixièmes de degré)
  * Durée longue (ex: 30–60s) + loop infinie pour un mouvement continu non perceptible

**Notes fidélité**

* Dégradés et glow → raster obligatoire pour éviter pertes visuelles.
* Séparation core/rays évite toute déformation du disque central.

---

## B5) thunderstorms-day.svg

**Analyse SVG**

* `viewBox`: `0 0 64 64`
* Primitives:

  * Soleil partiel (disque + rayons)
  * Nuage principal (path)
  * Éclair (path polygonal)
  * Gouttes / pluie (lines ou paths)
* Peinture:

  * Dégradés chauds (soleil)
  * Dégradés froids/gris (nuage)
  * Couleur franche jaune/orange pour l’éclair
  * Strokes nets, contraste élevé
* Animations SMIL (typiques de cette icône):

  * Rotation lente des rayons (comme clear-day)
  * Apparition / disparition rapide de l’éclair (flash)
  * Chute cyclique des gouttes (translate + opacity)

**Décomposition en calques (factorisée)**

* `sun_core.png`
* `sun_rays.png`
* `cloud.png`
* `lightning.png`
* `rain_drop.png` (une seule goutte, instanciée N fois)

**Adaptation LVGL (100% fidèle)**

* Composition:

  * conteneur 64×64
  * ordre Z: soleil core → soleil rays → nuage → pluie → éclair
* Animations:

  * Soleil: rotation des rayons identique à **B4** (30–60s loop)
  * Pluie: même pattern que **B1** (translate Y + opacity, 700ms, déphasée)
  * Éclair:

    * animation d’opacité brutale: 0 → 255 → 0
    * durée courte (80–150ms)
    * déclenchement pseudo-aléatoire via timer LVGL (ex: toutes 2–5s)
    * option double-flash (255→0→255→0) pour réalisme

**Notes fidélité / pièges**

* L’éclair ne doit jamais être interpolé en position → uniquement opacity (sinon flou).
* Les gouttes doivent rester derrière l’éclair pour conserver la hiérarchie visuelle.
* Le soleil partiel ne doit pas "tourner" avec le nuage → calques strictement séparés.

---

## B6) starry-night.svg

**Analyse SVG**

* `viewBox`: `0 0 64 64`
* Primitives:

  * Disque lune (circle/path)
  * Étoiles multiples (small paths / circles)
* Peinture:

  * Dégradé froid lunaire (gris/bleuté)
  * Étoiles blanches/jaunes sans stroke complexe
* Animations SMIL (usuelles pour ce type d’icône):

  * Scintillement des étoiles (opacity pulsée)

**Décomposition en calques (factorisée)**

* `moon.png` (statique)
* `star.png` (une étoile générique, instanciée N fois)

**Adaptation LVGL (100% fidèle)**

* Composition:

  * conteneur 64×64
  * `img_moon` en base
  * `img_star[i]` instanciées avec positions fixes
* Animations:

  * étoiles: animation d’opacité douce (ex: 0.4 → 1 → 0.4)
  * durées différentes par étoile (ex: 2s, 3.5s, 5s) pour éviter la synchro
  * easing `ease_in_out`

**Notes fidélité**

* Pas de translation des étoiles (sinon effet "neige").
* Décalage de phase obligatoire pour un rendu naturel.

---

## B7) partly-cloudy-night-snow.svg

**Analyse SVG**

* `viewBox`: `0 0 64 64`
* Primitives:

  * Lune partielle
  * Nuage
  * Flocons (paths ou cercles)
* Peinture:

  * Dégradés froids (lune)
  * Gris doux (nuage)
  * Blanc/cyan (neige)
* Animations SMIL (typiques):

  * Scintillement très léger de la lune (optionnel)
  * Chute verticale des flocons avec fade in/out

**Décomposition en calques (factorisée)**

* `moon.png`
* `cloud.png`
* `snowflake.png` (un flocon générique)

**Adaptation LVGL (100% fidèle)**

* Composition:

  * ordre Z: lune → nuage → neige
* Animations:

  * neige:

    * translation Y lente (plus lente que la pluie)
    * légère oscillation X possible (optionnelle, faible amplitude)
    * opacity: 0 → 255 → 255 → 0
    * durées longues (1.2s–2s)
    * déphasage entre flocons
  * lune: statique (ou très léger pulse d’opacité <5%)

**Notes fidélité / différenciation pluie vs neige**

* Vitesse divisée par ~2 par rapport à la pluie.
* Opacité plus douce, pas d’impact visuel brutal.

---

## B8) dust-day.svg

**Analyse SVG**

* `viewBox`: `0 0 64 64`
* Primitives:

  * Soleil (circle + rayons en path), centré
  * 2 groupes de « traînées de poussière » (3× line par groupe, une ligne en `stroke-dasharray`)
* Peinture:

  * Soleil: `linearGradient` chaud (jaune → orange)
  * Poussière: gradients clairs (type sable) appliqués sur strokes (épais, cap arrondi)
* Animations SMIL:

  * Soleil: `rotate 0→360` autour de **(32,32)** sur **45s** (loop)
  * Poussière: chaque groupe a un `translate` qui boucle sur **3s** : `(-2,2) → (0,0) → (-2,2)`

    * second groupe déphasé via `begin="-2.5s"`

**Décomposition en calques (factorisée)**

* `sun_core.png` (disque)
* `sun_rays.png` (rayons)
* `dust_streaks.png` (un groupe complet de traînées, transparent)

**Adaptation LVGL (100% fidèle)**

* Composition (Z): soleil core → soleil rays → poussière (au-dessus)
* Soleil:

  * même implémentation que **B4** (pivot centre, angle 0..3600, 45s loop)
* Poussière:

  * 2 instances de `dust_streaks.png` (objets `img_dust1`, `img_dust2`) aux positions de base
  * animation de **position** (petit jitter) sur 3000ms loop:

    * `img_dustX`: `pos = base + (dx,dy)` avec dx/dy interpolés `(-2,+2) → (0,0) → (-2,+2)`
  * déphasage:

    * `img_dust1`: 0ms
    * `img_dust2`: décalage ~2500ms (équivalent begin -2.5s sur une période 3s)

**Notes fidélité**

* Les `stroke-dasharray` + gradients sur lignes sont *très* variables en SVG decodeur → raster obligatoire.
* L’animation poussière doit rester subtile (petit déplacement), sinon ça devient « neige/pluie ».

---

## B9) dust-wind.svg

**Analyse SVG**

* `viewBox`: `0 0 64 64`
* Primitives:

  * Groupes de lignes courbes/ondulées représentant le vent chargé de poussière
  * Absence de soleil/lune → icône purement « particulaire »
* Peinture:

  * Strokes épais à cap arrondi
  * Dégradés sable/gris clair sur les lignes (aspect volumique)
* Animations SMIL:

  * Translation horizontale continue (vent)
  * Légère variation de position verticale / phase entre groupes

**Décomposition en calques (factorisée)**

* `dust_wind_group.png` (un groupe complet de lignes de vent, transparent)

**Adaptation LVGL (100% fidèle)**

* Composition:

  * conteneur 64×64
  * 2 à 3 instances de `dust_wind_group.png` superposées
* Animations:

  * Translation X cyclique (vent):

    * déplacement gauche → droite (ou inverse selon SVG) sur 2.5–4s
    * wrap visuel (repositionnement discret hors champ)
  * Déphasage:

    * chaque instance démarre avec un offset temporel différent
  * Optionnel:

    * légère oscillation Y (±1px) pour casser la rigidité

**Notes fidélité / pièges**

* Pas d’opacité pulsée (sinon effet brouillard).
* Le wrap doit être invisible (repositionnement hors écran, pas de jump).
* Les lignes doivent rester parfaitement nettes → raster indispensable.

---

## B10) celsius.svg

**Analyse SVG**

* `viewBox`: `0 0 64 64`
* Primitives:

  * Glyphe "°C" (paths simples, typographie dessinée)
* Peinture:

  * Couleur unie ou léger dégradé, strokes nets
* Animation SMIL:

  * Aucune

**Adaptation LVGL (factorisée)**

* Raster unique `celsius.png` (plein cadre)
* Usage:

  * Icône statique ou label décoratif
  * Peut être combinée avec une valeur numérique LVGL (`lv_label`) à côté

---

## B11) clear-night.svg

**Analyse SVG**

* Primitives:

  * Lune (disque/croissant)
  * Étoiles éventuelles
* Animation SMIL:

  * Scintillement léger (opacity)

**Adaptation LVGL**

* Réutilise **pattern nuit** (voir B6):

  * `moon.png` statique
  * étoiles avec opacity pulsée désynchronisée

---

## B12) cloudy.svg

**Analyse SVG**

* Primitives:

  * 1 à 2 nuages superposés (paths)
* Animation SMIL:

  * Légère dérive horizontale ou aucune

**Adaptation LVGL**

* Raster `cloud.png`
* Option animation:

  * micro-translate X (±1–2px, 6–10s) pour donner de la vie sans distraire

---

## B13) compass.svg

**Analyse SVG**

* Primitives:

  * Rose des vents (cercle + graduations)
  * Aiguille (path)
* Animation SMIL:

  * Rotation de l’aiguille (cap)

**Adaptation LVGL (identique baromètre)**

* Raster:

  * `compass_dial.png` (fond)
  * `compass_needle.png`
* Animation:

  * pivot centre
  * angle piloté par donnée externe (heading)

---

## B14) drizzle.svg

**Analyse SVG**

* Primitives:

  * Nuage
  * Gouttes fines (traits courts)
* Différence clé vs pluie:

  * densité faible
  * vitesse plus lente

**Adaptation LVGL**

* Réutilise **pattern pluie** (B1) avec paramètres:

  * durée: 1.0–1.5s
  * amplitude Y réduite
  * opacity plus douce

---

## B15) dust-night.svg

**Analyse SVG**

* Primitives:

  * Lune
  * Traînées de poussière
* Animation SMIL:

  * identique dust-day mais ambiance nocturne

**Adaptation LVGL**

* Combine **pattern nuit** (B6) + **pattern poussière** (B8/B9)
* Ajustements:

  * contrastes plus faibles
  * vitesses identiques à dust-day

---

## B16) partly-cloudy-night.svg

**Analyse / pattern**

* Lune + nuage, sans précipitations.
* Animation minimale ou nulle.

**Adaptation LVGL**

* Combine **pattern nuit (B6)** + **nuage statique (B12)**.
* Option micro-dérive du nuage (±1px, très lent).

---

## B17) partly-cloudy-night-rain.svg

**Analyse / pattern**

* Lune + nuage + pluie.

**Adaptation LVGL**

* Pattern nuit (B6)
* Pattern pluie (B1), paramètres pluie standard.

---

## B18) partly-cloudy-night-snow.svg

**Analyse / pattern**

* Lune + nuage + neige.

**Adaptation LVGL**

* Pattern nuit (B6)
* Pattern neige (B7), chute lente + opacité douce.

---

## B19) partly-cloudy-night-hail.svg

**Analyse / pattern**

* Lune + nuage + grêle (projectiles courts).

**Adaptation LVGL**

* Pattern nuit (B6)
* Nouveau **pattern grêle** (dérivé pluie):

  * translation Y rapide
  * pas d’oscillation X
  * impact visuel sec (opacity quasi constante)

---

## B20) partly-cloudy-night-sleet.svg

**Analyse / pattern**

* Lune + nuage + grésil (mix pluie/neige).

**Adaptation LVGL**

* Pattern nuit (B6)
* Mix **pluie (rapide)** + **neige (lente)** avec moins d’instances.

---

## B21) partly-cloudy-night-haze.svg

**Analyse / pattern**

* Lune + nuage + voile atmosphérique diffus.

**Adaptation LVGL**

* Pattern nuit (B6)
* Nouveau **pattern haze**:

  * 1–2 couches semi-transparentes
  * micro-translate X/Y très lent
  * opacity basse (30–60%)

---

## B22) partly-cloudy-night-smoke.svg

**Analyse / pattern**

* Lune + nuage + fumée (volumes plus marqués que haze).

**Adaptation LVGL**

* Pattern nuit (B6)
* Pattern fumée (variante haze):

  * opacity plus élevée
  * dérive directionnelle plus visible

---

## B23) pressure-high.svg / pressure-high-alt.svg

**Analyse / pattern**

* Icône pression haute (flèche / symbole ↑).

**Adaptation LVGL**

* Raster unique statique.
* Variante `-alt` = simple swap d’asset (pas de logique spécifique).

---

## B24) pressure-low-alt.svg

**Analyse / pattern**

* Icône pression basse (↓).

**Adaptation LVGL**

* Raster unique statique.
* Même logique que pression haute.

---

## B25) hail.svg

**Analyse / pattern**

* Projectiles ronds/courts, chute rapide, lecture "impact".

**Adaptation LVGL**

* Pattern **grêle** (dérivé pluie):

  * translation Y rapide
  * opacity quasi constante
  * aucune oscillation X

---

## B26) haze.svg / haze-day.svg / haze-night.svg

**Analyse / pattern**

* Voile atmosphérique diffus, peu contrasté.

**Adaptation LVGL**

* Pattern **haze**:

  * 1–2 couches PNG translucides
  * micro-translate X/Y très lent
  * day/night = palette et opacity ajustées

---

## B27) mist.svg

**Analyse / pattern**

* Brouillard bas, couches horizontales.

**Adaptation LVGL**

* Pattern **mist** (spécialisation haze):

  * translate X lent
  * opacity modérée (50–70%)
  * pas de chute verticale

---

## B28) horizon.svg

**Analyse / pattern**

* Ligne d’horizon, séparation ciel/sol.

**Adaptation LVGL**

* Raster statique.
* Option micro-pulse d’opacité pour profondeur.

---

## B29) humidity.svg

**Analyse / pattern**

* Goutte + pourcentage.

**Adaptation LVGL**

* Icône goutte statique.
* Valeur `%` via `lv_label`.

---

## B30) hurricane.svg

**Analyse / pattern**

* Spirale cyclonique.

**Adaptation LVGL**

* Raster spirale.
* Animation rotation continue (10–20s) + léger pulse d’opacité.

---

## B31) lightning-bolt.svg

**Analyse / pattern**

* Éclair seul, symbole d’énergie.

**Adaptation LVGL**

* Raster unique.
* Animation flash d’opacité (optionnelle) courte.

---

## B32) moon-first-quarter.svg

**Analyse / pattern**

* Phase lunaire statique.

**Adaptation LVGL**

* Raster statique.
* Swap d’asset selon phase.

---

## C) Checklist de validation (commune)

* Visuel: gradients/strokes/AA identiques à l’original.
* Alignement: pivots exacts, aucun drift cumulatif.
* Animation:

  * respecter la signature du phénomène (impact, diffusion, rotation)
  * aucune synchronicité artificielle
* Perf: pas de resize runtime, assets par taille.

---

## D) API LVGL : formalisation des patterns (struct + params)

Objectif : une API unique pour instancier n’importe quelle icône météo/UI, en ne changeant que des paramètres.

### D1) Types de base

```c
// Taille logique d’icône (tu peux aussi utiliser px direct)
typedef enum {
  WX_SIZE_64  = 64,
  WX_SIZE_96  = 96,
  WX_SIZE_128 = 128,
} wx_size_t;

// Familles de patterns (effets)
typedef enum {
  WX_FX_NONE = 0,
  WX_FX_ROTATE,      // rotation continue (rayons, spirale)
  WX_FX_FALL,        // chute verticale (pluie/neige/grêle)
  WX_FX_FLOW_X,      // flux horizontal (vent)
  WX_FX_JITTER,      // micro-translate cyclique (poussière)
  WX_FX_TWINKLE,     // scintillement (étoiles)
  WX_FX_FLASH,       // flash (éclair)
  WX_FX_CROSSFADE,   // swap de frames (scale non-uniforme simulé)
  WX_FX_DRIFT,       // micro-translate très lent (nuage/haze)
} wx_fx_type_t;

// Décor / composition
typedef enum { WX_DECOR_NONE=0, WX_DECOR_SUN, WX_DECOR_MOON } wx_decor_t;
typedef enum { WX_COVER_NONE=0, WX_COVER_CLOUD } wx_cover_t;
typedef enum { WX_PART_NONE=0, WX_PART_RAIN, WX_PART_DRIZZLE, WX_PART_SNOW, WX_PART_SLEET, WX_PART_HAIL } wx_particle_t;
typedef enum { WX_ATMOS_NONE=0, WX_ATMOS_HAZE, WX_ATMOS_SMOKE, WX_ATMOS_MIST, WX_ATMOS_DUST, WX_ATMOS_DUST_WIND } wx_atmos_t;

// Identifiants d’assets (par pack/taille)
typedef enum {
  WX_ASSET_SUN_CORE,
  WX_ASSET_SUN_RAYS,
  WX_ASSET_MOON,
  WX_ASSET_CLOUD,
  WX_ASSET_DROP,
  WX_ASSET_SNOWFLAKE,
  WX_ASSET_HAIL,
  WX_ASSET_LIGHTNING,
  WX_ASSET_DUST_STREAKS,
  WX_ASSET_DUST_WIND_GROUP,
  WX_ASSET_HAZE_LAYER,
  WX_ASSET_MIST_LAYER,
  WX_ASSET_HURRICANE_SPIRAL,
  WX_ASSET_DIAL,
  WX_ASSET_NEEDLE,
  WX_ASSET_UI_CELSIUS,
  WX_ASSET_PRESSURE_HIGH,
  WX_ASSET_PRESSURE_LOW,
  // etc.
} wx_asset_id_t;
```

### D2) Résolution d’assets (pack par taille)

Principe : tu fournis un resolver qui retourne le `lv_img_dsc_t*` correspondant.

```c
typedef const lv_img_dsc_t* (*wx_asset_resolver_t)(wx_asset_id_t id, wx_size_t size);
```

### D3) Paramètres d’animation (généraux)

```c
typedef struct {
  wx_fx_type_t type;
  uint32_t     period_ms;     // durée d’un cycle
  int16_t      amp_x;         // amplitude px (si applicable)
  int16_t      amp_y;         // amplitude px (si applicable)
  uint8_t      opa_min;       // 0..255 (si applicable)
  uint8_t      opa_max;       // 0..255
  uint16_t     angle_from;    // en dixièmes de degré (0..3600)
  uint16_t     angle_to;
  int16_t      pivot_x;       // pivot dans l’image
  int16_t      pivot_y;
  uint32_t     phase_ms;      // déphasage (0..period-1)
  bool         loop;
  bool         ease_in_out;
} wx_fx_params_t;
```

### D4) Paramètres de particules (pluie/neige/grêle)

```c
typedef struct {
  wx_particle_t kind;
  uint8_t       count;          // nb d’instances
  int16_t       base_x[8];       // positions de base (jusqu’à 8)
  int16_t       base_y[8];
  int16_t       fall_dx;         // option (neige légère)
  int16_t       fall_dy;         // amplitude Y
  uint32_t      period_ms;       // ex: pluie 700ms, neige 1200-2000ms
  uint8_t       opa_min;
  uint8_t       opa_max;
  uint32_t      phase_ms[8];     // déphasage par particule
} wx_particles_params_t;
```

### D5) Paramètres “flash” (éclair)

```c
typedef struct {
  bool     enabled;
  uint16_t flash_ms;       // 80-150ms
  uint16_t gap_ms_min;     // 2000
  uint16_t gap_ms_max;     // 5000
  bool     double_flash;   // 255→0→255→0
} wx_flash_params_t;
```

### D6) Paramètres “aiguille” (baromètre/compas)

```c
typedef struct {
  bool     enabled;
  int16_t  pivot_x;
  int16_t  pivot_y;
  uint16_t angle_now;      // 0..3600
  uint32_t smooth_ms;      // animation vers nouvelle valeur
} wx_needle_params_t;
```

### D7) Spécification d’icône (composition)

```c
typedef struct {
  wx_size_t size;
  wx_decor_t decor;
  wx_cover_t cover;
  wx_particle_t particles;
  wx_atmos_t atmos;

  // Assets overrides (optionnel)
  wx_asset_id_t asset_decor_core;  // soleil core / lune
  wx_asset_id_t asset_decor_fx;    // rayons
  wx_asset_id_t asset_cover;       // nuage

  // FX
  wx_fx_params_t       decor_fx;   // ex: rotation rayons
  wx_particles_params_t part_fx;   // pluie/neige/grêle
  wx_fx_params_t       atmos_fx;   // haze/mist/vent
  wx_flash_params_t    lightning;  // éclair
  wx_needle_params_t   needle;     // baromètre/compas
} wx_icon_spec_t;
```

### D8) Handle runtime (pour updates)

```c
typedef struct {
  lv_obj_t* cont;

  // couches communes
  lv_obj_t* img_decor_core;
  lv_obj_t* img_decor_fx;
  lv_obj_t* img_cover;

  // particules (jusqu’à 8)
  lv_obj_t* img_part[8];
  uint8_t   part_count;

  // atmos (jusqu’à 3 couches)
  lv_obj_t* img_atmos[3];
  uint8_t   atmos_count;

  // éclair
  lv_obj_t* img_lightning;

  // dial/needle
  lv_obj_t* img_dial;
  lv_obj_t* img_needle;

  // callbacks internes / timers
  lv_timer_t* t_lightning;

  wx_icon_spec_t spec;
} wx_icon_t;
```

### D9) API publique minimale

```c
// Création
wx_icon_t* wx_icon_create(lv_obj_t* parent,
                          const wx_icon_spec_t* spec,
                          wx_asset_resolver_t resolver);

// Destruction
void wx_icon_destroy(wx_icon_t* icon);

// Mise à jour de données (sans recréer)
void wx_icon_set_heading(wx_icon_t* icon, uint16_t angle_0_3600);       // compas
void wx_icon_set_pressure_angle(wx_icon_t* icon, uint16_t angle_0_3600);

// Reconfig (changement de pattern complet)
void wx_icon_apply_spec(wx_icon_t* icon,
                        const wx_icon_spec_t* spec,
                        wx_asset_resolver_t resolver);
```

### D10) Table de presets (mapping “nom d’icône” → spec)

Idée : une fonction par icône qui renvoie un `wx_icon_spec_t` rempli.

```c
wx_icon_spec_t wx_preset_partly_cloudy_night_rain(wx_size_t size);
wx_icon_spec_t wx_preset_clear_day(wx_size_t size);
wx_icon_spec_t wx_preset_dust_wind(wx_size_t size);
// ...
```

### D11) Notes d’implémentation (tranchées)

* **Rotation**: uniquement sur la couche “fx” (rayons, spirale), jamais sur le core.
* **Chute**: particules instanciées à partir d’un **seul** asset (`drop/snowflake/hail`) + déphasage.
* **Scale non-uniforme**: interdire en runtime → uniquement via **crossfade** de frames pré-bakées.
* **Flash**: opacité uniquement (0/255), pas d’interpolation de position.
* **Resolver**: clé pour garder le code agnostique (packs 64/96/128, thèmes, etc.).
