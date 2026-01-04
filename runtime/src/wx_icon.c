#include "wx_icon.h"
#include "wx_json.h"

#include <string.h>

struct wx_icon {
    lv_obj_t* root;
};

static wx_icon_t* wx_icon_create_root(lv_obj_t* parent) {
    wx_icon_t* icon = lv_mem_alloc(sizeof(*icon));
    if (!icon) {
        return NULL;
    }
    memset(icon, 0, sizeof(*icon));
    icon->root = lv_obj_create(parent);
    return icon;
}

wx_icon_t* wx_icon_create_from_spec_id(
    lv_obj_t* parent,
    const wx_pack_view_t* pack,
    uint32_t spec_id,
    uint16_t size_px
) {
    (void)size_px;
    if (!pack) {
        return NULL;
    }

    wxpk_toc_entry_t entry;
    if (wx_pack_find_entry(pack, spec_id, WXPK_T_JSON_SPEC, 0, &entry) != 0) {
        return NULL;
    }
    const char* json = (const char*)wx_pack_get_blob(pack, &entry);
    if (!json) {
        return NULL;
    }

    wx_icon_spec_t spec;
    if (wx_json_parse_spec(json, entry.length, &spec) != 0) {
        return NULL;
    }

    wx_icon_t* icon = wx_icon_create_from_spec(parent, &spec);
    if (!icon) {
        return NULL;
    }
    if (wx_icon_apply_spec(icon, &spec) != 0) {
        wx_icon_destroy(icon);
        return NULL;
    }
    return icon;
}

wx_icon_t* wx_icon_create_from_spec(lv_obj_t* parent, const wx_icon_spec_t* spec) {
    (void)spec;
    return wx_icon_create_root(parent);
}

void wx_icon_destroy(wx_icon_t* icon) {
    if (!icon) {
        return;
    }
    if (icon->root) {
        lv_obj_del(icon->root);
    }
    lv_mem_free(icon);
}

int wx_icon_apply_spec(wx_icon_t* icon, const wx_icon_spec_t* spec) {
    (void)icon;
    (void)spec;
    // TODO: instantiate layers and FX per spec.
    return 0;
}
