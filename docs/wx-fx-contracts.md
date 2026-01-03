# wx-fx-contracts.md — Contrats des effets (patterns) LVGL

## 0) Objectif

Définir, pour chaque FX, un **contrat strict** :

* ce que l’effet **peut modifier** (sur quels objets, quels champs)
* ce que l’effet **ne doit jamais modifier**
* les **paramètres** attendus et leurs unités
* les **invariants visuels** (anti-artefacts)

Le but : empêcher la dérive des implémentations quand on empile les icônes.

---

## 1) Règles globales (valables pour tous les FX)

1. Un FX s’applique à **une couche cible** (ou un groupe explicite). Jamais “au hasard”.
2. **Pas de resize runtime** : aucune fonction LVGL de zoom/resize sauf si le FX est explicitement `CROSSFADE` (swap frames).
3. Les FX ne modifient **pas** :

   * le contenu image (`lv_img_set_src`) sauf `CROSSFADE`
   * les styles (border/shadow) en runtime
4. Les mouvements sont en **pixels entiers** (évite le flou sur écrans non-AA). Si tu acceptes le subpixel, c’est un choix global, pas local.
5. Easing :

   * `ease_in_out` autorisé quand l’effet le demande
   * pas d’easing exotique sans raison (sinon incohérences inter-icônes)

---

## 2) FX: ROTATE

### 2.1 Intention

Rotation continue (rayons soleil, spirale cyclone, aiguille si anim).

### 2.2 Cible

* Cible unique : `lv_img` (ou objet dérivé) nommé `*_fx`.
* Interdit de rotation sur `*_core`.

### 2.3 Autorisé

* `lv_img_set_pivot(target, pivot_x, pivot_y)`
* `lv_img_set_angle(target, angle_0_3600)`

### 2.4 Interdit

* `lv_obj_set_pos()` (rotation ne doit pas déplacer la couche)
* opacité (sauf si explicitement combinée par un autre FX)
* changement de src

### 2.5 Paramètres

* `period_ms` (typique 30000–60000)
* `pivot_x/pivot_y` (pixels dans le PNG)
* `angle_from/angle_to` (0..3600)

### 2.6 Invariants / anti-artefacts

* Pivot exact : aucun wobble
* Wrap propre : 3599→0 non visible (utiliser angle modulo)

---

## 3) FX: FALL

### 3.1 Intention

Chute cyclique (pluie/neige/grêle). Combine translation + opacité.

### 3.2 Cible

* N objets particules `lv_img` (1 asset instancié N fois)

### 3.3 Autorisé

* `lv_obj_set_pos()` sur la particule
* `lv_obj_set_style_opa()` (ou `lv_obj_set_style_img_opa`) sur la particule

### 3.4 Interdit

* rotation
* scale/zoom
* changement de src

### 3.5 Paramètres

* `period_ms`
* `fall_dy` (px), `fall_dx` optionnel (neige)
* `opa_min/opa_max`
* `phase_ms[i]` pour désynchronisation

### 3.6 Invariants

* Pluie : rapide, opacité plus franche, pas d’oscillation X
* Neige : plus lente, opacité plus douce, oscillation X faible optionnelle
* Grêle : rapide + opacité quasi constante (impact sec)

---

## 4) FX: FLOW_X

### 4.1 Intention

Flux horizontal (vent, dust-wind). Wrap invisible.

### 4.2 Cible

* 2–3 couches `lv_img` identiques, déphasées

### 4.3 Autorisé

* `lv_obj_set_x()` (ou `lv_obj_set_pos`) sur la couche

### 4.4 Interdit

* opacité pulsée (ça devient brouillard)
* rotation
* changement de src

### 4.5 Paramètres

* `period_ms` (2500–5000)
* `amp_x` (largeur de boucle, typiquement 4–12px)
* `phase_ms`

### 4.6 Invariants

* Wrap hors champ : repositionnement doit être invisible
* Mouvement constant (pas d’à-coups)

---

## 5) FX: JITTER

### 5.1 Intention

Micro-translate cyclique (poussière, tremblement subtil).

### 5.2 Cible

* 1–2 couches `lv_img`

### 5.3 Autorisé

* `lv_obj_set_pos()` avec amplitude faible

### 5.4 Interdit

* opacité
* rotation

### 5.5 Paramètres

* `period_ms` (2000–6000)
* `amp_x/amp_y` (≤ 2px recommandé)

### 5.6 Invariants

* Reste subtil : si perceptible comme déplacement d’objet, c’est trop.

---

## 6) FX: DRIFT

### 6.1 Intention

Dérive lente (nuage, haze layer) sans attirer l’œil.

### 6.2 Cible

* 1 couche `lv_img` (ou 2 couches haze)

### 6.3 Autorisé

* `lv_obj_set_pos()` amplitude faible
* opacité constante ou très légère variation (option)

### 6.4 Interdit

* flash
* déplacement rapide

### 6.5 Paramètres

* `period_ms` (> 6000)
* `amp_x/amp_y` (1–2px)

### 6.6 Invariants

* Mouvement quasi imperceptible

---

## 7) FX: TWINKLE

### 7.1 Intention

Scintillement étoiles (opacity pulsée, désynchronisée).

### 7.2 Cible

* N petites étoiles `lv_img`

### 7.3 Autorisé

* opacité (range limité)

### 7.4 Interdit

* translation (sinon effet neige)
* rotation

### 7.5 Paramètres

* `period_ms` typiquement 2000–6000 (par étoile)
* `opa_min/opa_max` (ex: 80..255)
* `phase_ms` (toutes différentes)

### 7.6 Invariants

* Désynchronisation obligatoire
* Pas de noirs complets (opa_min > 0)

---

## 8) FX: FLASH

### 8.1 Intention

Éclair / flash d’événement (opacité brutale).

### 8.2 Cible

* 1 couche `lv_img` lightning

### 8.3 Autorisé

* opacité 0/255 uniquement

### 8.4 Interdit

* interpolation d’opacité lente (ça devient glow)
* translation

### 8.5 Paramètres

* `flash_ms` 80–150
* `gap_ms_min/max` 2000–5000
* `double_flash` option

### 8.6 Invariants

* Bord net : aucun anti-flou par mouvement
* Random contrôlé (borné)

---

## 9) FX: CROSSFADE

### 9.1 Intention

Simuler un transform non supporté (scale non-uniforme) via swap de frames.

### 9.2 Cible

* 2 couches `lv_img` (f0 + f1) superposées

### 9.3 Autorisé

* opacité inversée sur f0/f1
* (option) swap `lv_img_set_src` si on recycle un seul objet

### 9.4 Interdit

* toute transformation géométrique (le but est précisément de l’éviter)

### 9.5 Paramètres

* `period_ms` (ex: 5000)
* `opa_min/max` (0/255)
* easing `ease_in_out` recommandé

### 9.6 Invariants

* Les deux frames doivent être strictement alignées (plein cadre)

---

## 10) FX: NEEDLE (instrument)

### 10.1 Intention

Aiguille pilotée par une valeur (compas/baromètre). Mise à jour lissée.

### 10.2 Cible

* `img_dial` statique
* `img_needle` rotatif

### 10.3 Autorisé

* `lv_img_set_pivot(img_needle, pivot_x, pivot_y)`
* `lv_img_set_angle(img_needle, angle)`
* animation lissée vers angle cible

### 10.4 Interdit

* modification du dial
* translation du needle (hors correction initiale)

### 10.5 Paramètres

* `angle_now` (0..3600)
* `smooth_ms` (200–600)

### 10.6 Invariants

* Pas d’overshoot
* pas de jitter (arrondir angle si besoin)

---

## 11) Compatibilité / composition de FX

### 11.1 Règle

Deux FX ne doivent pas écrire le même champ d’un même objet.

### 11.2 Compositions autorisées (exemples)

* `SUN`: `ROTATE` sur `sun_rays` + statique sur `sun_core`
* `THUNDER`: `FALL` (pluie) + `FLASH` (éclair)
* `DUST_DAY`: `ROTATE` (rayons) + `JITTER` (poussière)
* `HURRICANE`: `ROTATE` (spirale) + (option) `DRIFT` global

### 11.3 Compositions interdites

* `FLASH` + `TWINKLE` sur le même objet
* `FALL` + `FLOW_X` sur une même particule

---

## 12) Paramètres “par défaut” (fallbacks)

* `ROTATE`: 45000ms
* `FALL`:

  * rain: 700ms, dy ~15px, opa 0→255→0
  * drizzle: 1200ms, dy plus faible
  * snow: 1600ms, dy modéré, dx faible option
  * hail: 900ms, opa quasi constante
* `TWINKLE`: 3000–6000ms, opa 80..255
* `FLASH`: 120ms, gap 2000–5000ms
* `DRIFT`: 8000–12000ms, amp 1px
* `JITTER`: 3000ms, amp 2px
* `FLOW_X`: 3000ms, amp 8px

---

## 13) Observabilité (debug)

Chaque FX doit pouvoir logguer (option build flag) :

* cible(s)
* period/phase
* amplitudes
* dernier angle/pos/opa

Le debug doit être silencieux par défaut.
