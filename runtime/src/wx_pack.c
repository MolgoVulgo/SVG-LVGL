#include "wx_pack.h"

#include <string.h>

#define WXPK_MAGIC 0x4B505857u
#define WXPK_HEADER_SIZE 32u
#define WXPK_ENDIAN_LITTLE 0u

typedef struct __attribute__((packed)) {
    uint32_t magic;
    uint16_t version;
    uint8_t endian;
    uint8_t header_size;
    uint32_t flags;
    uint32_t toc_offset;
    uint32_t toc_count;
    uint32_t blobs_offset;
    uint32_t file_crc32;
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
    if (out_header->magic != WXPK_MAGIC) {
        return -1;
    }
    if (out_header->version != 1) {
        return -1;
    }
    if (out_header->endian != WXPK_ENDIAN_LITTLE) {
        return -1;
    }
    if (out_header->header_size != WXPK_HEADER_SIZE) {
        return -1;
    }
    if (out_header->toc_offset < WXPK_HEADER_SIZE) {
        return -1;
    }
    if (out_header->toc_offset + out_header->toc_count * sizeof(wxpk_toc_entry_t) > view->size) {
        return -1;
    }
    if (out_header->blobs_offset > view->size) {
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

int wx_pack_find_entry(
    const wx_pack_view_t* view,
    uint32_t key_hash,
    uint8_t type,
    uint16_t size_px,
    wxpk_toc_entry_t* out_entry
) {
    wxpk_header_t header;
    if (!out_entry) {
        return -1;
    }
    if (wxpk_read_header(view, &header) != 0) {
        return -1;
    }

    for (uint32_t i = 0; i < header.toc_count; i++) {
        size_t offset = header.toc_offset + i * sizeof(wxpk_toc_entry_t);
        if (offset + sizeof(wxpk_toc_entry_t) > view->size) {
            return -1;
        }
        wxpk_toc_entry_t entry;
        memcpy(&entry, view->base + offset, sizeof(entry));
        if (entry.key_hash == key_hash && entry.type == type && entry.size_px == size_px) {
            *out_entry = entry;
            return 0;
        }
    }
    return -1;
}

const void* wx_pack_get_blob(const wx_pack_view_t* view, const wxpk_toc_entry_t* entry) {
    if (!view || !entry) {
        return NULL;
    }
    if (entry->offset + entry->length > view->size) {
        return NULL;
    }
    return view->base + entry->offset;
}
