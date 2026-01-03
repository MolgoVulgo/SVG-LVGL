#ifndef WX_ICON_H
#define WX_ICON_H

#include <lvgl.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct wx_icon wx_icon_t;

wx_icon_t* wx_icon_from_pack(lv_obj_t* parent, const void* pack_data, size_t pack_size);
void wx_icon_destroy(wx_icon_t* icon);
void wx_icon_update(wx_icon_t* icon, const char* json_spec);

#ifdef __cplusplus
}
#endif

#endif
