#include "wx_icon.h"
#include "wx_pack.h"

struct wx_icon {
    lv_obj_t* root;
};

wx_icon_t* wx_icon_from_pack(lv_obj_t* parent, const void* pack_data, size_t pack_size) {
    (void)pack_data;
    (void)pack_size;

    wx_icon_t* icon = lv_mem_alloc(sizeof(*icon));
    if (!icon) {
        return NULL;
    }

    icon->root = lv_obj_create(parent);
    return icon;
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

void wx_icon_update(wx_icon_t* icon, const char* json_spec) {
    (void)icon;
    (void)json_spec;
    // TODO: parse and apply JSON spec.
}
