# wxpk_v_1_canevas_binaire.md

Canevas binaire WXPK v1 (detaille)

## 1) Vue d'ensemble
Un pack WXPK v1 contient un header fixe, un TOC, puis les payloads et le JSON wx.spec v1.
Encodage little-endian.

Structure globale:
- Header 32 bytes
- TOC (n entries, 28 bytes each)
- Payloads (assets binaires)
- JSON wx.spec v1 (UTF-8, null-terminated)

## 2) Header (32 bytes)

Offset | Taille | Champ | Type | Description
0x00 | 4 | magic | char[4] | "WXPK"
0x04 | 2 | version_major | uint16 | 1
0x06 | 2 | version_minor | uint16 | 0
0x08 | 4 | toc_count | uint32 | nombre d'entrees TOC
0x0C | 4 | toc_offset | uint32 | offset absolu du TOC (depuis 0x00)
0x10 | 4 | json_offset | uint32 | offset absolu JSON
0x14 | 4 | json_size | uint32 | taille JSON en bytes (incl. null terminator)
0x18 | 4 | pack_size | uint32 | taille totale du pack
0x1C | 4 | reserved | uint32 | 0

## 3) TOC entry (28 bytes)

Offset | Taille | Champ | Type | Description
0x00 | 4 | asset_hash | uint32 | FNV1a32(asset_key)
0x04 | 2 | size_px | uint16 | 64/96/128
0x06 | 2 | type | uint16 | 1=image,2=mask,3=alpha
0x08 | 4 | payload_offset | uint32 | offset absolu payload
0x0C | 4 | payload_size | uint32 | taille payload
0x10 | 4 | reserved0 | uint32 | 0
0x14 | 4 | reserved1 | uint32 | 0
0x18 | 4 | reserved2 | uint32 | 0

## 4) JSON wx.spec v1
- stocke a json_offset
- taille json_size
- terminaison '\0' obligatoire

## 5) Regles
- magic obligatoire
- endianess little-endian
- pack_size = taille fichier
- json_offset >= toc_offset + toc_count*28
- chaque payload_offset pointe dans la zone payloads
- assets resolus via (asset_hash,size_px,type)
