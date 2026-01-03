# Assets naming & packing (LVGL weather icons)

## 0) Objectif

Définir une convention **unique** et **mécanique** pour :

* nommer les PNG sources et les assets LVGL générés (`*.c/*.h`)
* organiser les packs par taille / thème
* garantir : alignement, pivots, rendu pixel-perfect, zéro resize runtime

Ce document est la vérité pour le `wx_asset_resolver_t`.

---

## 1) Principes non négociables

1. **Plein cadre** : chaque PNG fait exactement `SIZE×SIZE` et inclut l’offset (marges) si nécessaire.

   * Conséquence : la composition LVGL se fait à `(0,0)` dans un conteneur `SIZE×SIZE`.
2. **Fond transparent** obligatoire (alpha).
3. **Aucune mise à l’échelle runtime** (ni zoom LVGL, ni resize obj) : on choisit le pack de taille.
4. **Un asset = une intention** (core vs fx vs cover vs particule). Pas de mélange.
5. **Les pivots sont définis dans le repère image** (pixels du PNG) et sont identiques pour toutes les tailles via scaling linéaire.

---

## 2) Arborescence de référence

### 2.1 Structure recommandée

```
/assets
  /src_svg
    clear-day.svg
    ...
  /raster
    /base
      /64
      /96
      /128
    /dark
      /64
      /96
      /128
  /lvgl
    /base
      /64
      /96
      /128
    /dark
      /64
      /96
      /128
```

* `src_svg/` : sources originales (jamais modifiées à la main sauf versionnement clair)
* `raster/<theme>/<size>/` : PNG exportés (alpha)
* `lvgl/<theme>/<size>/` : sorties `lv_img_conv` (`*.c/*.h`)

### 2.2 Option (monorepo firmware)

Si tu veux tout embarquer dans le firmware :

```
/firmware
  /components
    /wx_icons
      /assets
        /base/64/*.c
        /base/96/*.c
        /base/128/*.c
```

---

## 3) Convention de nommage

### 3.1 Tokens

* `theme` : `base` | `dark` | `amoled` | etc.
* `size` : `64` | `96` | `128` (px)
* `asset` : identifiant fonctionnel (voir §4)
* `variant` : suffix optionnel (`alt`, `v2`, `a`, `b`)
* `frame` : pour crossfade / animation frame-bakée (`f0`, `f1`, ...)

### 3.2 PNG raster (source pour conversion)

Format :

```
<asset>[_<variant>][_fN]_<size>.png
```

Exemples :

* `sun_core_64.png`
* `sun_rays_128.png`
* `pressure_high_alt_64.png`
* `raindrop_norm_f0_64.png` / `raindrop_norm_f1_64.png`
* `haze_layer_a_96.png`

### 3.3 LVGL outputs (lv_img_conv)

Format :

```
wx_<theme>_<asset>[_<variant>][_fN]_<size>.(c|h)
```

Exemples :

* `wx_base_sun_core_64.c`
* `wx_dark_cloud_96.c`
* `wx_base_raindrop_norm_f0_64.c`

### 3.4 Symbol LVGL (`lv_img_dsc_t`)

Nom du symbole dans le `.c` :

```
wx_<theme>_<asset>[_<variant>][_fN]_<size>
```

Exemple :

* `extern const lv_img_dsc_t wx_base_cloud_64;`

---

## 4) Dictionnaire d’assets (canon)

Ce dictionnaire doit rester stable car il alimente `wx_asset_id_t`.

### 4.1 Décor

* `sun_core`
* `sun_rays`
* `moon`
* `moon_phase_first_quarter` (si phases multiples)

### 4.2 Couverture

* `cloud`

### 4.3 Particules

* `drop` (pluie)
* `drizzle_drop` (optionnel si visuel différent)
* `snowflake`
* `hail`
* `sleet_drop` (optionnel, sinon mix drop+snowflake)

### 4.4 Atmos

* `haze_layer_a`, `haze_layer_b` (couches)
* `smoke_layer_a`
* `mist_layer_a`
* `dust_streaks`
* `dust_wind_group`

### 4.5 Énergie / événements

* `lightning`
* `hurricane_spiral`

### 4.6 Instruments

* `dial` (baromètre/compas – fond)
* `needle` (baromètre/compas – aiguille)
* `compass_dial` / `compass_needle` (si distinct)

### 4.7 UI

* `ui_celsius`
* `pressure_high`, `pressure_high_alt`
* `pressure_low`, `pressure_low_alt`
* `humidity_drop` (si icône séparée)

---

## 5) Variantes et frames (règles)

### 5.1 Variantes (`_alt`, `_v2`)

* Une variante change l’asset visuel mais **pas l’intention**.
* Exemple : `pressure_high_alt` = même meaning, autre look.

### 5.2 Frames (`_fN`)

Utilisées uniquement quand LVGL ne peut pas reproduire un transform (ex: scale non-uniforme).

* `*_f0` = état normal
* `*_f1` = état compressé / alternatif
* L’animation runtime se fait par **crossfade** (opacity) entre frames.

---

## 6) Pivots (contrat)

### 6.1 Définition

Un pivot est défini **en pixels** dans le repère du PNG `SIZE×SIZE`.

### 6.2 Stockage des pivots

Les pivots ne doivent pas être “devinés” en runtime.
Deux options :

1. **Table statique** par asset et par taille
2. **Table normalisée** (0..1) puis conversion en pixels

Recommandé : normalisé.

Exemple (normalisé) :

* `sun_rays` pivot = `(0.5, 0.5)`
* `needle` pivot = `(0.5, 0.5)`

### 6.3 Implication

* Changer un export PNG qui décale le dessin = breaking change.
* Toute modification doit conserver le plein cadre + pivot cohérent.

---

## 7) Packs thème / taille

### 7.1 Sélection du pack

* UI choisit `size` en fonction du layout (pas de scaling).
* `resolver(id,size)` renvoie l’asset exact.

### 7.2 Thèmes

* `theme=base` = couleurs standard
* `theme=dark` = contrastes adaptés dark UI
* Un thème est un **ensemble complet** d’assets (ou partiel, mais alors fallback explicite).

---

## 8) Fallbacks (obligatoires)

### 8.1 Fallback de taille

Interdit par défaut.

* Si une taille manque, on **échoue** (assert/log) ou on choisit la plus proche **uniquement si explicitement autorisé**.

### 8.2 Fallback de thème

Autorisé si défini :

* si `dark` manque → fallback `base`.

---

## 9) Exemple de resolver (contrat attendu)

Le resolver doit :

* être O(1)
* ne faire aucun malloc
* renvoyer `NULL` si asset absent

Pseudo-table (à générer) :

* clé = `(theme,size,asset_id)`
* valeur = `&wx_<theme>_<asset>_<size>`

---

## 10) Check de conformité (CI)

Règles vérifiables automatiquement :

* Tous les PNG font exactement `SIZE×SIZE`
* Alpha présent
* Nommage conforme regex
* Tous les `wx_asset_id_t` ont une entrée pour chaque pack requis
* Toutes les frames `_fN` existent en paire (f0+f1)

Regex PNG :

* `^[a-z0-9]+(?:_[a-z0-9]+)*(?:_f[0-9]+)?_(64|96|128)\.png$`

Regex LVGL symbol :

* `^wx_(base|dark)_[a-z0-9]+(?:_[a-z0-9]+)*(?:_f[0-9]+)?_(64|96|128)$`
