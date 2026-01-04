#ifndef WX_JSON_H
#define WX_JSON_H

#include <stddef.h>

#include "wx_icon.h"

#ifdef __cplusplus
extern "C" {
#endif

int wx_json_parse_spec(const char* json, size_t length, wx_icon_spec_t* out_spec);

#ifdef __cplusplus
}
#endif

#endif
