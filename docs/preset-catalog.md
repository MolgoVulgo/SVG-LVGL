# preset-catalog.md — Catalogue des presets (wx_icon_spec_t)

## 0) Objectif

Lister les presets officiels, avec :

* **composants** (decor/cover/particles/atmos)
* **layers** requis (assets)
* **FX** appliqués + paramètres par défaut
* notes de différenciation (pluie vs neige vs grêle, haze vs smoke vs mist)

Un preset = une fonction `wx_preset_<name>(size)` qui remplit un `wx_icon_spec_t`.

---

## 1) Conventions

### 1.1 Tailles

* `size ∈ {64,96,128}` (packs, pas de scale runtime)

### 1.2 Layers canoniques

* Decor: `sun_core`, `sun_rays`, `moon`
* Cover: `cloud`
* Particules: `drop`, `snowflake`, `hail`
* Atmos: `haze_layer_a`, `mist_layer_a`, `dust_streaks`, `dust_wind_group`
* Event: `lightning`
* Instrument: `dial`, `needle`
* UI: `ui_celsius`, `pressure_high/low(_alt)`, `humidity_drop`

### 1.3 Paramètres par défaut (rappel)

* rotate: 45000ms
* rain fall: 700ms, dy ~15px
* drizzle fall: 1200ms
* snow fall: 1600ms
* hail fall: 900ms (opa quasi constante)
* twinkle: 3000–6000ms
* flash: 120ms, gap 2–5s, double option
* drift: 8–12s, amp 1px
* flow_x: 3–5s, amp ~8px
* jitter: 3s, amp 2px

---

## 2) Presets météo — Ciel clair

### 2.1 `clear_day`

* components: decor=SUN, cover=NONE, particles=NONE, atmos=NONE
* layers:

  * `sun_core`
  * `sun_rays`
* fx:

  * ROTATE sur `sun_rays` (pivot centre, 45s)

### 2.2 `clear_night`

* components: decor=MOON, cover=NONE, particles=NONE, atmos=NONE
* layers:

  * `moon`
  * (option) `star` (si pack étoiles séparé)
* fx:

  * (option) TWINKLE sur étoiles (désync)

### 2.3 `starry_night`

* components: decor=MOON, cover=NONE, particles=NONE, atmos=NONE
* layers:

  * `moon`
  * `star` (N instances)
* fx:

  * TWINKLE sur `star[i]` (opa 80..255, periods variés)

---

## 3) Presets météo — Nuages

### 3.1 `cloudy`

* components: decor=NONE, cover=CLOUD, particles=NONE, atmos=NONE
* layers:

  * `cloud`
* fx:

  * (option) DRIFT sur `cloud` (amp 1px, 10s)

### 3.2 `partly_cloudy_day`

* components: decor=SUN, cover=CLOUD, particles=NONE, atmos=NONE
* layers:

  * `sun_core`, `sun_rays`, `cloud`
* fx:

  * ROTATE sur `sun_rays`
  * (option) DRIFT cloud très lent

### 3.3 `partly_cloudy_night`

* components: decor=MOON, cover=CLOUD, particles=NONE, atmos=NONE
* layers:

  * `moon`, `cloud`
* fx:

  * (option) DRIFT cloud très lent

---

## 4) Presets météo — Pluie / Bruine

### 4.1 `drizzle`

* components: decor=NONE, cover=CLOUD, particles=DRIZZLE, atmos=NONE
* layers:

  * `cloud`, `drop` (ou `drizzle_drop`)
* fx:

  * FALL params drizzle (période 1200ms, dy plus faible, opa douce)

### 4.2 `rain`

* components: decor=NONE, cover=CLOUD, particles=RAIN, atmos=NONE
* layers:

  * `cloud`, `drop`
* fx:

  * FALL params rain (700ms)

### 4.3 `partly_cloudy_day_rain`

* components: decor=SUN, cover=CLOUD, particles=RAIN, atmos=NONE
* layers:

  * `sun_core`, `sun_rays`, `cloud`, `drop`
* fx:

  * ROTATE rays + FALL rain

### 4.4 `partly_cloudy_night_rain`

* components: decor=MOON, cover=CLOUD, particles=RAIN, atmos=NONE
* layers:

  * `moon`, `cloud`, `drop`
* fx:

  * FALL rain

---

## 5) Presets météo — Neige / Grésil / Grêle

### 5.1 `snow`

* components: decor=NONE, cover=CLOUD, particles=SNOW, atmos=NONE
* layers:

  * `cloud`, `snowflake`
* fx:

  * FALL snow (1600ms, opa douce, dx faible option)

### 5.2 `partly_cloudy_night_snow`

* components: decor=MOON, cover=CLOUD, particles=SNOW, atmos=NONE
* layers:

  * `moon`, `cloud`, `snowflake`
* fx:

  * FALL snow

### 5.3 `sleet`

* components: decor=NONE, cover=CLOUD, particles=SLEET, atmos=NONE
* layers:

  * `cloud`, `drop`, `snowflake`
* fx:

  * FALL rain (moins d’instances) + FALL snow (moins d’instances, période plus longue)

### 5.4 `hail`

* components: decor=NONE, cover=CLOUD, particles=HAIL, atmos=NONE
* layers:

  * `cloud`, `hail`
* fx:

  * FALL hail (900ms, opa quasi constante)

### 5.5 `partly_cloudy_night_hail`

* components: decor=MOON, cover=CLOUD, particles=HAIL, atmos=NONE
* layers:

  * `moon`, `cloud`, `hail`
* fx:

  * FALL hail

---

## 6) Presets météo — Orages

### 6.1 `thunderstorms_day`

* components: decor=SUN, cover=CLOUD, particles=RAIN, atmos=NONE
* layers:

  * `sun_core`, `sun_rays`, `cloud`, `drop`, `lightning`
* fx:

  * ROTATE rays
  * FALL rain
  * FLASH lightning (120ms, gap 2–5s, double option)

### 6.2 `thunderstorms_night`

* components: decor=MOON, cover=CLOUD, particles=RAIN, atmos=NONE
* layers:

  * `moon`, `cloud`, `drop`, `lightning`
* fx:

  * FALL rain
  * FLASH lightning

### 6.3 `lightning_bolt`

* components: decor=NONE, cover=NONE, particles=NONE, atmos=NONE
* layers:

  * `lightning`
* fx:

  * (option) FLASH

---

## 7) Presets météo — Atmosphère (haze/smoke/mist)

### 7.1 `haze_day`

* components: decor=SUN, cover=CLOUD (option), particles=NONE, atmos=HAZE
* layers:

  * `sun_core` (+ `sun_rays` option), `cloud` option, `haze_layer_a` (1–2 couches)
* fx:

  * (option) ROTATE rays (si rays présent)
  * DRIFT haze (10s, amp 1px, opa 30–60%)

### 7.2 `haze_night`

* components: decor=MOON, cover=CLOUD (option), particles=NONE, atmos=HAZE
* layers:

  * `moon`, `cloud` option, `haze_layer_a`
* fx:

  * DRIFT haze

### 7.3 `smoke_night`

* components: decor=MOON, cover=CLOUD, particles=NONE, atmos=SMOKE
* layers:

  * `moon`, `cloud`, `smoke_layer_a` (1–2 couches)
* fx:

  * DRIFT smoke (amp identique, opa plus élevée)

### 7.4 `mist`

* components: decor=NONE, cover=NONE (ou CLOUD), particles=NONE, atmos=MIST
* layers:

  * `mist_layer_a` (1–2 couches)
* fx:

  * FLOW_X lent (ou DRIFT X) selon l’asset

---

## 8) Presets météo — Poussière / Vent

### 8.1 `dust_day`

* components: decor=SUN, cover=NONE, particles=NONE, atmos=DUST
* layers:

  * `sun_core`, `sun_rays`, `dust_streaks`
* fx:

  * ROTATE rays
  * JITTER dust (3s, amp ~2px) + déphasage si 2 instances

### 8.2 `dust_night`

* components: decor=MOON, cover=NONE, particles=NONE, atmos=DUST
* layers:

  * `moon`, `dust_streaks`
* fx:

  * JITTER dust

### 8.3 `dust_wind`

* components: decor=NONE, cover=NONE, particles=NONE, atmos=DUST_WIND
* layers:

  * `dust_wind_group` (2–3 instances)
* fx:

  * FLOW_X (wrap invisible, 3–4s, amp ~8px)

---

## 9) Presets météo — Cyclone

### 9.1 `hurricane`

* components: decor=NONE, cover=NONE, particles=NONE, atmos=NONE
* layers:

  * `hurricane_spiral`
* fx:

  * ROTATE (10–20s)
  * (option) DRIFT ou léger pulse d’opacité

---

## 10) Presets instruments / UI

### 10.1 `barometer`

* components: instrument
* layers:

  * `dial`, `needle`
* fx:

  * NEEDLE (piloté par donnée)

### 10.2 `compass`

* components: instrument
* layers:

  * `compass_dial`, `compass_needle` (ou `dial/needle` si mutualisé)
* fx:

  * NEEDLE (piloté par heading)

### 10.3 `pressure_high` / `pressure_high_alt`

* layers:

  * `pressure_high` (ou `_alt`)
* fx:

  * none

### 10.4 `pressure_low` / `pressure_low_alt`

* layers:

  * `pressure_low` (ou `_alt`)
* fx:

  * none

### 10.5 `celsius`

* layers:

  * `ui_celsius`
* fx:

  * none

### 10.6 `humidity`

* layers:

  * `humidity_drop`
* fx:

  * none (valeur `%` via `lv_label`)

---

## 11) Notes de différenciation (rappel)

* drizzle vs rain : même asset possible, mais période + amplitude + opa diffèrent.
* haze vs smoke vs mist :

  * haze = voile léger
  * smoke = voile plus dense
  * mist = couches horizontales + flow X
* sleet = mix rain + snow (moins d’instances, périodes distinctes)
* hail = chute rapide, opa quasi constante (impact)

---

## 12) Nommage des presets (canon)

Format :

* `snake_case`
* `partly_cloudy_<day|night>[_<phenomenon>]`

Exemples :

* `partly_cloudy_day_rain`
* `partly_cloudy_night_snow`
* `thunderstorms_day`
* `dust_wind`

---

## 13) TODO explicite (si tu veux couvrir tout le set)

* Ajouter les presets manquants dès que les SVG existent :

  * `partly_cloudy_day_sleet`, `partly_cloudy_day_hail`, etc.
* Ajouter les phases lunaires si besoin (assets + preset mapping).
