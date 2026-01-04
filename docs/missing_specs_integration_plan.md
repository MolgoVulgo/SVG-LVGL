# missing-specs-and-integration-plan.md — Spécifications manquantes et plan d'intégration

## 0) Portée et rôle

Ce document **complète les spécifications existantes** afin de rendre le projet **WX Toolchain** totalement développable et industrialisable.  
Il a pour objet de :

* Définir formellement le schéma JSON `wx.spec v1` et sa contrepartie runtime `wx_icon_spec_t`.
* Uniformiser les interfaces Python internes (entrées/sorties normalisées).
* Décrire le pipeline complet de transformation (SVG → JSON → PNG → WXPK → Runtime LVGL).
* Introduire un cadre de validation et de tests unitaires.

Ce document est **normatif** et **supplante toute interprétation implicite** des autres fichiers.

---

## 1) Schéma JSON `wx.spec v1`

### 1.1 Objectif

Le format `wx.spec v1` décrit l’identité, la composition et les effets visuels d’une icône météo (ou instrument) sous une forme exploitable offline et runtime.

Chaque spécification correspond à **une instance unique** de `wx_icon_spec_t`.

### 1.2 Structure JSON (normative)

```json
{
  "spec_id": 1003,
  "name": "partly_cloudy_day_rain",
  "components": {
    "decor": "SUN",
    "cover": "CLOUD",
    "particles": "RAIN",
    "atmos": "NONE",
    "event": "NONE"
  },
  "layers": [
    { "id": "sun_core", "asset": "sun_core", "fx": [] },
    { "id": "sun_rays", "asset": "sun_rays", "fx": ["ROTATE"] },
    { "id": "cloud", "asset": "cloud", "fx": ["DRIFT"] },
    { "id": "drop", "asset": "drop", "fx": ["FALL"] }
  ],
  "fx": {
    "ROTATE": { "period_ms": 45000, "pivot_x": 32, "pivot_y": 32 },
    "FALL": {
      "period_ms": 700,
      "fall_dy": 15,
      "opa_min": 0,
      "opa_max": 255,
      "phase_ms": [0,200,400]
    },
    "DRIFT": { "period_ms": 10000, "amp_x": 1, "amp_y": 0 }
  },
  "metadata": {
    "version": 1,
    "created_by": "wx-toolchain",
    "confidence": 0.95
  }
}
```

### 1.3 Contraintes

* `spec_id` : `uint32_t` unique, déterministe (voir §4.4)
* `name` : regex `[a-z0-9_]+`
* `components` : tous les champs requis
* `layers` : au moins 1
* `fx` : clés issues de `wx-fx-contracts.md`
* `metadata.version` = 1 obligatoire

---

## 2) Structure C `wx_icon_spec_t`

### 2.1 Définition C (normative)

```c
#pragma pack(push,1)
typedef struct {
  uint32_t spec_id;             // Identifiant unique (aligné sur JSON)
  uint8_t decor;                // wx_decor_t enum
  uint8_t cover;                // wx_cover_t enum
  uint8_t particles;            // wx_particles_t enum
  uint8_t atmos;                // wx_atmos_t enum
  uint8_t event;                // wx_event_t enum

  uint8_t layer_count;          // Nombre total de calques
  wx_layer_spec_t layers[8];    // Définition des calques

  wx_fx_spec_t fx[WX_FX_COUNT]; // Paramètres FX normalisés

  uint32_t confidence_x1000;    // Confiance *1000 (0..1000)
} wx_icon_spec_t;
#pragma pack(pop)
```

### 2.2 Structures associées

```c
typedef struct {
  char asset_key[32];           // nom canonique de l'asset
  uint8_t fx_mask;              // bitmask des FX appliqués
} wx_layer_spec_t;

typedef struct {
  uint16_t period_ms;
  int16_t amp_x, amp_y, fall_dy;
  uint16_t pivot_x, pivot_y;
  uint8_t opa_min, opa_max;
  uint8_t phase_count;
  uint16_t phase_ms[6];
} wx_fx_spec_t;
```

### 2.3 Invariants d'implémentation

* `sizeof(wx_icon_spec_t)` ≤ 512 bytes
* Tous les angles exprimés en dixièmes de degré LVGL (`0..3600`)
* `opa_min/opa_max` ∈ [0..255]
* Les phases sont optionnelles si `phase_count=0`

---

## 3) API interne Python (offline)

### 3.1 Interfaces de module normalisées

#### Module `tools.wx.svg.parser`
```python
def parse_svg(path: str) -> SvgDoc:
    """Charge un SVG, normalise le viewBox, renvoie un objet SvgDoc."""
```

#### Module `tools.wx.semantic.mapper`
```python
def map_to_spec(svg: SvgDoc, filename: str) -> dict:
    """Applique les heuristiques SMIL + forme + couleur pour produire un wx.spec v1."""
```

#### Module `tools.wx.plan.layers`
```python
def build_layer_plan(spec: dict) -> list:
    """Retourne la liste des calques (nom, fx, asset)."""
```

#### Module `tools.wx.export.raster`
```python
def export_png_layers(plan: list, sizes: list[int], out_dir: str):
    """Rasterise les calques pour chaque taille (64/96/128)."""
```

#### Module `tools.wx.pack.wxpk`
```python
def pack_to_wxpk(manifest: dict, specs: list[dict], out_path: str):
    """Assemble un pack binaire conforme WXPK v1."""
```

### 3.2 Exceptions normalisées

| Exception | Cause |
|------------|--------|
| `InvalidSvgError` | SVG non lisible ou corrompu |
| `MappingError` | Aucun pattern détecté |
| `ValidationError` | Spéc JSON non conforme au schéma |
| `ExportError` | Inkscape ou lv_img_conv en échec |
| `PackError` | CRC ou TOC incohérents |

### 3.3 Sorties standard

* `out/specs/` → fichiers `.json`
* `out/png/` → images rasterisées
* `out/pack/` → `wxpk_v1.bin`

---

## 4) Pipeline d’intégration (SVG → LVGL)

### 4.1 Chaîne normative

```text
[SVG] → parse_svg() → map_to_spec() → build_layer_plan()
       → export_png_layers() → lv_img_conv() → pack_to_wxpk()
       → [WXPK v1] → wxpk_open() → wx_icon_create_from_spec()
```

### 4.2 Règles de validation

1. Chaque spec JSON doit être **validée par le schéma officiel** avant inclusion dans le pack.
2. Les assets exportés doivent être **plein cadre + transparents**.
3. Les CRC doivent être recalculés post-pack.

### 4.3 Identifiants déterministes

* `spec_id = FNV1a32(name)`
* `asset_hash = FNV1a32(asset_key)`

Garantit la reproductibilité entre builds.

---

## 5) Jeux de tests et validation

### 5.1 Fixtures obligatoires

| Nom | Type | But |
|------|------|-----|
| `clear_day.svg` | SVG | Test de rotation lente (ROTATE) |
| `partly_cloudy_day_rain.svg` | SVG | Test multi-FX (ROTATE + FALL + DRIFT) |
| `barometer.svg` | SVG | Test pivot + rotation aiguille |

### 5.2 Validation offline

* Comparaison des `wx.spec v1` générés avec références connues.
* Vérification des hash et CRC des packs.

### 5.3 Validation runtime

* Instanciation automatique de chaque spec dans LVGL.
* Comparaison des comportements FX (durée, amplitude, phase).

---

## 6) Annexes

### 6.1 Exemple complet (preset `partly_cloudy_day_rain`)

**JSON `wx.spec v1` :**
```json
{
  "spec_id": 0x1A2B3C4D,
  "name": "partly_cloudy_day_rain",
  "components": { "decor": "SUN", "cover": "CLOUD", "particles": "RAIN", "atmos": "NONE", "event": "NONE" },
  "layers": [
    { "id": "sun_core", "asset": "sun_core", "fx": [] },
    { "id": "sun_rays", "asset": "sun_rays", "fx": ["ROTATE"] },
    { "id": "cloud", "asset": "cloud", "fx": ["DRIFT"] },
    { "id": "drop", "asset": "drop", "fx": ["FALL"] }
  ],
  "fx": {
    "ROTATE": { "period_ms": 45000 },
    "DRIFT": { "period_ms": 10000, "amp_x": 1, "amp_y": 0 },
    "FALL": { "period_ms": 700, "fall_dy": 15, "phase_ms": [0,200,400] }
  }
}
```

**Structure C équivalente :**
```c
wx_icon_spec_t spec = {
  .spec_id = 0x1A2B3C4D,
  .decor = WX_DECOR_SUN,
  .cover = WX_COVER_CLOUD,
  .particles = WX_PART_RAIN,
  .atmos = WX_ATMOS_NONE,
  .event = WX_EVENT_NONE,
  .layer_count = 4,
  .layers = {
    {"sun_core", 0},
    {"sun_rays", FX_ROTATE},
    {"cloud", FX_DRIFT},
    {"drop", FX_FALL}
  },
  .fx = {
    [FX_ROTATE] = {.period_ms=45000, .pivot_x=32, .pivot_y=32},
    [FX_DRIFT]  = {.period_ms=10000, .amp_x=1},
    [FX_FALL]   = {.period_ms=700, .fall_dy=15, .phase_ms={0,200,400}}
  },
  .confidence_x1000 = 950
};
```

### 6.2 Correspondance JSON → C

| JSON Key | C Field | Type |
|-----------|----------|------|
| `spec_id` | `spec_id` | `uint32_t` |
| `fx.ROTATE.period_ms` | `fx[FX_ROTATE].period_ms` | `uint16_t` |
| `layers[].asset` | `layers[].asset_key` | `char[32]` |
| `metadata.confidence` | `confidence_x1000` | `uint32_t` |

---

## 7) Dispositions finales

* Ce document est **ajouté à `/docs/` comme référence normative**.
* Toute modification du schéma `wx.spec v1` doit entraîner un **incrément majeur de version** et une mise à jour de la TOC WXPK.
* Les exemples fournis sont **compatibles ESP32 / LVGL 8.3**.

---

**Fin du document.**

