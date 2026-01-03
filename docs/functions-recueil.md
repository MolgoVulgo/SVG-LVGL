# Recueil des fonctions à créer (outil offline : SVG → patterns → LVGL)

## 0) Portée

Outil **offline** (Node/Python au choix) qui :

1. lit un SVG
2. détecte composants + animations
3. mappe vers un ou plusieurs **patterns**
4. produit :

   * un **rapport JSON** (spec + calques + confiance)
   * (option) des commandes / manifest pour exporter PNG + lancer `lv_img_conv`

---

## 1) Fonctions de lecture / parsing SVG

### 1.1 Chargement / normalisation

* `loadSvgFile(path: string): string`

  * Lit le fichier et retourne le texte brut.

* `parseSvgXml(svgText: string): SvgDoc`

  * Parse XML en AST exploitable.

* `getViewBox(doc: SvgDoc): {x:number,y:number,w:number,h:number}`

  * Extrait `viewBox` (fallback sur width/height).

* `indexElements(doc: SvgDoc): SvgIndex`

  * Index par `id`, type (`path`, `circle`, `line`, `g`), et relations parent/enfant.

---

## 2) Fonctions d’extraction SMIL (animations)

### 2.1 Extraction brute

* `extractSmilAnimations(doc: SvgDoc): SmilAnim[]`

  * Récupère `animate`, `animateTransform`.

* `parseDuration(dur: string): number /*ms*/`

  * Convertit `"0.7s"`, `"150ms"` en millisecondes.

* `parseBegin(begin: string): number /*ms*/`

  * Gère `"-2.5s"`, `"0s"`, `"1.2s"`.

* `parseValues(values: string): string[]`

  * Split `"0;1;1;0"`, `"1 -5; -2 10"`.

* `normalizeSmil(anim: SmilAnim, viewBox: ViewBox): SmilAnimNorm`

  * Convertit en structure normalisée : type, période, pivot, from/to, phases.

### 2.2 Détection de patterns à partir SMIL

* `inferFxFromSmil(anims: SmilAnimNorm[]): FxInference[]`

  * Déduit `ROTATE`, `FALL`, `JITTER`, `DRIFT`, `CROSSFADE`, `TWINKLE`, `FLASH`.

* `computePhase(periodMs: number, beginMs: number): number`

  * Transforme begin négatif en `phase_ms`.

---

## 3) Fonctions de détection sémantique (formes/couleurs)

### 3.1 Features géométriques

* `collectGeometryFeatures(doc: SvgDoc, idx: SvgIndex): GeoFeatures`

  * Compte `circle/line/path`, densité de lignes, présence de groupes, bbox approximatives.

* `detectNeedleLikeShapes(doc: SvgDoc, idx: SvgIndex): boolean`

  * Heuristique baromètre/compas (dial + needle).

### 3.2 Features de style

* `collectStyleFeatures(doc: SvgDoc, idx: SvgIndex): StyleFeatures`

  * Palette dominante (stroke/fill), gradients présents, stroke widths.

* `detectLightning(style: StyleFeatures, geo: GeoFeatures): boolean`

  * Jaune/orange + path zigzag.

* `detectSun(style: StyleFeatures, geo: GeoFeatures): boolean`

  * Circle chaud + rayons (multiples paths autour).

* `detectMoon(style: StyleFeatures, geo: GeoFeatures): boolean`

  * Forme croissant / palette froide.

* `detectCloud(geo: GeoFeatures, style: StyleFeatures): boolean`

  * Grande masse grise (path volumique).

* `detectParticles(doc: SvgDoc, idx: SvgIndex, style: StyleFeatures): ParticleGuess`

  * Pluie/bruine/neige/grêle/sleet via lines/circles + couleurs.

* `detectAtmos(doc: SvgDoc, idx: SvgIndex, style: StyleFeatures): AtmosGuess`

  * haze/smoke/mist/dust/wind via couches/traits horizontaux/courbes.

---

## 4) Mapping final vers wx_icon_spec_t

### 4.1 Priors par nom

* `inferPriorsFromFilename(name: string): Priors`

  * `partly-cloudy-night-rain` → MOON + CLOUD + RAIN.

### 4.2 Assemblage composants → spec

* `composeIconComponents(priors: Priors, sem: SemanticGuess, fx: FxInference[]): IconComponents`

  * Décide decor/cover/particles/atmos + lightning/needle.

* `buildWxIconSpec(components: IconComponents, fx: FxInference[], viewBox: ViewBox): WxIconSpec`

  * Remplit `wx_icon_spec_t` (durées, amplitudes, phases, easing).

* `applyDefaultParams(spec: WxIconSpec): WxIconSpec`

  * Fallbacks cohérents (pluie=700ms, neige=1600ms, rotation=45s…).

* `validateSpec(spec: WxIconSpec): SpecWarnings`

  * Contrôle cohérence (ex: sleet = rain+snow, crossfade = 2 frames requises).

---

## 5) Plan de calques (raster plan)

### 5.1 Grouping

* `planLayers(doc: SvgDoc, idx: SvgIndex, components: IconComponents, fx: FxInference[]): LayerPlan`

  * Règles : 1 calque par cible animée, core vs fx, particule template, needle split.

* `assignElementsToLayers(idx: SvgIndex, layerPlan: LayerPlan): LayerAssignment`

  * Associe selectors/ids → calques.

### 5.2 Export hints

* `generateExportManifest(layerPlan: LayerPlan, sizes: number[]): ExportManifest`

  * Liste des PNG à produire (64/96/128) + noms.

* `emitInkscapeCommands(manifest: ExportManifest): string[]`

  * Génère les commandes d’export (si Inkscape).

* `emitLvImgConvJobs(manifest: ExportManifest, outDir: string): LvImgConvJob[]`

  * Jobs pour conversion LVGL.

---

## 6) Scoring / audit

* `scoreConfidence(priors: Priors, sem: SemanticGuess, fx: FxInference[], doc: SvgDoc): ConfidenceReport`

  * Score 0..1 + raisons + pénalités (filters/masks/complexité).

* `buildAuditTrail(...): string[]`

  * Liste lisible des décisions (pour debug et correction des heuristiques).

---

## 7) Sérialisation de sortie

* `toMappingJson(fileName: string, spec: WxIconSpec, layers: LayerPlan, confidence: ConfidenceReport): MappingJson`

  * Construit le JSON final.

* `writeJson(path: string, data: unknown): void`

  * Écrit le rapport.

---

## 8) API haut niveau (entrée unique)

* `mapSvgToPattern(svgPath: string, opts: MapOptions): MappingResult`

  * Orchestration complète.

* `mapSvgBatch(paths: string[], opts: MapOptions): BatchResult`

  * Traitement en masse.

---

## 9) Explicatif (logique du design)

* Séparation stricte **détection** (SMIL + sémantique) vs **décision** (composition) vs **production** (spec + calques + manifest).
* Le firmware LVGL ne doit pas parser du SVG : il consomme **des assets** + une `wx_icon_spec_t` stable.
* Toute limitation LVGL (scale non-uniforme, filters) est résolue **offline** (raster + crossfade/frames).
* Le scoring + audit sert à corriger les heuristiques sans “guess” silencieux.
