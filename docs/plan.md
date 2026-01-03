# Plan de développement réaligné (WX Weather Icons)

## 1) Objectif global

Fournir une chaîne de génération et d’exécution d’icônes météo animées pour LVGL/ESP reposant sur un format de données unifié :

* JSON **wx.spec v1** (spécification runtime)
* pack binaire **WXPK v1** (format de production)

Le code C ne contient aucune donnée d’icône statique. Le runtime consomme uniquement ces deux formats.

---

## 2) Architecture de la chaîne

### 2.1 Offline (Python)

1. **Analyse SVG**

   * Parsing structure et styles.
   * Identification des calques et FX associés.

2. **Mapping et génération JSON wx.spec v1**

   * Normalisation des `asset_key` ([a-z0-9_]+).
   * Calcul `asset_hash = FNV1a32(asset_key)`.
   * Attribution des FX contractuels (type, params, target_z).
   * Règle : **toutes les clés FX doivent être présentes** conformément à `mapping-svg-pattern.md`.

3. **Rasterisation des calques**

   * Export en PNG pleine taille (64 / 96 / 128 px).
   * Convention de pivot et alignement unique.

4. **Packaging WXPK v1**

   * Inclusion header 32B + TOC + payloads + JSON wx.spec v1.
   * Hashing **manuel** : un bump explicite de version est requis pour toute rupture de compatibilité.
   * Versionnement incrémental contrôlé par pipeline (non auto-bump).

5. **Validation CI**

   * Comparaison auto SVG → PNG.
   * Vérification des FX obligatoires.
   * Hash cohérent entre JSON et pack.

---

### 2.2 Runtime (ESP/LVGL)

1. **Loader WXPK**

   * Lecture du header et du TOC.
   * Extraction du JSON et des assets binaires.

2. **Parser JSON wx.spec v1**

   * Construction des structures runtime à partir du JSON.
   * Résolution des assets par `(asset_hash, size_px, type)`.

3. **Instanciation LVGL**

   * Création dynamique des `lv_img` d'après la spécification JSON.
   * Application des FX via les contrats définis dans `wx-fx-contracts.md`.

4. **Animation et mise à jour**

   * Gestion du cycle de vie (create/destroy/update).
   * Synchronisation opacité, translation, rotation, etc.
   * Aucun hardcode ni preset C.

---

## 3) Interfaces normalisées

### 3.1 Côté offline

* Entrées : SVG source, tables de mapping, contrôles FX.
* Sorties : `icon.wxspec.json` + `icon.wxpk`.

Un pack peut être **mono-icône** (usage courant) ou **multi-icônes** (groupement logique par thème ou taille).
Le TOC du pack référence alors plusieurs specs et ensembles d’assets.
Chaque entrée TOC inclut un **identifiant de spec** (`spec_id`) permettant au loader de sélectionner la bonne icône, ou un champ `id` dans le JSON wx.spec v1 servant de clé interne.

### 3.2 Côté runtime

* Fonctions d’API (C) :

  ```c
  wx_icon_t* wx_icon_from_pack(lv_obj_t* parent, const void* pack_data);
  void wx_icon_destroy(wx_icon_t* icon);
  void wx_icon_update(wx_icon_t* icon, const char* json_spec);
  ```

  `wx_icon_update()` applique une **surcharge temporaire** : elle permet d’injecter une nouvelle spécification JSON (ex. changement de thème ou d’animation) sans recharger l’ensemble du pack.
  Le pack reste la source de vérité persistente.

---

## 4) Données contractuelles

### 4.1 Assets

* Identifiés par `asset_key` → `asset_hash`.
* Lookup runtime par `(asset_hash, size_px, type)`.
* Renommage interdit sans bump de version.

### 4.2 FX (contrats JSON)

* Typologie conforme à `wx-fx-contracts.md` : ROTATE, FALL, FLOW_X, JITTER, DRIFT, TWINKLE, FLASH, CROSSFADE, NEEDLE.
* Chaque FX : intention, params, invariants, compatibilités.
* Ciblage par `target_z`.
* Présence intégrale des clés FX exigée (voir `mapping-svg-pattern.md`).

### 4.3 Presets

* **Purement documentaires** : regroupés dans `preset-catalog.md`.
* Aucun code C généré, uniquement JSON wx.spec v1.

---

## 5) Validation et CI

* Génération auto des packs à partir des SVG.
* Contrôle d’intégrité FNV1a32.
* Tests d’affichage LVGL offline.
* Validation des FX (présence et conformité).
* Publication automatique des packs validés.

---

## 6) Critère de réussite

> Ajout d’un SVG → génération JSON + WXPK → affichage LVGL conforme sans modification de code.
