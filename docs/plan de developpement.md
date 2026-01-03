# plan de developpement.md — Plan de développement (offline Python → runtime ESP/LVGL)

## 0) Objectif

Produire un projet **fonctionnel** et **industrializable** :

* Offline (Python) : SVG → calques → images → JSON runtime `wx.spec v1` → pack `WXPK v1`
* Runtime (ESP/LVGL) : charger pack → résoudre assets → instancier layers → appliquer FX → afficher

Le runtime est une **bibliothèque prête à l’emploi**, avec exemples.

Documents normatifs :

* `wx-pack-spec.md` (ABI pack + schéma JSON figé)
* `wx-fx-contracts.md` (contrats FX)
* `assets-naming-and-packing.md` (naming + hashing)

---

## 1) Jalons (macro)

1. Fondations (contrats + arborescence dépôt)
2. Offline Python (analyse + pipeline + packer)
3. Runtime C (lib + loader + FX)
4. Intégration & exemples (ESP)
5. Non-régression & CI

---

## 2) Arborescence cible (proposée)

```
/README.md
/agent.md
/docs
  wx-pack-spec.md
  wx-fx-contracts.md
  assets-naming-and-packing.md
  preset-catalog.md
  mapping-svg-pattern.md
  technical-choices.md
  plan de developpement.md
/tools
  /wx
    __init__.py
    cli.py
    svg/
      parse.py
      smil.py
      geom.py
      semantic.py
    plan/
      layers.py
      pivots.py
      validate.py
    export/
      raster.py
      manifest.py
      lvgl_conv.py
    pack/
      wxpk.py
      hash.py
      crc.py
      schema.py
    gui/
      app.py
      widgets/
/tests
  /fixtures
    ...
/firmware
  /wxlib
    include/
      wxpk.h
      wx_icon.h
      wx_fx.h
      wx_assets.h
    src/
      wxpk.c
      wx_icon.c
      wx_fx.c
      wx_resolver.c
  /examples
    /basic
    /from_pack
    /instruments
```

---

## 3) Développement offline Python (ordre strict)

### Étape P1 — Implémenter le hashing et la normalisation

* `asset_key` normalisé `[a-z0-9_]+`
* `asset_hash = FNV1a32(asset_key)`

Livrables :

* `tools/wx/pack/hash.py`
* tests unitaires (vecteurs connus)

---

### Étape P2 — Définir le schéma `wx.spec v1` (code)

* validation JSON (types, champs obligatoires)
* génération d’IDs `spec_id` (u32) :

  * règle déterministe (ex: mapping table + stable ID file)

Livrables :

* `tools/wx/pack/schema.py`
* `tools/wx/pack/validate_spec.py`

---

### Étape P3 — Parser SVG robuste

* XML parse
* extraction `<g>/<path>/<circle>/<rect>`
* extraction styles (`fill`, `stroke`, `opacity`)
* extraction SMIL (`<animate>`, `attributeName`, `dur`, `values`, `keyTimes`)

Livrables :

* `tools/wx/svg/parse.py`
* `tools/wx/svg/smil.py`

---

### Étape P4 — Détection pattern (mapping)

* heuristiques déterministes :

  * rotate → ROTATE
  * opacity pulses → TWINKLE/FLASH
  * translate y → FALL
  * translate x wrap → FLOW_X
  * needle rotate piloté → NEEDLE
* sortie : `wx.spec v1` (layers + fx)

Livrables :

* `tools/wx/svg/semantic.py`
* `tools/wx/plan/layers.py`

---

### Étape P5 — Plan calques & pivots

* 1 cible SMIL = 1 layer
* split core/fx (ex: sun_core vs sun_rays)
* calcul pivots (par règle + table) + normalisation

Livrables :

* `tools/wx/plan/pivots.py`
* `tools/wx/plan/validate.py`

---

### Étape P6 — Rasterisation PNG multi-tailles

* export par layer et par taille (64/96/128)
* fond transparent, plein cadre, positions figées

Livrables :

* `tools/wx/export/raster.py`
* `tools/wx/export/manifest.py`

---

### Étape P7 — Conversion LVGL (dev)

* génération `*.c/*.h` via `lv_img_conv` (ou équivalent)

Livrables :

* `tools/wx/export/lvgl_conv.py`

---

### Étape P8 — Packager WXPK v1 (prod)

* écrire `wxpk_header_t` + `wxpk_toc_entry_t`
* mode recommandé : JSON splitté

  * `WXPK_T_JSON_SPEC` par `spec_id`
  * `WXPK_T_JSON_INDEX` optionnel
* blobs images codec recommandé : `WXPK_C_LVGL_BIN`
* CRC32 blob

Livrables :

* `tools/wx/pack/wxpk.py`
* `tools/wx/pack/crc.py`

---

### Étape P9 — CLI (orchestrateur)

Commandes minimum :

* `wx analyze <svg_dir> -> mapping/audit`
* `wx export <svg_dir> --sizes 64,96,128 -> png + manifest`
* `wx pack <manifest> <spec.json> -> pack.bin`
* `wx all <svg_dir> -> tout en une commande`

Livrables :

* `tools/wx/cli.py`

---

### Étape P10 — GUI PySide6 (orchestrateur visuel)

* la GUI appelle les modules/CLI
* affichage :

  * SVG
  * layers
  * JSON spec
  * preview PNG + FX (simulation)

Livrables :

* `tools/wx/gui/app.py`

---

## 4) Développement runtime ESP/LVGL (bibliothèque)

### Étape C1 — Implémenter le loader WXPK

* structs strictes (`wxpk.h`)
* `wxpk_open`, `wxpk_find_img`, `wxpk_find_spec`, `wxpk_blob_ptr`
* validation header/offsets

Livrables :

* `firmware/wxlib/include/wxpk.h`
* `firmware/wxlib/src/wxpk.c`

---

### Étape C2 — Implémenter le resolver pack

* entrée : `(asset_hash, size_px)`
* sortie : `lv_img_dsc_t*` (ou handle)

Décision pratique :

* si codec = `LVGL_BIN`, construire un `lv_img_dsc_t` pointant sur blob
* si PNG : nécessite decodeur (option)

Livrables :

* `wx_resolver.c/.h`

---

### Étape C3 — Parser JSON minimal (runtime)

Deux options :

* parser JSON (cJSON ou jsmn)
* ou version compacte binaire plus tard

Choix initial : parser JSON minimal.

Livrables :

* `wx_icon_spec_parse.c/.h`

---

### Étape C4 — Instanciation LVGL depuis `wx_icon_spec_t`

* création container `SIZE×SIZE`
* création `lv_img` pour chaque `layer.z`
* `instances` : instancier N objets

Livrables :

* `wx_icon.c/.h`

---

### Étape C5 — Implémentation FX (conforme contrat)

* `wx_fx.c/.h`
* ROTATE, FALL, FLOW_X, JITTER, DRIFT, TWINKLE, FLASH, CROSSFADE, NEEDLE

Livrables :

* `wx_fx.c/.h`

---

### Étape C6 — API publique de la lib (prête à l’emploi)

API minimale :

* `wx_init(lv_disp_t*, ...)` (option)
* `wx_pack_open(handle, data, size)`
* `wx_icon_create_from_spec_id(parent, pack, spec_id, size_px)`
* `wx_icon_destroy(icon)`
* `wx_icon_set_value(icon, channel, value)` (instruments)
* `wx_icon_tick()` (si nécessaire)

Livrables :

* `wx_api.h` (publique)
* exemples compilables

---

## 5) Exemples (obligatoires)

### Exemple E1 — from_pack

* charge un `pack.bin`
* instancie 3 icônes (1 statique, 1 fall, 1 flash)

### Exemple E2 — instruments

* affiche `compass` / `barometer`
* met à jour angle/valeur toutes les X ms

### Exemple E3 — multi-size

* affiche la même spec en 64/96/128 (si disponible)

Livrables :

* `firmware/examples/*`

---

## 6) Validation et non-régression

### Étape V1 — Fixtures offline

* SVG d’entrée
* JSON `wx.spec v1` attendu
* hashes PNG attendus
* taille pack attendue

### Étape V2 — CI

* lint naming
* validate spec
* build pack
* (option) build firmware lib

---

## 7) Critère “code complet”

Le projet est considéré complet quand :

* `wx all <dir>` produit un pack `WXPK v1` valide
* le runtime charge le pack et affiche les presets core set
* les FX respectent `wx-fx-contracts.md`
* les exemples compilent et tournent

---

## 8) Ordre d’exécution recommandé (pratique)

1. P1 → P2 → P8 (hash/schema/pack) pour verrouiller ABI
2. C1 → C2 pour charger des blobs
3. P3 → P6 pour produire images
4. C3 → C5 pour consommer JSON et animer
5. P9 + P10 pour outillage
6. V1 + V2 pour stabiliser
