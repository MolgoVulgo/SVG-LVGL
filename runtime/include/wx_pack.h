#ifndef WX_PACK_H
#define WX_PACK_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    const uint8_t* base;
    size_t size;
} wx_pack_view_t;

int wx_pack_open(wx_pack_view_t* view, const void* data, size_t size);
const char* wx_pack_get_json(const wx_pack_view_t* view);

#ifdef __cplusplus
}
#endif

#endif
