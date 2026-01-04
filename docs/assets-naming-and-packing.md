# assets-naming-and-packing.md — Convention canonique assets, nommage et packing

## 0) Portée

Ce document définit la **convention normative unique** pour :

* le **nommage des assets** (PNG, sorties LVGL, symboles)
* l’**organisation des packs** par thème et par taille
* la **définition et l’usage des pivots**
* les **règles de packing** garantissant un rendu pixel‑perfect

Il constitue la **vérité contractuelle** pour l’outillage offline (Python), le packaging WXPK et le runtime ESP/LVGL.

Toute autre convention est obsolète.

---

## 1) Principes non négociables

1. **PNG plein cadre** : chaque image fait exactement `SIZE × SIZE` pixels et intègre ses marges.
2. **Fond transparent obligatoire** (alpha).
3. **Aucune mise à l’échelle runtime** (ni zoom LVGL, ni resize objet).
4. **Un asset = une intention visuelle unique** (core, FX, particule, UI, etc.).
5. **Pivots définis dans le repère image**, identiques conceptuellement pour toutes les tailles via scaling linéaire.
6. **Aucune déduction implicite runtime** (noms, tailles, pivots, fallback).

---

## 2) Arborescence de référence

### 2.1 Structure standard

```
/assets
  /src_svg
  /raster
    /<theme>
      /64
      /96
      /128
  /lvgl
    /<theme>
      /64
      /96
      /128
```

* `src_svg/` : sources maîtres (versionnées uniquement)
* `raster/` : PNG exportés plein cadre + alpha
* `lvgl/` : sorties `lv_img_conv` (`*.c/*.h`)

### 2.2 Intégration firmware (option)

```
/firmware/components/wx_icons/assets/<theme>/<size>/*.c
```

---

## 3) Convention de nommage

### 3.1 Tokens

* `theme` : `base`, `dark`, `amoled`, …
* `size` : `64`, `96`, `128`
* `asset` : identifiant canonique (§4)
* `variant` : suffix optionnel (`alt`, `v2`, `a`, `b`)
* `frame` : frame animée bakée (`f0`, `f1`, …)

---

### 3.2 PNG raster

```
<asset>[_<variant>][_fN]_<size>.png
```

Exemples :

* `sun_core_64.png`
* `pressure_high_alt_96.png`
* `raindrop_norm_f0_64.png`

---

### 3.3 Sorties LVGL (`lv_img_conv`)

```
wx_<theme>_<asset>[_<variant>][_fN]_<size>.(c|h)
```

---

### 3.4 Symbole LVGL

```
wx_<theme>_<asset>[_<variant>][_fN]_<size>
```

---

## 4) Dictionnaire d’assets canoniques

Ce dictionnaire est **stable** et alimente l’identité runtime.

### Décor

* `sun_core`
* `sun_rays`
* `moon`
* `moon_phase_first_quarter`

### Couverture

* `cloud`

### Particules

* `drop`
* `drizzle_drop`
* `snowflake`
* `hail`
* `sleet_drop`

### Atmosphère

* `haze_layer_a`, `haze_layer_b`
* `smoke_layer_a`
* `mist_layer_a`
* `dust_streaks`
* `dust_wind_group`

### Événements

* `lightning`
* `hurricane_spiral`

### Instruments

* `dial`
* `needle`
* `compass_dial`
* `compass_needle`

### UI

* `ui_celsius`
* `pressure_high`, `pressure_high_alt`
* `pressure_low`, `pressure_low_alt`
* `humidity_drop`

---

## 5) Variantes et frames

### 5.1 Variantes

* Modifient le rendu, **pas l’intention**.
* Partagent les mêmes pivots et FX.

### 5.2 Frames (`_fN`)

* Utilisées uniquement quand un FX n’est pas reproductible dynamiquement.
* Animation runtime par **crossfade** (opacity).
* Les frames doivent exister en paires cohérentes (`f0`, `f1`, …).

---

## 6) Pivots — Contrat canonique

### 6.1 Définition

* Pivot exprimé en coordonnées **normalisées** `(x,y) ∈ [0..1]`.
* Repère : image PNG plein cadre `SIZE × SIZE`.
* Aucun pivot implicite.

### 6.2 Conversion normalisée → pixels

```
pivot_px_x = round(pivot_norm_x * (size_px - 1))
pivot_px_y = round(pivot_norm_y * (size_px - 1))
```

---

### 6.3 Table canonique des pivots

Tous les assets définis ci‑dessous utilisent un pivot **centré** `(0.5, 0.5)` :

* décor : `sun_core`, `sun_rays`, `moon`, `moon_phase_first_quarter`
* couverture : `cloud`
* particules : `drop`, `drizzle_drop`, `snowflake`, `hail`, `sleet_drop`
* atmos : `haze_layer_a`, `haze_layer_b`, `smoke_layer_a`, `mist_layer_a`, `dust_streaks`, `dust_wind_group`
* événements : `lightning`, `hurricane_spiral`
* instruments : `dial`, `needle`, `compass_dial`, `compass_needle`
* UI : `ui_celsius`, `pressure_high`, `pressure_high_alt`, `pressure_low`, `pressure_low_alt`, `humidity_drop`

Toute modification de pivot est un **breaking change visuel**.

---

## 7) Packs thème / taille

* Sélection par `size` (pas de scaling).
* Sélection par `theme`.
* Un thème est un **ensemble cohérent** d’assets.

---

## 8) Fallbacks

### Taille

* **Interdit par défaut**.
* Autorisé uniquement si explicitement contracté.

### Thème

* Autorisé si défini (`dark → base`).

---

## 9) Resolver — Contrat attendu

* Résolution O(1)
* Aucun `malloc`
* Retour `NULL` si asset absent

Clé logique : `(theme, size, asset_id)`.

---

## 10) Conformité automatique (CI)

Vérifications obligatoires :

* PNG exactement `SIZE × SIZE`
* Alpha présent
* Nommage conforme
* Présence de tous les assets requis par pack
* Cohérence des frames

Regex PNG :

```
^[a-z0-9]+(?:_[a-z0-9]+)*(?:_f[0-9]+)?_(64|96|128)\.png$
```

Regex symbole LVGL :

```
^wx_(base|dark)_[a-z0-9]+(?:_[a-z0-9]+)*(?:_f[0-9]+)?_(64|96|128)$
```

---

## 11) Cohérence et invariants

* Convention compatible avec WXPK v1 et `wx.spec v1`.
* Aucun conflit entre nommage, pivots et packing.
* Toute déviation implique mise à jour documentaire + régénération des assets.
