# WX Weather Icons — README

## 1) Objet du projet
WX Weather Icons est une chaîne complète permettant de transformer des icônes SVG météo en assets animés LVGL pour ESP, via une pipeline offline Python et un runtime interprétatif.

Principe clé :
Toute l’intelligence est offline (Python). Le runtime n’interprète que des données.

## 2) Architecture globale
SVG → Python (analyse, découpe, raster) → JSON wx.spec v1 + pack WXPK v1 → ESP/LVGL (lib)

## 3) Principes structurants
- JSON wx.spec v1 = vérité runtime
- WXPK v1 = format de production
- lookup assets par (asset_hash, size_px, type)
- asset_hash = FNV1a32(asset_key)
- enums WX_ASSET_* uniquement pour le canon
- runtime ESP n’analyse jamais de SVG

Docs normatifs :
wx-pack-spec.md, wx-fx-contracts.md, assets-naming-and-packing.md, agent.md

## 4) Contenu du dépôt
Voir arborescence décrite dans plan de developpement.md

## 5) Pipeline offline
Analyse SVG, mapping patterns, découpe calques, raster PNG, génération wx.spec v1, génération pack WXPK v1.

## 6) Runtime ESP/LVGL
Lib prête à l’emploi :
- loader WXPK
- resolver assets
- parse JSON
- instanciation LVGL
- FX contractuels

## 7) Exemples
from_pack, instruments, multi-size

## 8) État du projet
Architecture complète, implémentation en cours.

## 9) Critère de réussite
SVG ajouté → pack généré → affichage LVGL sans modifier le code.

