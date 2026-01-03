# Mapping automatique SVG → Pattern (LVGL)

## 0) Objectif

À partir d’un SVG (fichier texte), produire automatiquement :

1. un **pattern** (ou une **composition** de patterns) parmi ceux du framework (rotation, fall, flow_x, jitter, twinkle, flash, drift, crossfade, needle…)
2. un **wx_icon_spec_t** (ou un preset) prêt à instancier
3. les **recommandations de découpe en calques** + exports PNG requis (assets)

Contrainte : le mapping vise la **robustesse** (pas la perfection sémantique). Il doit couvrir 95% des icônes météo par heuristiques explicites.

---

## 1) Entrées / sorties

### Entrées

* Contenu SVG brut
* (Optionnel) nom de fichier (utile : `partly-cloudy-night-rain.svg` donne un prior)

### Sorties

* `wx_icon_spec_t` complet (structure + params)
* Liste d’assets nécessaires (`wx_asset_id_t[]`) + nombre d’instances
* Plan de découpe “calques” (quels éléments SVG vont dans quel PNG)
* Rapport de confiance + raisons (audit)

---

## 2) Stratégie : heuristiques en 3 étages

### Étape A — Détection d’animations (SMIL)

Analyser les balises : `animate`, `animateTransform`. Extraire par animation :

* type : `rotate | translate | scale | opacity`
* cible : element id (ou parent `<g>`)
* durée : `dur`
* begin : `begin`
* valeurs : `values` (+ éventuellement `keyTimes`, `keySplines`)

Décision rapide :

* `animateTransform(type=rotate)` → **WX_FX_ROTATE**
* `animateTransform(type=translate)` + `animate(opacity)` sur même cible → **WX_FX_FALL**
* `animateTransform(type=translate)` sans opacity, amplitude faible → **WX_FX_JITTER** ou **WX_FX_DRIFT**
* `animateTransform(type=scale)` non-uniforme ("1 0.9") → **WX_FX_CROSSFADE**
* `animate(attributeName=opacity)` répétée sur plusieurs petits éléments → **WX_FX_TWINKLE**
* `opacity 0→1→0` très court → **WX_FX_FLASH**

### Étape B — Détection “formes” (sémantique météo)

Heuristiques via géométrie + styles :

* **Soleil** : présence d’un `circle` jaune/orange + plusieurs rayons (paths autour) → `WX_DECOR_SUN` (+ FX rotate si SMIL rotate)
* **Lune** : path/circle gris/bleu clair, forme croissant (souvent 2 arcs) → `WX_DECOR_MOON`
* **Nuage** : path volumique gris clair, grande surface, souvent `fill` neutre → `WX_COVER_CLOUD`
* **Pluie / bruine** : plusieurs `line` verticales avec stroke bleu/cyan, parfois gradients → `WX_PART_RAIN` / `WX_PART_DRIZZLE`
* **Neige** : petits cercles/étoiles/flocons blancs → `WX_PART_SNOW`
* **Grêle** : petits disques denses, chute rapide → `WX_PART_HAIL`
* **Éclair** : path polygonal jaune (zigzag) → `lightning` présent
* **Haze/Smoke/Mist** : multiples lignes horizontales/voiles semi-transparents, strokes gris → `WX_ATMOS_*`
* **Vent poussière** : courbes horizontales + sable/gris + translate X → `WX_ATMOS_DUST_WIND`
* **Baromètre/compas** : cercle + graduations + aiguille séparée → `needle` présent

### Étape C — Composition finale

Assembler un `wx_icon_spec_t` selon les composants trouvés :

* decor = sun|moon|none
* cover = cloud|none
* particles = rain|drizzle|snow|sleet|hail|none
* atmos = haze|smoke|mist|dust|dust_wind|none
* lightning.flash enabled si éclair
* needle enabled si compas/baromètre

---

## 3) Extraction de paramètres (durées, amplitudes, phases)

### Rotation

* `dur` → `decor_fx.period_ms`
* pivot : depuis `animateTransform` (cx,cy) si présent ; sinon centre du viewBox
* angle: `0..3600`

### Fall (pluie/neige/grêle)

* `dur` → `part_fx.period_ms`
* translate start/end → amplitude (dx,dy)
* opacity values → `opa_min/max` et “plateau”
* `begin` négatif → `phase_ms` = `period - abs(begin)` modulo

### Jitter/Drift

* amplitude faible (<3px) et période 2–6s → `WX_FX_JITTER`
* amplitude faible et période >6s → `WX_FX_DRIFT`

### Crossfade (scale non uniforme)

* scale values → détecter 2 états significatifs
* générer recommandation : exporter 2 frames PNG
* `period_ms` = dur
* `opa_min/max` = 0/255

### Flash

* si opacité avec segments très courts (<200ms)
* `flash_ms` estimé depuis keyTimes/values
* si aucune temporisation claire : prendre 120ms

### Sleet

* pas toujours encodé en SMIL → si particules mixtes (bleu + blanc) → `WX_PART_SLEET`
* paramètres : pluie rapide + neige lente (counts réduits)

---

## 4) Découpe automatique en calques (raster plan)

Objectif : produire des PNG animables.

Règles :

1. **Un calque par entité animée** (cible SMIL = calque minimum).
2. **Décor split** : core (disque) séparé des FX (rayons) si rotation.
3. **Particules** : exporter **une particule générique** si répétition (lines identiques) sinon exporter le groupe complet.
4. **Atmos** : exporter 1 couche générique si répétable.
5. **Needle** : exporter dial et needle séparés.

Sortie “plan de calques” :

* `layer_id`, liste des éléments SVG (par id / index / selector), et asset cible.

---

## 5) Scoring / confiance

Calculer un score 0..1 et l’expliquer.

Exemples :

* +0.3 si nom de fichier matche un preset connu
* +0.2 si présence SMIL et mapping direct (rotate/fall)
* +0.2 si couleurs typiques (jaune soleil, bleu pluie)
* -0.3 si SVG complexe (filters, masks, clipPath, patterns)
* -0.2 si absence d’ids et structure plate

Si score <0.6 : produire un mapping “best effort” + recommandations de validation manuelle.

---

## 6) Dictionnaire de presets (prior par nom)

Avant analyse du contenu, appliquer des priors sur le nom :

* `clear-day` → decor sun + rotate rays
* `clear-night` → moon (+ twinkle si étoiles)
* `partly-cloudy-(day|night)` → decor + cloud
* suffixes:

  * `-rain` → particles rain
  * `-drizzle` → particles drizzle
  * `-snow` → particles snow
  * `-sleet` → particles sleet
  * `-hail` → particles hail
  * `-haze` → atmos haze
  * `-smoke` → atmos smoke
  * `-mist` → atmos mist
  * `dust-` → atmos dust / dust_wind
  * `hurricane` → rotate spiral
  * `barometer|compass` → needle

Ensuite, le contenu du SVG confirme ou invalide.

---

## 7) Format de sortie (JSON interne)

Exemple de rapport (à générer par un outil):

```json
{
  "file": "partly-cloudy-night-rain.svg",
  "confidence": 0.92,
  "components": {
    "decor": "MOON",
    "cover": "CLOUD",
    "particles": "RAIN",
    "atmos": "NONE",
    "lightning": false,
    "needle": false
  },
  "fx": {
    "decor_fx": {"type":"ROTATE","period_ms":45000,"pivot":[19,24]},
    "particles": {"kind":"RAIN","count":3,"period_ms":700,"fall_dy":15,"phases":[0,200,400]}
  },
  "layers": [
    {"asset":"MOON","selector":"#moon_group"},
    {"asset":"CLOUD","selector":"#cloud"},
    {"asset":"DROP","selector":"#drop_template"}
  ],
  "notes": ["SMIL not supported in LVGL; raster+lv_anim required"]
}
```

---

## 8) Implémentation conseillée (outil offline)

* Parser SVG via un parseur XML (offline), produire le JSON ci-dessus.
* Un second outil applique le plan de calques (export PNG via Inkscape/Resvg) et lance `lv_img_conv`.
* Le firmware ne fait que charger les assets (resolver) + instancier `wx_icon_spec_t`.

---

## 9) Limites assumées

* Les SVG avec `filter`, `mask`, `clipPath`, `pattern`, gradients complexes imbriqués : mapping OK, mais raster obligatoire + parfois calques plus grossiers.
* Les SVG sans ids : découpe auto moins fiable (fallback: découpe par groupes `<g>` + bbox).
* Le mapping sémantique par couleur peut échouer si thème custom.
