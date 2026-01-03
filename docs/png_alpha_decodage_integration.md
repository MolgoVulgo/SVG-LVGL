bin# PNG + alpha — décodage & intégration (WX → LVGL)

## 1) Positionnement
- **Prod** : on **n’interprète pas** de PNG au runtime ; on convertit **offline** en **LVGL_BIN TRUE_COLOR_ALPHA** et on encapsule dans **WXPK v1**.
- **Démo/interop** : possible d’activer un décodeur PNG LVGL côté runtime (coût mémoire/CPU), mais non recommandé pour l’ESP en prod.

---

## 2) Offline (recommandé)
### 2.1 Décoder un PNG + alpha → buffer RGBA
- Source Python : `Pillow`/`PIL.Image.open()` → `convert('RGBA')`.
- Obtenir `w,h` et un buffer `bytes` ordonné RGBA (alpha **non prémultiplié**).

### 2.2 Conversion RGBA → format LVGL (TRUE_COLOR_ALPHA)
- Conserver **alpha non prémultiplié** (LVGL attend un canal alpha indépendant).
- Mappage octets typique (exemple little‑endian) : `A8 R8 G8 B8` → selon le `lv_color_format_t` ciblé.
- Option réduction : RGB565 + A8 séparé si pipeline spécifique, sinon **ARGB8888**.

### 2.3 Emballer en LVGL_BIN
- Écrire `lv_image_header_t` (v9) : `cf`, `w`, `h`, flags (sans compression pour débuter).
- Suivre de la trame pixels.
- Aligner/valider CRC si vous standardisez (ou laisser au conteneur WXPK v1 gérer l’intégrité).

### 2.4 Encapsuler dans WXPK v1
- Entrée TOC `ASSET_IMAGE` avec `asset_hash`, `size_px`, `IMG_TYPE` (votre code interne), `OFFSET/LENGTH`, `CRC`.

---

## 3) Runtime (optionnel, non recommandé en prod)
### 3.1 Activer un décodeur PNG LVGL
- Ajouter la lib `lv_png`/décodeur PNG au build LVGL.  
- En init : `lv_png_init();` (ou équivalent) pour enregistrer le décodeur.  
- Charger via `lv_img_set_src(img, "S:/path/to/image.png");` (FS LVGL requis).

**Coûts**
- RAM : buffers de décompression + frame complète.
- CPU : parsing PNG (défiltres, zlib).  
- Temps d’I/O : supérieur à LVGL_BIN binaire natif.

### 3.2 Contraintes d’alpha
- PNG fournit un **alpha droit** (non prémultiplié) → c’est compatible LVGL.  
- Éviter la prémultiplication en amont ; si présence d’APNG ou colorimetric chunks, ignorer/déflater pour le runtime.

---

## 4) Pièges & invariants
- **Gamma/ICC** : les chunks gAMA/cHRM/iCCP de PNG peuvent altérer la teinte si appliqués. Pour consistance UI, **neutraliser** ces métadonnées au moment de la conversion.
- **SRGB** : forcer une cible sRGB standard ; ne pas appliquer de correction au runtime.
- **Stride/alignment** : LVGL préfère des lignes contiguës sans padding exotique ; si nécessaire, ré‑emballer lors de la conversion.
- **Endianness** : rester en **little‑endian** côté binaire.
- **Compression** : ne pas recompresser LVGL_BIN ; laisser WXPK compresser **uniquement** le JSON.

---

## 5) Squelette Python (offline)
```python
from PIL import Image

def png_to_lvglbin_rgba(src_png: str) -> tuple[bytes, int, int]:
    im = Image.open(src_png).convert("RGBA")
    w, h = im.size
    rgba = im.tobytes()  # RGBA, non prémultiplié
    # Ici: réordonner au besoin vers votre cf cible (ex: ARGB8888 LE)
    # Exemple naïf: RGBA -> BGRA (swap R<->B)
    bgra = bytearray(len(rgba))
    bgra[0::4] = rgba[2::4]
    bgra[1::4] = rgba[1::4]
    bgra[2::4] = rgba[0::4]
    bgra[3::4] = rgba[3::4]
    return bytes(bgra), w, h

# Puis écrire un en-tête lv_image_header_t v9 + pixels pour former LVGL_BIN
```

---

## 6) Flux recommandé (WX)
1) **SVG → PNG par calque** (offline).  
2) **PNG → LVGL_BIN TRUE_COLOR_ALPHA** (offline).  
3) **Pack WXPK v1** (assets + JSON `wx.spec v1`).  
4) **Runtime**: loader WXPK → LVGL (aucune dépendance PNG).

---

## 7) Tests & validation
- Comparer rendu PNG viewer ↔ rendu LVGL (delta tolérance < 1 LSB par canal).  
- Vérifier l’alpha sur fonds de tests (checkerboard clair/sombre).  
- Bench RAM/CPU : BIN vs PNG au runtime (documenter l’écart → justifie le choix offline).

