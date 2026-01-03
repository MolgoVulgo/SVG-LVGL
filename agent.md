# agent.md

## Rôle de l’agent IA
Agent d’ingénierie déterministe.

## Vérité runtime
JSON wx.spec v1 uniquement.
Format prod : WXPK v1.

## Séparation des responsabilités
Offline Python : analyse SVG, génération assets, JSON, pack.
Runtime ESP : interprétation stricte JSON + pack.

## Règles contractuelles
- asset_key normalisé [a-z0-9_]+
- asset_hash = FNV1a32(asset_key)
- FX ciblent via target_z
- toutes les clés FX présentes

## Posture
Réponses en français, directes, sans extrapolation.

## Évolutions
Breaking change = bump de version + régénération.

