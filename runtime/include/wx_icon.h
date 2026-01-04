#ifndef WX_ICON_H
#define WX_ICON_H

#include <stddef.h>
#include <stdint.h>

#ifdef WX_NO_LVGL
typedef struct lv_obj_t lv_obj_t;
#else
#include <lvgl.h>
#endif

#include "wx_fx.h"
#include "wx_pack.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct wx_icon wx_icon_t;

typedef enum {
    WX_DECOR_NONE = 0,
    WX_DECOR_SUN = 1,
    WX_DECOR_MOON = 2,
} wx_decor_t;

typedef enum {
    WX_COVER_NONE = 0,
    WX_COVER_CLOUD = 1,
} wx_cover_t;

typedef enum {
    WX_PART_NONE = 0,
    WX_PART_RAIN = 1,
    WX_PART_DRIZZLE = 2,
    WX_PART_SNOW = 3,
    WX_PART_SLEET = 4,
    WX_PART_HAIL = 5,
} wx_particles_t;

typedef enum {
    WX_ATMOS_NONE = 0,
    WX_ATMOS_HAZE = 1,
    WX_ATMOS_SMOKE = 2,
    WX_ATMOS_MIST = 3,
    WX_ATMOS_DUST = 4,
    WX_ATMOS_DUST_WIND = 5,
} wx_atmos_t;

typedef enum {
    WX_EVENT_NONE = 0,
    WX_EVENT_LIGHTNING = 1,
} wx_event_t;

typedef struct {
    char asset_key[32];
    uint8_t fx_mask;
} wx_layer_spec_t;

#define WX_LAYER_MAX 8u

typedef struct {
    uint32_t spec_id;
    uint8_t decor;
    uint8_t cover;
    uint8_t particles;
    uint8_t atmos;
    uint8_t event;
    uint8_t layer_count;
    wx_layer_spec_t layers[WX_LAYER_MAX];
    wx_fx_spec_t fx[WX_FX_COUNT];
    uint32_t confidence_x1000;
} wx_icon_spec_t;

wx_icon_t* wx_icon_create_from_spec_id(
    lv_obj_t* parent,
    const wx_pack_view_t* pack,
    uint32_t spec_id,
    uint16_t size_px
);
wx_icon_t* wx_icon_create_from_spec(lv_obj_t* parent, const wx_icon_spec_t* spec);
void wx_icon_destroy(wx_icon_t* icon);
int wx_icon_apply_spec(wx_icon_t* icon, const wx_icon_spec_t* spec);

#ifdef __cplusplus
}
#endif

#endif
