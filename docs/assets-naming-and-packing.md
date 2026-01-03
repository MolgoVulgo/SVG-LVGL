# assets-naming-and-packing.md

## Asset keys & hashing
asset_key :
- minuscule
- regex [a-z0-9_]+

asset_hash = FNV1a32(asset_key)

Renommage interdit sans bump de version pack.

Resolver runtime : (asset_hash, size_px, type).

