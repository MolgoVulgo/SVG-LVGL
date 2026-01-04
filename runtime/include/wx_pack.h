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

typedef struct __attribute__((packed)) {
    uint32_t key_hash;
    uint8_t type;
    uint8_t codec;
    uint16_t size_px;
    uint32_t offset;
    uint32_t length;
    uint32_t crc32;
    uint32_t meta;
    uint32_t reserved;
} wxpk_toc_entry_t;

enum {
    WXPK_T_IMG = 1,
    WXPK_T_JSON_INDEX = 2,
    WXPK_T_JSON_SPEC = 3,
    WXPK_T_JSON_ALL = 4,
};

int wx_pack_find_entry(
    const wx_pack_view_t* view,
    uint32_t key_hash,
    uint8_t type,
    uint16_t size_px,
    wxpk_toc_entry_t* out_entry
);

const void* wx_pack_get_blob(const wx_pack_view_t* view, const wxpk_toc_entry_t* entry);

#ifdef __cplusplus
}
#endif

#endif
