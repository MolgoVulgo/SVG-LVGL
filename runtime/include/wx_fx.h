#ifndef WX_FX_H
#define WX_FX_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    WX_FX_ROTATE = 0,
    WX_FX_FALL = 1,
    WX_FX_FLOW_X = 2,
    WX_FX_JITTER = 3,
    WX_FX_DRIFT = 4,
    WX_FX_TWINKLE = 5,
    WX_FX_FLASH = 6,
    WX_FX_CROSSFADE = 7,
    WX_FX_NEEDLE = 8,
    WX_FX_COUNT = 9,
} wx_fx_id_t;

typedef struct {
    uint16_t period_ms;
    int16_t amp_x;
    int16_t amp_y;
    int16_t fall_dy;
    uint16_t pivot_x;
    uint16_t pivot_y;
    uint8_t opa_min;
    uint8_t opa_max;
    uint8_t phase_count;
    uint16_t phase_ms[6];
} wx_fx_spec_t;

#define WX_FX_MASK(id) (1u << (id))

#ifdef __cplusplus
}
#endif

#endif
