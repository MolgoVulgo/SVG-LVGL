# WX Weather Icons — README

## 1) Objet du projet

WX Weather Icons est une **chaîne complète et industrialisable** permettant de transformer des icônes SVG météo en :

* assets graphiques multi-tailles,
* descriptions d’animation déclaratives,
* packs binaires embarqués,

puis de les afficher côté **ESP / LVGL** via une **bibliothèque prête à l’emploi**, sans aucune logique SVG au runtime.

Le projet repose sur un principe fondamental :

> **Toute l’intelligence est offline (Python). Le runtime n’interprète que des données.**

---

## 2) Architecture globale

### Vue d’ensemble

```
SVG
 ↓
[ Python / Offline ]
  analyse
  découpe
  raster
  wx.spec v1 (JSON runtime)
  WXPK v1 (pack BIN)
 ↓
[ ESP / Runtime LVGL ]
  loader WXPK
  resolver assets
  interprétation JSON
  affichage + FX
```

---

## 3) Principes structurants (non négociables)

* **JSON `wx.spec v1` est la vérité runtime**
* **WXPK v1 est le format de production**
* lookup des assets par `(asset_hash, size_px, type)`
* `asset_hash = FNV1a32(asset_key normalisé)`
* enums `WX_ASSET_*` réservés au canon (optimisation uniquement)
* le runtime ESP **n’analyse jamais de SVG**

Documents normatifs :

* `wx-pack-spec.md`
* `wx-fx-contracts.md`
* `assets-naming-and-packing.md`
* `agent.md`

---

## 4) Contenu du dépôt

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
  /wx           # outil offline Python
/firmware
  /wxlib        # bibliothèque ESP/LVGL
  /examples     # exemples prêts à compiler
/tests
  /fixtures     # non-régression
```

---

## 5) Pipeline offline (Python)

### Responsabilités

* parsing SVG (XML + SMIL)
* détection de patterns
* découpe en calques
* génération des images PNG multi-tailles
* génération des specs JSON `wx.spec v1`
* génération du pack binaire `WXPK v1`

### CLI (prévu)

```
wx analyze <svg_dir>
wx export <svg_dir> --sizes 64,96,128
wx pack <manifest> <spec.json>
wx all <svg_dir>
```

---

## 6) Runtime ESP / LVGL (bibliothèque)

### Responsabilités

* charger un pack `WXPK v1`
* résoudre les assets par hash
* parser le JSON runtime
* instancier les objets LVGL
* appliquer les FX contractuels

### API cible (indicative)

```c
wx_pack_open(&pack, data, size);
wx_icon_t* icon = wx_icon_create_from_spec_id(parent, &pack, spec_id, 64);
wx_icon_set_value(icon, WX_CH_HEADING, value);
```

Aucune icône n’est codée en dur.

---

## 7) Exemples fournis (objectif)

* **from_pack** : charge un pack et affiche plusieurs icônes
* **instruments** : compass / barometer pilotés dynamiquement
* **multi-size** : même spec affichée en 64 / 96 / 128

Ces exemples servent de **référence d’intégration**.

---

## 8) État actuel du projet

### Ce qui est en place

* architecture verrouillée
* contrats techniques figés
* spécification pack + JSON finalisée
* plan de développement détaillé

### Ce qui reste à implémenter

#### Offline (Python)

* implémentation complète du parser SVG
* heuristiques de mapping (patterns)
* rasterisation réelle (Inkscape / resvg)
* packer WXPK v1
* CLI fonctionnelle
* GUI PySide6 (orchestrateur)

#### Runtime (ESP)

* loader WXPK v1
* resolver assets
* parser JSON minimal
* implémentation complète des FX
* API publique stable

#### Qualité

* fixtures de non-régression
* CI (lint, validate, pack)

---

## 9) Ordre recommandé pour mener le projet à terme

1. Implémenter WXPK loader côté ESP
2. Implémenter packer WXPK côté Python
3. Valider un aller-retour minimal (1 SVG → 1 icône LVGL)
4. Implémenter les FX un par un
5. Finaliser la CLI
6. Ajouter les exemples ESP
7. Ajouter la non-régression

---

## 10) Critère de réussite

Le projet est considéré **abouti** lorsque :

* un SVG ajouté côté offline produit un pack valide
* ce pack est chargé sans modification du code ESP
* une icône animée s’affiche correctement sous LVGL
* les exemples compilent et tournent

---

## 11) Règles de contribution

* toute modification des contrats implique un bump de version
* aucune logique runtime ne doit dériver du SVG
* pas d’implémentation hors spécification

---

## 12) Statut

Le projet est **architecturalement complet**, mais **fonctionnellement en cours d’implémentation**.

Le README sert de **point d’entrée unique** pour tout développeur ou agent IA travaillant sur le projet.

---

## Mise à jour de cohérence (wx.spec v1 / WXPK v1)

Cette section aligne **plan.md** avec les documents normatifs sans introduire de conflit.

### Statut

* Le plan reste **valide conceptuellement**.
* Les adaptations ci-dessous sont **strictement de cohérence**, non fonctionnelles.

### Alignements appliqués

* **Sortie runtime figée** : toutes les références implicites à des structures ad‑hoc sont remplacées conceptuellement par **JSON `wx.spec v1`**.
* **Format de production** : toute mention de formats binaires génériques est à lire comme **`WXPK v1`**.
* **Résolution d’assets** : le chargement est réalisé par **`asset_hash` (FNV1a32) + TOC**, les enums restant optionnels (canon).
* **Ciblage FX** : les FX opèrent sur des **layers identifiés par `z`** via `target_z` uniquement.

### Clarification de périmètre

* Aucune analyse SVG n’est prévue côté runtime.
* Toute logique de découpe, d’inférence ou de mapping appartient à l’offline (Python).

### Non‑régression

* Aucun nouveau pattern, FX ou asset n’est introduit ici.
* Les patterns existants et leur API restent inchangés.

Cette mise à jour garantit la **compatibilité totale** de `plan.md` avec :

* `wx-pack-spec.md`
* `mapping-svg-pattern.md`
* `technical-choices.md`
* `assets-naming-and-packing.md`
* `agent.md`
