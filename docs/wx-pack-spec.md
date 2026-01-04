# wx-pack-spec.md — Spécification binaire WXPK v1

## 0) Portée

Ce document définit **la spécification binaire normative et unique** du format de pack **WXPK v1**.

Il fait autorité pour :

* la génération offline (Python)
* le chargement et l’interprétation runtime (ESP / LVGL)

Tout pack déclaré **WXPK v1** doit respecter strictement ce document. Toute autre description antérieure est obsolète.

---

## 1) Principes généraux

* Endianness : **little‑endian uniquement**
* Alignement : **4 bytes** pour toutes les sections
* Accès runtime : lecture directe mémoire (flash / mmap / buffer)
* Lookup logique unique : **TOC + clé `(key_hash, type, size_px)`**
* Format de production : **BIN uniquement**
* Vérité runtime : **JSON `wx.spec v1` embarqué**

---

## 2) Layout binaire global

```
+------------------------+
| wxpk_header_t (32B)    |
+------------------------+
| padding (0–3B)         |
+------------------------+
| TOC entries            |
| wxpk_toc_entry_t[n]    |
+------------------------+
| padding (0–3B)         |
+------------------------+
| blobs (images / json)  |
+------------------------+
```

* Tous les offsets sont **absolus depuis le début du fichier**.
* L’ordre des blobs est libre.

---

## 3) Header binaire

### 3.1 Structure `wxpk_header_t`

```c
#pragma pack(push,1)
typedef struct {
  uint32_t magic;        // 'W''X''P''K' = 0x4B505857
  uint16_t version;      // = 1 pour WXPK v1
  uint8_t  endian;       // 0 = little-endian
  uint8_t  header_size;  // sizeof(wxpk_header_t) = 32

  uint32_t flags;        // réservé (0 pour v1)

  uint32_t toc_offset;   // offset absolu vers la TOC
  uint32_t toc_count;    // nombre d’entrées TOC

  uint32_t blobs_offset; // offset absolu du premier blob

  uint32_t file_crc32;   // optionnel, 0 si non utilisé
} wxpk_header_t;
#pragma pack(pop)
```

### 3.2 Contraintes

* `magic` **doit** être `0x4B505857`
* `version` **doit** être `1`
* `header_size` **doit** être `32`
* `toc_offset >= header_size`
* `blobs_offset >= toc_offset + toc_count * sizeof(wxpk_toc_entry_t)`

---

## 4) Table des matières (TOC)

### 4.1 Structure `wxpk_toc_entry_t`

```c
#pragma pack(push,1)
typedef struct {
  uint32_t key_hash;   // asset_hash (image) ou spec_id (JSON spec)
  uint8_t  type;       // wxpk_entry_type_t
  uint8_t  codec;      // wxpk_codec_t
  uint16_t size_px;    // 64/96/128, 0 pour JSON

  uint32_t offset;     // offset absolu du blob
  uint32_t length;     // taille du blob en bytes
  uint32_t crc32;      // CRC32 du blob

  uint32_t meta;       // réservé (0 pour v1)
} wxpk_toc_entry_t;
#pragma pack(pop)
```

* Taille fixe : **28 bytes**
* Clé de lookup runtime : `(key_hash, type, size_px)`

---

### 4.2 Types d’entrées (`type`)

```c
typedef enum {
  WXPK_T_IMG        = 1,  // image
  WXPK_T_JSON_INDEX = 2,  // index JSON global (optionnel)
  WXPK_T_JSON_SPEC  = 3,  // spec wx.spec v1 (1 par preset)
  WXPK_T_JSON_ALL   = 4   // JSON global monolithique (optionnel)
} wxpk_entry_type_t;
```

---

### 4.3 Codecs image (`codec`)

```c
typedef enum {
  WXPK_C_NONE          = 0,
  WXPK_C_LVGL_BIN      = 1, // recommandé production
  WXPK_C_PNG           = 2, // nécessite décodeur LVGL
  WXPK_C_RAW_RGBA8888  = 3
} wxpk_codec_t;
```

---

## 5) Convention des clés et hashing

### 5.1 Asset key

* Identifiant **canonique** d’un asset
* Contraintes obligatoires :

  * minuscules uniquement
  * UTF‑8
  * regex autorisée : `[a-z0-9_]+`

Toute violation est une **erreur bloquante** (outil offline / CI).

---

### 5.2 Asset hash

* `asset_hash = FNV1a32(asset_key normalisé)`
* Algorithme **figé**

Conséquences :

* `asset_hash` est la **clé primaire runtime**
* le runtime ne dépend jamais du nom texte

---

### 5.3 Images

* `type = WXPK_T_IMG`
* `key_hash = asset_hash`
* `size_px` **obligatoire** (64 / 96 / 128)

---

### 5.4 Specs JSON

* `type = WXPK_T_JSON_SPEC`
* `key_hash = spec_id` (u32 direct, **pas de hash**)
* `size_px = 0`

Ce choix est **définitif**.

---

## 6) Blobs

* Les blobs sont stockés **bruts**, sans compression additionnelle
* Chaque blob commence à l’offset indiqué dans la TOC

### 6.1 Images

* Un blob = une image pour une taille donnée
* Codec recommandé : `WXPK_C_LVGL_BIN`
* PNG autorisé uniquement si un décodeur est présent

### 6.2 JSON

* Encodage UTF‑8
* Format : **`wx.spec v1` uniquement**
* Vérité runtime absolue

Organisation recommandée :

* une entrée TOC par spec (`WXPK_T_JSON_SPEC`)
* optionnel : un index JSON global (`WXPK_T_JSON_INDEX`)

---

## 7) CRC et validation

* `crc32` calculé sur le blob uniquement
* Le runtime **doit refuser** :

  * CRC invalide
  * offsets hors fichier
  * types inconnus

---

## 8) Algorithme de lookup runtime

```
find(type, key_hash, size_px):
  for entry in TOC:
    if entry.type == type
       and entry.key_hash == key_hash
       and entry.size_px == size_px:
         return entry
  return NULL
```

* TOC triée + dichotomie autorisée
* Aucun autre mécanisme implicite n’est autorisé

---

## 9) Vérité runtime et séparation des responsabilités

### 9.1 Vérité runtime

* La **seule vérité runtime** est le JSON `wx.spec v1`
* Toute logique d’icône (layers, FX, paramètres) est décrite dans ce JSON
* Le runtime ESP/LVGL ne contient **aucune heuristique métier**

---

### 9.2 Séparation stricte

**Offline (Python)** :

* analyse SVG
* découpe en calques
* génération des assets image
* génération des specs JSON `wx.spec v1`
* génération du pack `WXPK v1`

**Runtime (ESP / LVGL)** :

* chargement du pack
* résolution via TOC `(asset_hash, size_px, type)`
* interprétation stricte du JSON
* affichage LVGL + FX

Aucune analyse SVG n’est autorisée côté runtime.

---

## 10) Règles contractuelles JSON `wx.spec v1`

* `asset_key` normalisé `[a-z0-9_]+`
* `asset_hash = FNV1a32(asset_key)`
* calques identifiés par `z` (ID stable, unique)
* tous les FX ciblent **exclusivement** via `target_z`
* le champ `fx` contient **toutes** les clés attendues (tableaux vides si inutilisées)

---

## 11) Versioning et compatibilité

* Toute rupture de compatibilité implique :

  * bump de version (`WXPK` ou `wx.spec`)
  * mise à jour documentaire
  * régénération complète des packs

* Tout renommage d’`asset_key` sans bump est une **rupture ABI**.

---

## 12) Décisions figées

Les points suivants sont **définitifs** :

* `WXPK v1` est la seule norme binaire valide
* `wx.spec v1` est la vérité runtime
* lookup exclusif par TOC
* enums `WX_ASSET_*` non contractuels
* codec image de production recommandé : `LVGL_BIN`
* core ESP strictement interprétatif

Toute évolution incompatible impose une révision explicite et un bump de version.
