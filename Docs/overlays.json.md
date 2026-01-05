# Spécification overlays.json (v1.0)

Ce document décrit le format `overlays.json` généré par le pipeline. Il est destiné à l’ESP32/LVGL et reste strictement déterministe.

---

## 1. Vue d’ensemble

`overlays.json` décrit les animations paramétriques d’une icône. Chaque animation SVG admissible est convertie en un overlay LVGL.

Le fichier est **plat**, **versionné**, sans logique implicite.

---

## 2. Structure globale

```json
{
  "version": "1.0",
  "size": { "w": 150, "h": 150 },
  "palette": ["#fbbf24", "#ffffff"],
  "gradients": [ /* defs */ ],
  "static": [ /* éléments fixes */ ],
  "alpha": 255,
  "z_order": {
    "base_z_min": 0,
    "base_z_max": 12,
    "overlays_z_min": 13,
    "overlays_z_max": 21,
    "base_position": "below",
    "base_draw_order": "before",
    "overlays_z_offset": 13
  },
  "overlays": [
    { /* overlay */ }
  ]
}
```

### Champs

- `version` : version du format (string, `"1.0"`).
- `size` : dimensions finales en pixels (w, h).
- `palette` : liste unique des couleurs trouvées (fills, strokes, stops).
- `gradients` : définitions `linearGradient`/`radialGradient`.
- `static` : éléments fixes (non animés) avec leurs couleurs.
- `alpha` : opacité globale appliquée côté LVGL (0..255, optionnel).
- `z_order` : position de la base vs overlays (cf. section 6).
- `overlays` : liste des overlays (une entrée par animation).

---

## 3. Overlay (entrée de la liste)

```json
{
  "id": "sun_rays",
  "type": "rotate",
  "z": 7,
  "target": {
    "tag": "path",
    "attrs": {
      "d": "M ...",
      "stroke": "#fbbf24",
      "stroke-width": 3
    }
  },
  "anim": {
    "kind": "rotate",
    "dur_ms": 45000,
    "begin_ms": 0,
    "repeat": "indefinite",
    "values": [[0, 75, 75], [360, 75, 75]]
  }
}
```

### Champs

- `id` : identifiant stable (string). Si l’élément SVG n’avait pas d’id, un id auto est injecté.
- `type` : type d’animation (`rotate`, `translate`, `scale`, `opacity`).
- `z` : ordre de dessin (0 = premier élément **dessinable** du DOM). Croissant.
- `z_rel` : `z` relatif à `overlays_z_offset` (plus simple côté LVGL).
- `target` : description graphique de la cible (forme + attributs).
- `anim` : paramètres d’animation.

---

## 4. Palette / Gradients / Static

### palette

Liste unique des couleurs présentes dans le SVG :

- `fill`, `stroke` des éléments (animés ou statiques).
- `stop-color` des gradients.
- Les valeurs `none` sont ignorées.

### gradients

Définitions SVG utilisées par les overlays et/ou la base.

```json
{
  "id": "sun",
  "gradient_ref": "sun",
  "type": "linearGradient",
  "attrs": { "x1": "0", "y1": "0", "x2": "1", "y2": "1" },
  "stops": [
    { "offset": "0%", "stop-color": "#fbbf24", "stop-opacity": "1" }
  ]
}
```

### static

Liste des éléments **fixes** (non animés) avec leurs couleurs.

```json
{ "id": "sun_disk", "tag": "circle", "z": 3, "attrs": { "fill": "url(#sun)" } }
```

---

## 5. target

### Champs

- `tag` : type de forme (`line`, `circle`, `rect`, `image`, `ellipse`, `polygon`, `polyline`, `path`).
- `attrs` : attributs de forme, **déjà remappés** dans le repère 150×150 (ou taille cible).

### Attributs communs

- `fill`, `stroke`, `opacity`, `id`.
- `stroke-width` est remappé selon l’échelle X.
- `href` : référence normalisée (`href` ou `xlink:href` d’origine).
- `gradient_id` : identifiant normalisé sans `#`.
- `gradient_ref` : alias de `gradient_id` pour LVGL.

### Attributs géométriques (remappés)

- `x`, `y`, `x1`, `y1`, `x2`, `y2`, `cx`, `cy`, `r`, `rx`, `ry`, `width`, `height`.

### Spécifique `path`

- `d` : contenu du path, **remappé** du viewBox vers la taille cible.
- Par défaut, `--allow-path-overlay` est actif (désactivation via `--no-allow-path-overlay`).

---

## 6. anim

### Champs obligatoires

- `kind` : type d’animation (doit correspondre à `type`).
- `dur_ms` : durée en millisecondes.
- `begin_ms` : décalage en millisecondes (peut être négatif).
- `repeat` : `"indefinite"` uniquement.

### Champs optionnels

- `values` : liste de valeurs (ex: rotate ou translate).
- `from`, `to` : valeurs de départ/arrivée si `values` absent.

### Remappage des valeurs

- `rotate` : `[deg, cx, cy]` (cx/cy remappés viewBox → px).
- `translate` : `[dx, dy]` (dx/dy remappés viewBox → px).
- `scale` : valeurs conservées (pas de remappage).
- `opacity` : 0..1 (pas de remappage).

---

## 7. z_order

```json
"z_order": {
  "base_z_min": 0,
  "base_z_max": 12,
  "overlays_z_min": 13,
  "overlays_z_max": 21,
  "base_position": "below"
}
```

### Champs

- `base_z_min` / `base_z_max` : plage de z pour les éléments statiques.
- `overlays_z_min` / `overlays_z_max` : plage de z pour les éléments animés.
- `base_position` :
  - `below` : la base est entièrement sous les overlays.
  - `above` : la base est entièrement au-dessus.
  - `mixed` : intercalation (nécessite un découpage base multi-couches).
  - `all_static` : aucun overlay.
  - `none` : aucune base.
- `base_draw_order` : `before` (dessiner base puis overlays), `after` (dessiner overlays puis base), `mixed` (interdit en S2 mono-couche).
- `overlays_z_offset` : z minimal des overlays (permet de recalculer les z relatifs).

---

## 8. Validations minimales

- `version == "1.0"`.
- `size.w == size.h`.
- `overlays` est un tableau.
- `dur_ms > 0`, `repeat == "indefinite"`.
- `alpha` ∈ [0..255] si présent.
- `z` strictement croissant ou égal au z-order DOM (éléments dessinables uniquement).
- `base_position != mixed` pour S2 mono-couche.
- En mode strict, `base_position == mixed` déclenche une erreur.

---

## 9. Exemple minimal

```json
{
  "version": "1.0",
  "size": { "w": 150, "h": 150 },
  "z_order": {
    "base_z_min": 0,
    "base_z_max": 0,
    "overlays_z_min": 1,
    "overlays_z_max": 1,
    "base_position": "below"
  },
  "overlays": [
    {
      "id": "sun_rays",
      "type": "rotate",
      "z": 1,
      "z_rel": 0,
      "target": { "tag": "path", "attrs": { "d": "M ...", "stroke": "#fbbf24" } },
      "anim": { "kind": "rotate", "dur_ms": 45000, "begin_ms": 0, "repeat": "indefinite", "values": [[0, 75, 75], [360, 75, 75]] }
    }
  ]
}
```
