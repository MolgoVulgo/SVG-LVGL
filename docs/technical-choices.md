# technical-choices.md — Choix techniques, langages et GUI

## 0) Rôle du document

Ce document justifie et fige :

* les **choix technologiques**
* les **langages utilisés** par couche
* la **mise en place d’une GUI** pour l’outil offline
* la **possibilité d’un aperçu visuel** avant intégration LVGL

Il sert de référence décisionnelle. Les choix décrits ici ne sont pas rediscutés sans instruction explicite.

---

## 1) Architecture globale retenue

### 1.1 Séparation stricte des responsabilités

Le projet est découpé en trois couches indépendantes :

1. **Analyse & mapping SVG (offline)**
2. **Production des assets (offline)**
3. **Runtime embarqué (LVGL / C)**

Aucune logique de la couche 1 ou 2 ne doit exister dans la couche 3.

---

## 2) Choix du langage

### 2.1 Outils offline : **Python**

#### Justification

Python est retenu comme langage principal pour les outils offline car :

* parsing XML/SVG mature (`lxml`, `xml.etree`)
* manipulation géométrique et couleur simple
* scripting robuste pour pipelines (export, conversion, CI)
* facilité d’intégration avec Inkscape / resvg / CLI externes

Le besoin n’est **pas la performance**, mais :

* la lisibilité
* la traçabilité des décisions
* la maintenabilité

#### Alternatives écartées

* **Node.js** : parsing SVG possible mais plus verbeux, moins adapté à l’analyse structurelle lourde
* **Rust** : trop coûteux en mise en place pour un outil d’analyse heuristique

---

### 2.2 Runtime embarqué : **C (LVGL 8.3)**

#### Justification

* LVGL impose le C
* contrôle fin de la mémoire
* compatibilité microcontrôleurs / SoC
* absence de runtime lourd

Aucune autre abstraction (C++, bindings) n’est autorisée.

---

## 3) Choix GUI (outil offline)

### 3.1 Objectif de la GUI

La GUI n’est **pas un éditeur graphique**.
Elle sert uniquement à :

* visualiser un SVG d’entrée
* visualiser le **résultat du mapping** (patterns détectés)
* prévisualiser le rendu rasterisé animé
* diagnostiquer les erreurs de mapping

---

### 3.2 Technologie GUI retenue : **PySide6 (Qt)**

#### Justification

* bindings Qt stables
* rendu vectoriel + raster performant
* widgets matures (tree view, panels, overlay)
* portabilité Linux / Windows

#### Alternatives écartées

* Web (Electron/WebView) : inutilement lourd

---

## 4) Aperçu visuel (preview)

### 4.1 Principe

L’aperçu doit :

* reproduire **le comportement LVGL**, pas celui du SVG
* utiliser les **PNG rasterisés**, jamais le SVG animé
* appliquer les **patterns** (rotate, fall, drift, etc.)

L’aperçu est une **simulation LVGL**, pas un rendu SVG.

---

### 4.2 Implémentation preview

#### Option retenue : moteur léger Python

* Chargement des PNG exportés
* Application des FX via timers Qt :

  * rotation
  * translation
  * opacité
* Respect strict de `wx-fx-contracts.md`

Le code de preview est volontairement simple et redondant avec le runtime C.
Il sert à **valider la logique**, pas à factoriser.

---

### 4.3 Ce que l’aperçu ne fait pas

* pas de rendu SVG direct
* pas de scale non uniforme
* pas d’effets non supportés LVGL

---

## 5) Workflow utilisateur (outil)

1. Charger un SVG
2. Lancer l’analyse
3. Afficher :

   * patterns détectés
   * score de confiance
   * plan de calques
4. Générer les PNG
5. Prévisualiser l’animation
6. Exporter :

   * JSON de mapping
   * manifest assets

Aucune étape implicite.

---

## 6) Organisation du dépôt (proposée)

```
/tools
  /svg_mapper
    parser.py
    smil.py
    semantic.py
    mapper.py
    layers.py
    export.py
    gui_qt.py
/docs
  agent.md
  wx-fx-contracts.md
  assets-naming-and-packing.md
  preset-catalog.md
  mapping-svg-pattern.md
  technical-choices.md
/firmware
  /wx_icons
    wx_icon.c
    wx_icon.h
```

---

## 7) CI / automatisation

### 7.1 Vérifications offline

* parsing SVG valide
* mapping JSON générable
* score >= seuil défini
* conformité assets (naming, tailles)

### 7.2 Vérifications runtime

* compilation firmware sans warnings
* assets présents pour chaque preset

---

## 8) Décisions figées

Les points suivants sont considérés **définitifs** :

* Python pour les outils offline
* C + LVGL 8.3 pour le runtime
* Rasterisation obligatoire
* Preview basée sur PNG + patterns
* GUI Qt (PySide6)

Toute modification nécessite une instruction explicite.
