#include "wx_pack.h"

#include <string.h>

#define WXPK_MAGIC "WXPK"
#define WXPK_HEADER_SIZE 32u

typedef struct __attribute__((packed)) {
    char magic[4];
    uint16_t version_major;
    uint16_t version_minor;
    uint32_t toc_count;
    uint32_t toc_offset;
    uint32_t json_offset;
    uint32_t json_size;
    uint32_t pack_size;
    uint32_t reserved;
} wxpk_header_t;

static int wxpk_read_header(const wx_pack_view_t* view, wxpk_header_t* out_header) {
    if (!view || !view->base || !out_header) {
        return -1;
    }
    if (view->size < WXPK_HEADER_SIZE) {
        return -1;
    }
    if (sizeof(*out_header) != WXPK_HEADER_SIZE) {
        return -1;
    }
    memcpy(out_header, view->base, sizeof(*out_header));
    if (memcmp(out_header->magic, WXPK_MAGIC, 4) != 0) {
        return -1;
    }
    if (out_header->version_major != 1) {
        return -1;
    }
    if (out_header->pack_size != view->size) {
        return -1;
    }
    if ((size_t)out_header->json_offset + out_header->json_size > view->size) {
        return -1;
    }
    return 0;
}

int wx_pack_open(wx_pack_view_t* view, const void* data, size_t size) {
    if (!view || !data || size == 0) {
        return -1;
    }
    view->base = (const uint8_t*)data;
    view->size = size;
    return 0;
}

const char* wx_pack_get_json(const wx_pack_view_t* view) {
    wxpk_header_t header;
    if (wxpk_read_header(view, &header) != 0) {
        return NULL;
    }
    if (header.json_size == 0) {
        return NULL;
    }
    const uint8_t* json = view->base + header.json_offset;
    if (json[header.json_size - 1] != '\0') {
        return NULL;
    }
    return (const char*)json;
}
