# Plan d’actions detaille — Alignement code / documentation

## 0) Pre-requis

- Verifier que `docs/*.md` et `README.md` sont la source normative finale.
- Geler le perimetre: offline (Python) + runtime (C LVGL) + tests.

---

## 1) Alignement du schema `wx.spec v1`

### 1.1 Modeles Python

- Remplacer `Spec` par une structure conforme:
  - `spec_id` (uint32), `name` (regex `[a-z0-9_]+`)
  - `components` (decor/cover/particles/atmos/event)
  - `layers[]` (id, asset, fx[])
  - `fx` (dictionnaire FX avec champs normatifs)
  - `metadata.version` obligatoire (=1)
- Supprimer `size_px` du schema JSON (hors spec normative).
- Conserver `assets` uniquement si un format interne est necessaire, sinon enlever du JSON runtime.
- Refactorer `pipeline/spec/model.py` + `pipeline/wxspec.py` + validateurs.

### 1.2 Validation

- Implementer les contraintes:
  - `spec_id` deterministe et unique (regle a definir).
  - `name` conforme.
  - `layers` >= 1.
  - `fx` uniquement cles de `wx-fx-contracts.md`.
- Adapter `pipeline/validation/fx.py` au nouveau schema.

### 1.3 Tests

- Mettre a jour `tests/test_validation.py` pour le nouveau schema.
- Ajouter tests sur `spec_id`, `name`, `metadata.version`, `layers` et `fx`.

---

## 2) Alignement WXPK v1 (binaire)

### 2.1 Format header / toc

- Reimplenter `pipeline/wxpk.py` selon `docs/wx-pack-spec.md`:
  - `wxpk_header_t` (magic, version, endian, header_size, flags, toc_offset, toc_count, blobs_offset, file_crc32)
  - Alignement 4 bytes.
  - TOC avec `type`, `codec`, `size_px`, `offset`, `length`, `crc32`, `meta`.
- Introduire l’enum type (`WXPK_T_IMG`, `WXPK_T_JSON_SPEC`, etc.) + codec.

### 2.2 Blobs JSON

- Creer une entree TOC par spec JSON (type `WXPK_T_JSON_SPEC`, key_hash = `spec_id`, size_px=0).
- Optionnel: entree `WXPK_T_JSON_INDEX` ou `WXPK_T_JSON_ALL` si retenu.

### 2.3 Runtime

- Aligner `runtime/src/wx_pack.c`:
  - lecture header conforme
  - lecture TOC
  - lookup par `(key_hash, type, size_px)`
  - suppression de `json_offset/json_size` hors spec
- Mettre a jour `runtime/include/wx_pack.h` pour exposer un resolveur (ex: `wx_pack_find_entry`).

### 2.4 Tests

- Mettre a jour `tests/test_wxpk.py` pour le format normative:
  - header fields
  - toc entries
  - alignement 4 bytes
  - extraction spec JSON par `spec_id`.

---

## 3) Alignement des FX

### 3.1 Schema FX

- Remplacer les champs internes (`speed_dps`, `speed_pps`) par les champs normatifs:
  - `period_ms`, `pivot_x`, `pivot_y`, `fall_dy`, `amp_x`, `amp_y`, `opa_min`, `opa_max`, `phase_ms[]`, etc.
- Mettre a jour `pipeline/spec/model.py` + `pipeline/validation/fx.py`.

### 3.2 Runtime

- Mettre a jour `runtime/include/wx_fx.h` pour exposer les structs FX conformes.
- Preparer stubs d’application FX (meme si non implemente).

---

## 4) Alignement API runtime

- Modifier `runtime/include/wx_icon.h` pour coller a l’API cible:
  - `wx_icon_create_from_spec_id(parent, pack, spec_id, size_px)`
  - `wx_icon_destroy`
  - `wx_icon_apply_spec` ou `wx_icon_update_from_json`.
- Mettre a jour `runtime/src/wx_icon.c` en coherance.
- Supprimer l’API obsolette si non retenue.

---

## 5) Migration des outils offline

- Adapter les modules existants pour produire le nouveau JSON `wx.spec v1`.
- Conserver un format interne si necessaire, mais generer le schema normatif en sortie.
- Mettre a jour `pipeline/cli.py` si des sorties JSON sont exposees.

---

## 6) Verification finale

- Repasser une revue de coherence:
  - `docs/*` vs `pipeline/*`
  - `docs/*` vs `runtime/*`
- Executer les tests unitaires.
- Lister les ecarts restants (si existants).
