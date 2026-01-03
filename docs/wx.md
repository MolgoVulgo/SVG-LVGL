# wx.md

Spec JSON wx.spec v1 (detaillee)

## 1) Vue d'ensemble
Le JSON wx.spec v1 est la verite runtime. Il decrit une icone animee sous forme de layers, assets, et FX.
Le runtime ESP/LVGL ne fait que charger ce JSON et le pack WXPK v1.

## 2) Regles globales
- version: "wx.spec.v1" obligatoire.
- asset_key normalise [a-z0-9_]+.
- asset_hash = FNV1a32(asset_key).
- lookup runtime par (asset_hash, size_px, type).
- FX ciblent via target_z.
- toutes les cles FX sont presentes dans le JSON (meme si desactives).

## 3) Schema JSON (structure)

### 3.1 Racine
```json
{
  "version": "wx.spec.v1",
  "id": "cloud_sun",
  "size_px": 96,
  "assets": [ ... ],
  "layers": [ ... ],
  "fx": { ... }
}
```

Champs racine:
- version (string, obligatoire): toujours "wx.spec.v1".
- id (string, obligatoire): identifiant logique de l'icone.
- size_px (int, obligatoire): taille nominale de rendu (64, 96, 128).
- assets (array, obligatoire): inventaire des assets utilises.
- layers (array, obligatoire): description des layers ordonnes par z.
- fx (object, obligatoire): dictionnaire complet des FX contractuels.

### 3.2 Assets
```json
{
  "asset_key": "cloud_main",
  "asset_hash": 123456789,
  "type": "image",
  "size_px": 96,
  "path": "cloud_main_96.bin"
}
```

Champs asset:
- asset_key (string, obligatoire): nom logique normalise.
- asset_hash (uint32, obligatoire): FNV1a32(asset_key).
- type (string, obligatoire): "image" | "mask" | "alpha".
- size_px (int, obligatoire): taille en pixels.
- path (string, obligatoire): chemin relatif dans le pack (ou nom de ressource).

### 3.3 Layers
```json
{
  "z": 10,
  "asset_key": "cloud_main",
  "x": 0,
  "y": 0,
  "w": 96,
  "h": 96,
  "pivot_x": 48,
  "pivot_y": 48,
  "opacity": 255
}
```

Champs layer:
- z (int, obligatoire): ordre d'empilement.
- asset_key (string, obligatoire): reference vers assets[].asset_key.
- x, y (int, obligatoire): position locale.
- w, h (int, obligatoire): dimensions de l'asset.
- pivot_x, pivot_y (int, obligatoire): pivot pour rotation/animation.
- opacity (int, obligatoire): 0..255.

### 3.4 FX (dictionnaire complet)
Le champ fx est un objet contenant toutes les cles FX, meme si une FX est inactive.
Une FX inactive a "enabled": false.

Clés FX contractuelles:
- ROTATE
- FALL
- FLOW_X
- JITTER
- DRIFT
- TWINKLE
- FLASH
- CROSSFADE
- NEEDLE

Exemple:
```json
"fx": {
  "ROTATE": { "enabled": true, "target_z": 20, "speed_dps": 15 },
  "FALL": { "enabled": false, "target_z": 0, "speed_pps": 0 },
  "FLOW_X": { "enabled": false, "target_z": 0, "speed_pps": 0, "range_px": 0 },
  "JITTER": { "enabled": false, "target_z": 0, "amp_px": 0 },
  "DRIFT": { "enabled": false, "target_z": 0, "amp_px": 0, "speed_pps": 0 },
  "TWINKLE": { "enabled": false, "target_z": 0, "period_ms": 0 },
  "FLASH": { "enabled": false, "target_z": 0, "period_ms": 0 },
  "CROSSFADE": { "enabled": false, "target_z": 0, "period_ms": 0 },
  "NEEDLE": { "enabled": false, "target_z": 0, "min_deg": 0, "max_deg": 0 }
}
```

## 4) Contraintes et validation
- asset_hash doit correspondre a asset_key.
- layers[].asset_key doit exister dans assets[].asset_key.
- target_z doit referencer un z present dans layers[].z.
- size_px doit etre coherente avec les assets references.

## 5) Exemple minimal
```json
{
  "version": "wx.spec.v1",
  "id": "clear_day",
  "size_px": 96,
  "assets": [
    { "asset_key": "sun", "asset_hash": 123, "type": "image", "size_px": 96, "path": "sun_96.bin" }
  ],
  "layers": [
    { "z": 10, "asset_key": "sun", "x": 0, "y": 0, "w": 96, "h": 96, "pivot_x": 48, "pivot_y": 48, "opacity": 255 }
  ],
  "fx": {
    "ROTATE": { "enabled": true, "target_z": 10, "speed_dps": 12 },
    "FALL": { "enabled": false, "target_z": 0, "speed_pps": 0 },
    "FLOW_X": { "enabled": false, "target_z": 0, "speed_pps": 0, "range_px": 0 },
    "JITTER": { "enabled": false, "target_z": 0, "amp_px": 0 },
    "DRIFT": { "enabled": false, "target_z": 0, "amp_px": 0, "speed_pps": 0 },
    "TWINKLE": { "enabled": false, "target_z": 0, "period_ms": 0 },
    "FLASH": { "enabled": false, "target_z": 0, "period_ms": 0 },
    "CROSSFADE": { "enabled": false, "target_z": 0, "period_ms": 0 },
    "NEEDLE": { "enabled": false, "target_z": 0, "min_deg": 0, "max_deg": 0 }
  }
}
```
