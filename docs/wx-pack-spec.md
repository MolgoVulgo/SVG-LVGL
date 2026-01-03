## Statut du document

Ce document est un **catalogue logique et documentaire**.

* Il décrit les **familles de presets**, leurs intentions visuelles et leurs compositions.
* Il **ne définit pas** de code runtime.
* Il **ne constitue pas** une API C.

Les presets **runtime effectifs** sont matérialisés par des **specs JSON `wx.spec v1`**, produites offline et embarquées dans les packs `WXPK`.

Aucun preset n’est codé en dur côté C.

---

## Mise à jour normative — JSON runtime `wx.spec` v1

### Statut

* La sortie JSON décrite dans ce document est désormais la **vérité runtime**.
* Le runtime ESP/LVGL consomme ce JSON (directement ou via pack WXPK), sans aucune interprétation SVG.
* La spécification formelle (schéma + signatures FX + pack) est définie dans **`wx-pack-spec.md`**.

### Règles obligatoires

* `asset_key` **normalisé** : minuscules uniquement, regex `[a-z0-9_]+` (UTF-8). Toute violation = erreur.
* `asset_hash = FNV1a32(asset_key)`.
* Les calques (`layers`) sont identifiés par `z` (ID **stable runtime**), unique par spec.
* Tous les FX ciblent via `target_z` uniquement.
* Le champ `fx` contient **toutes** les clés FX attendues (tableaux vides si non utilisées).

### Dépréciation

* Tous les exemples JSON antérieurs non conformes à `wx.spec v1` sont **obsolètes** et ne doivent plus être utilisés.
* Se référer à **`wx-pack-spec.md`** pour l’exemple normatif et le schéma figé.

---

# add-fonct — Format de sortie BIN (WXPK v1)

## 0) Portée

Ce document définit **le format de sortie BIN officiel** du projet.
Il remplace toute spécification antérieure.

Le format adopté est **WXPK v1**, tel que défini dans `wx-pack-spec.md`.

---

## 1) Décision structurante

* **BIN est le format de production**.
* Le **JSON runtime (wx.spec v1)** est **embarqué dans le pack**.
* Le runtime ESP/LVGL **ne consomme que le pack** (pas de fichiers externes).

Mode recommandé : **specs JSON splittées** (une entrée par icône).

---

## 2) Format WXPK v1 (normatif)

### 2.1 Header

Le header est strictement conforme à la structure suivante :

* Type : `wxpk_header_t`
* Taille : **32 bytes** (fixe)

Voir définition exacte dans `wx-pack-spec.md`.

---

### 2.2 Table des matières (TOC)

Chaque entrée TOC est strictement conforme à :

* Type : `wxpk_toc_entry_t`
* Taille : **28 bytes** (fixe)

Clé de lookup logique : `(key_hash, type, size_px)`.

---

## 3) Convention des clés (key_hash)

### 3.1 Images (WXPK_T_IMG)

* `key_hash = FNV1a32(asset_key)`
* `asset_key` **doit être normalisé** avant hash :

  * minuscules uniquement
  * regex autorisée : `[a-z0-9_]+`
  * UTF-8

Toute violation est une **erreur bloquante CI**.

---

### 3.2 Specs JSON (WXPK_T_JSON_SPEC)

* `key_hash = spec_id` (u32 direct, **pas de hash**)
* Lookup direct, sans collision.

Ce choix est **figé**.

---

## 4) JSON runtime embarqué

### 4.1 Nature du JSON

* Format : **wx.spec v1**
* Vérité runtime
* Produit exclusivement par l’outil offline Python

### 4.2 Organisation recommandée

* Une entrée TOC par spec (`WXPK_T_JSON_SPEC`)
* Optionnel : un index JSON global (`WXPK_T_JSON_INDEX`)

Avantages :

* chargement partiel
* faible empreinte mémoire

---

## 5) Règles de compatibilité

* `wxpk_header.version` doit correspondre à la version supportée par le runtime.
* Toute modification breaking implique :

  * bump de version WXPK
  * régénération complète des packs

---

## 6) Résumé exécutable

* **WXPK v1** est la seule norme valide
* Header = 32 bytes (`wxpk_header_t`)
* TOC entry = 28 bytes (`wxpk_toc_entry_t`)
* Images : lookup par `FNV1a32(asset_key)`
* Specs : lookup par `spec_id`
* JSON runtime embarqué (specs splittées recommandées)
* `asset_key` normalisé `[a-z0-9_]+`

---

## Décisions figées (rappel runtime)

Les points suivants sont considérés **définitifs** :

* **JSON runtime `wx.spec v1` est la vérité d’exécution**.

  * Toute logique d’icône, de calques et de FX est décrite dans le JSON.
  * Le runtime ESP/LVGL ne contient aucune heuristique métier.

* **BIN `WXPK v1` est le format de production**.

  * Les assets image et les specs JSON sont embarqués dans le pack.
  * Le runtime charge exclusivement depuis le pack.

* **Lookup des assets par `asset_hash + TOC`**.

  * `asset_hash = FNV1a32(asset_key normalisé)`.
  * La table des matières (TOC) est l’unique mécanisme de résolution en production.

* **Enums `WX_ASSET_*` réservés au canon**.

  * Utilisés uniquement comme optimisation ou raccourci.
  * Le runtime ne doit jamais dépendre fonctionnellement d’un enum.

* **Codec image de production recommandé : `LVGL_BIN`**.

  * PNG autorisé uniquement si un décodeur LVGL est présent.

* **Rôle du core ESP strictement interprétatif**.

  * Le core ESP/LVGL interprète : JSON `wx.spec v1` + pack `WXPK v1`.
  * Il n’analyse jamais de SVG.
  * Toute analyse, découpe ou décision sémantique est **exclusivement offline (Python)**.

Toute modification de ces points implique une révision explicite de l’architecture et un bump de version.

---

## Asset keys & hashing

### Asset key (identifiant canonique)

* `asset_key` est l’identifiant **canonique** d’un asset.
* Il est utilisé pour le packaging, le hashing et le lookup runtime.

Contraintes **obligatoires** :

* minuscules uniquement
* UTF-8
* regex autorisée : `[a-z0-9_]+`

Toute violation est une **erreur bloquante** (CI / outil offline).

---

### Asset hash

* `asset_hash = FNV1a32(asset_key)`
* L’algorithme de hash est **figé** (voir `wx-pack-spec.md`).

Conséquences :

* `asset_hash` est la **clé primaire runtime** pour la résolution d’images.
* Le runtime ne dépend jamais du nom texte.

---

### Stabilité et versioning

* Tout **renommage** d’un `asset_key` existant est **interdit** sans :

  * bump de version du pack (WXPK)
  * régénération complète des assets

Un renommage sans bump est considéré comme une **rupture ABI**.

---

### Résolution runtime

Le resolver runtime repose exclusivement sur :

* `asset_hash`
* `size_px`
* `type` (image / spec)

Aucun autre mécanisme implicite n’est autorisé en production.

---

## Mise à jour normative — Règles d’exécution du projet

### Vérité runtime

* La **seule vérité runtime** est le JSON **`wx.spec v1`**.
* Toute logique d’icône (layers, FX, paramètres) doit être exprimée dans ce JSON.
* Le format de production est **`WXPK v1`** (pack BIN).

### Rôle strict de l’IA (Codex)

L’IA agit comme **agent d’ingénierie déterministe** :

* elle **ne code pas de presets en dur côté C**
* elle **ne déduit jamais** de logique runtime à partir du SVG côté ESP
* elle applique les contrats existants sans extrapolation

### Séparation des responsabilités

* **Offline (Python)** :

  * analyse SVG
  * découpe en calques
  * génération des assets image
  * génération des specs JSON `wx.spec v1`
  * génération du pack `WXPK v1`

* **Runtime (ESP / LVGL)** :

  * chargement du pack
  * résolution des assets par `(asset_hash, size_px, type)`
  * interprétation stricte des specs JSON
  * affichage LVGL + FX

Aucune logique SVG, sémantique ou heuristique n’est autorisée côté runtime.

### Règles contractuelles à respecter

* `asset_key` doit être normalisé `[a-z0-9_]+`
* `asset_hash = FNV1a32(asset_key)`
* les FX ciblent **exclusivement** via `target_z`
* toutes les clés FX sont présentes dans le JSON (tableaux vides si inutilisées)

### Posture de réponse attendue

* toutes les réponses sont en **français**
* ton **technique, direct, non pédagogique**
* aucune suggestion hors périmètre
* aucune réécriture implicite des contrats

### Gestion des évolutions

* toute modification breaking implique :

  * bump de version (`wx.spec` ou `WXPK`)
  * mise à jour documentaire
  * régénération complète des packs

L’IA doit signaler explicitement toute demande incompatible avec ces règles.
