#ifndef WX_TYPES_H
#define WX_TYPES_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct wx_icon wx_icon_t;

typedef struct {
    uint32_t asset_hash;
    uint16_t size_px;
    uint16_t type;
} wx_asset_key_t;

#ifdef __cplusplus
}
#endif

#endif
