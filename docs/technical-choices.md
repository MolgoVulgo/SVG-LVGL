# technical-choices.md

Choix techniques :
- JSON wx.spec v1 = vérité runtime
- BIN WXPK v1 = format prod
- lookup assets via asset_hash + TOC
- enums WX_ASSET_* réservés au canon
- codec image prod : LVGL_BIN

Le core ESP interprète uniquement JSON + pack.
Jamais de parsing SVG.

