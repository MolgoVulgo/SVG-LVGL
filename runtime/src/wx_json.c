#include "wx_json.h"

#include <stdlib.h>
#include <string.h>

#include "jsmn.h"

#define WX_JSON_MAX_TOKENS 256

static int json_token_skip(const jsmntok_t* tokens, int token_count, int index) {
    int i = index;
    if (tokens[i].type == JSMN_STRING || tokens[i].type == JSMN_PRIMITIVE) {
        return i + 1;
    }
    int end = tokens[i].end;
    i++;
    while (i < token_count && tokens[i].start < end) {
        i++;
    }
    return i;
}

static int json_key_eq(const char* json, const jsmntok_t* tok, const char* key) {
    size_t key_len = strlen(key);
    size_t tok_len = (size_t)(tok->end - tok->start);
    if (tok->type != JSMN_STRING || key_len != tok_len) {
        return 0;
    }
    return strncmp(json + tok->start, key, tok_len) == 0;
}

static int json_find_key(
    const char* json,
    const jsmntok_t* tokens,
    int token_count,
    int obj_index,
    const char* key
) {
    int i = obj_index + 1;
    int end = tokens[obj_index].end;
    while (i < token_count && tokens[i].start < end) {
        const jsmntok_t* key_tok = &tokens[i];
        int value_index = i + 1;
        if (json_key_eq(json, key_tok, key)) {
            return value_index;
        }
        i = json_token_skip(tokens, token_count, value_index);
    }
    return -1;
}

static int json_copy_string(const char* json, const jsmntok_t* tok, char* out, size_t out_len) {
    size_t len = (size_t)(tok->end - tok->start);
    if (tok->type != JSMN_STRING) {
        return -1;
    }
    if (len >= out_len) {
        return -1;
    }
    memcpy(out, json + tok->start, len);
    out[len] = '\0';
    return 0;
}

static int json_parse_int(const char* json, const jsmntok_t* tok, int* out) {
    if (tok->type != JSMN_PRIMITIVE) {
        return -1;
    }
    size_t len = (size_t)(tok->end - tok->start);
    char buf[32];
    if (len >= sizeof(buf)) {
        return -1;
    }
    memcpy(buf, json + tok->start, len);
    buf[len] = '\0';
    char* endptr = NULL;
    long value = strtol(buf, &endptr, 10);
    if (!endptr || *endptr != '\0') {
        return -1;
    }
    *out = (int)value;
    return 0;
}

static int json_parse_float(const char* json, const jsmntok_t* tok, double* out) {
    if (tok->type != JSMN_PRIMITIVE) {
        return -1;
    }
    size_t len = (size_t)(tok->end - tok->start);
    char buf[32];
    if (len >= sizeof(buf)) {
        return -1;
    }
    memcpy(buf, json + tok->start, len);
    buf[len] = '\0';
    char* endptr = NULL;
    double value = strtod(buf, &endptr);
    if (!endptr || *endptr != '\0') {
        return -1;
    }
    *out = value;
    return 0;
}

static int json_map_enum(const char* value, const char* const* names, const uint8_t* codes, size_t count) {
    for (size_t i = 0; i < count; i++) {
        if (strcmp(value, names[i]) == 0) {
            return codes[i];
        }
    }
    return -1;
}

static int json_fx_id(const char* value) {
    struct { const char* name; uint8_t id; } map[] = {
        {"ROTATE", WX_FX_ROTATE},
        {"FALL", WX_FX_FALL},
        {"FLOW_X", WX_FX_FLOW_X},
        {"JITTER", WX_FX_JITTER},
        {"DRIFT", WX_FX_DRIFT},
        {"TWINKLE", WX_FX_TWINKLE},
        {"FLASH", WX_FX_FLASH},
        {"CROSSFADE", WX_FX_CROSSFADE},
        {"NEEDLE", WX_FX_NEEDLE},
    };
    for (size_t i = 0; i < sizeof(map) / sizeof(map[0]); i++) {
        if (strcmp(value, map[i].name) == 0) {
            return map[i].id;
        }
    }
    return -1;
}

static int json_parse_components(
    const char* json,
    const jsmntok_t* tokens,
    int token_count,
    int obj_index,
    wx_icon_spec_t* out_spec
) {
    char buf[32];
    const char* decor_names[] = {"NONE", "SUN", "MOON"};
    const uint8_t decor_codes[] = {WX_DECOR_NONE, WX_DECOR_SUN, WX_DECOR_MOON};
    const char* cover_names[] = {"NONE", "CLOUD"};
    const uint8_t cover_codes[] = {WX_COVER_NONE, WX_COVER_CLOUD};
    const char* part_names[] = {"NONE", "RAIN", "DRIZZLE", "SNOW", "SLEET", "HAIL"};
    const uint8_t part_codes[] = {
        WX_PART_NONE, WX_PART_RAIN, WX_PART_DRIZZLE, WX_PART_SNOW, WX_PART_SLEET, WX_PART_HAIL
    };
    const char* atmos_names[] = {"NONE", "HAZE", "SMOKE", "MIST", "DUST", "DUST_WIND"};
    const uint8_t atmos_codes[] = {
        WX_ATMOS_NONE, WX_ATMOS_HAZE, WX_ATMOS_SMOKE, WX_ATMOS_MIST, WX_ATMOS_DUST, WX_ATMOS_DUST_WIND
    };
    const char* event_names[] = {"NONE", "LIGHTNING"};
    const uint8_t event_codes[] = {WX_EVENT_NONE, WX_EVENT_LIGHTNING};

    int value_index = json_find_key(json, tokens, token_count, obj_index, "decor");
    if (value_index < 0 || json_copy_string(json, &tokens[value_index], buf, sizeof(buf)) != 0) {
        return -1;
    }
    int mapped = json_map_enum(
        buf,
        decor_names,
        decor_codes,
        sizeof(decor_codes) / sizeof(decor_codes[0])
    );
    if (mapped < 0) {
        return -1;
    }
    out_spec->decor = (uint8_t)mapped;

    value_index = json_find_key(json, tokens, token_count, obj_index, "cover");
    if (value_index < 0 || json_copy_string(json, &tokens[value_index], buf, sizeof(buf)) != 0) {
        return -1;
    }
    mapped = json_map_enum(
        buf,
        cover_names,
        cover_codes,
        sizeof(cover_codes) / sizeof(cover_codes[0])
    );
    if (mapped < 0) {
        return -1;
    }
    out_spec->cover = (uint8_t)mapped;

    value_index = json_find_key(json, tokens, token_count, obj_index, "particles");
    if (value_index < 0 || json_copy_string(json, &tokens[value_index], buf, sizeof(buf)) != 0) {
        return -1;
    }
    mapped = json_map_enum(
        buf,
        part_names,
        part_codes,
        sizeof(part_codes) / sizeof(part_codes[0])
    );
    if (mapped < 0) {
        return -1;
    }
    out_spec->particles = (uint8_t)mapped;

    value_index = json_find_key(json, tokens, token_count, obj_index, "atmos");
    if (value_index < 0 || json_copy_string(json, &tokens[value_index], buf, sizeof(buf)) != 0) {
        return -1;
    }
    mapped = json_map_enum(
        buf,
        atmos_names,
        atmos_codes,
        sizeof(atmos_codes) / sizeof(atmos_codes[0])
    );
    if (mapped < 0) {
        return -1;
    }
    out_spec->atmos = (uint8_t)mapped;

    value_index = json_find_key(json, tokens, token_count, obj_index, "event");
    if (value_index < 0 || json_copy_string(json, &tokens[value_index], buf, sizeof(buf)) != 0) {
        return -1;
    }
    mapped = json_map_enum(
        buf,
        event_names,
        event_codes,
        sizeof(event_codes) / sizeof(event_codes[0])
    );
    if (mapped < 0) {
        return -1;
    }
    out_spec->event = (uint8_t)mapped;

    return 0;
}

static int json_parse_fx_entry(
    const char* json,
    const jsmntok_t* tokens,
    int token_count,
    int obj_index,
    wx_fx_spec_t* out_fx
) {
    int value_index;
    int int_value = 0;

    memset(out_fx, 0, sizeof(*out_fx));

    value_index = json_find_key(json, tokens, token_count, obj_index, "period_ms");
    if (value_index >= 0 && json_parse_int(json, &tokens[value_index], &int_value) == 0) {
        out_fx->period_ms = (uint16_t)int_value;
    }

    value_index = json_find_key(json, tokens, token_count, obj_index, "pivot_x");
    if (value_index >= 0 && json_parse_int(json, &tokens[value_index], &int_value) == 0) {
        out_fx->pivot_x = (uint16_t)int_value;
    }

    value_index = json_find_key(json, tokens, token_count, obj_index, "pivot_y");
    if (value_index >= 0 && json_parse_int(json, &tokens[value_index], &int_value) == 0) {
        out_fx->pivot_y = (uint16_t)int_value;
    }

    value_index = json_find_key(json, tokens, token_count, obj_index, "fall_dy");
    if (value_index >= 0 && json_parse_int(json, &tokens[value_index], &int_value) == 0) {
        out_fx->fall_dy = (int16_t)int_value;
    }

    value_index = json_find_key(json, tokens, token_count, obj_index, "fall_dx");
    if (value_index >= 0 && json_parse_int(json, &tokens[value_index], &int_value) == 0) {
        out_fx->amp_x = (int16_t)int_value;
    }

    value_index = json_find_key(json, tokens, token_count, obj_index, "amp_x");
    if (value_index >= 0 && json_parse_int(json, &tokens[value_index], &int_value) == 0) {
        out_fx->amp_x = (int16_t)int_value;
    }

    value_index = json_find_key(json, tokens, token_count, obj_index, "amp_y");
    if (value_index >= 0 && json_parse_int(json, &tokens[value_index], &int_value) == 0) {
        out_fx->amp_y = (int16_t)int_value;
    }

    value_index = json_find_key(json, tokens, token_count, obj_index, "opa_min");
    if (value_index >= 0 && json_parse_int(json, &tokens[value_index], &int_value) == 0) {
        out_fx->opa_min = (uint8_t)int_value;
    }

    value_index = json_find_key(json, tokens, token_count, obj_index, "opa_max");
    if (value_index >= 0 && json_parse_int(json, &tokens[value_index], &int_value) == 0) {
        out_fx->opa_max = (uint8_t)int_value;
    }

    value_index = json_find_key(json, tokens, token_count, obj_index, "phase_ms");
    if (value_index >= 0 && tokens[value_index].type == JSMN_ARRAY) {
        int count = tokens[value_index].size;
        int i = value_index + 1;
        if (count > 6) {
            count = 6;
        }
        out_fx->phase_count = (uint8_t)count;
        for (int idx = 0; idx < count; idx++) {
            if (json_parse_int(json, &tokens[i], &int_value) != 0) {
                return -1;
            }
            out_fx->phase_ms[idx] = (uint16_t)int_value;
            i = json_token_skip(tokens, token_count, i);
        }
    }

    return 0;
}

static int json_parse_fx(
    const char* json,
    const jsmntok_t* tokens,
    int token_count,
    int obj_index,
    wx_icon_spec_t* out_spec
) {
    int i = obj_index + 1;
    int end = tokens[obj_index].end;
    while (i < token_count && tokens[i].start < end) {
        const jsmntok_t* key_tok = &tokens[i];
        char key_buf[16];
        int value_index = i + 1;
        if (json_copy_string(json, key_tok, key_buf, sizeof(key_buf)) != 0) {
            return -1;
        }
        int fx_id = json_fx_id(key_buf);
        if (fx_id < 0 || fx_id >= WX_FX_COUNT) {
            return -1;
        }
        if (json_parse_fx_entry(json, tokens, token_count, value_index, &out_spec->fx[fx_id]) != 0) {
            return -1;
        }
        i = json_token_skip(tokens, token_count, value_index);
    }
    return 0;
}

static int json_parse_layers(
    const char* json,
    const jsmntok_t* tokens,
    int token_count,
    int array_index,
    wx_icon_spec_t* out_spec
) {
    if (tokens[array_index].type != JSMN_ARRAY) {
        return -1;
    }
    int end = tokens[array_index].end;
    int i = array_index + 1;
    int out_count = 0;

    while (i < token_count && tokens[i].start < end) {
        if (tokens[i].type != JSMN_OBJECT) {
            return -1;
        }
        if (out_count >= WX_LAYER_MAX) {
            return -1;
        }
        int asset_index = json_find_key(json, tokens, token_count, i, "asset");
        if (asset_index < 0) {
            return -1;
        }
        if (json_copy_string(json, &tokens[asset_index], out_spec->layers[out_count].asset_key,
                             sizeof(out_spec->layers[out_count].asset_key)) != 0) {
            return -1;
        }

        out_spec->layers[out_count].fx_mask = 0;
        int fx_index = json_find_key(json, tokens, token_count, i, "fx");
        if (fx_index >= 0) {
            if (tokens[fx_index].type != JSMN_ARRAY) {
                return -1;
            }
            int fx_end = tokens[fx_index].end;
            int fx_tok = fx_index + 1;
            while (fx_tok < token_count && tokens[fx_tok].start < fx_end) {
                char fx_buf[16];
                if (json_copy_string(json, &tokens[fx_tok], fx_buf, sizeof(fx_buf)) != 0) {
                    return -1;
                }
                int fx_id = json_fx_id(fx_buf);
                if (fx_id < 0) {
                    return -1;
                }
                out_spec->layers[out_count].fx_mask |= (uint8_t)WX_FX_MASK(fx_id);
                fx_tok = json_token_skip(tokens, token_count, fx_tok);
            }
        }
        out_count++;
        i = json_token_skip(tokens, token_count, i);
    }

    out_spec->layer_count = (uint8_t)out_count;
    return 0;
}

int wx_json_parse_spec(const char* json, size_t length, wx_icon_spec_t* out_spec) {
    if (!json || length == 0 || !out_spec) {
        return -1;
    }
    jsmn_parser parser;
    jsmntok_t tokens[WX_JSON_MAX_TOKENS];

    jsmn_init(&parser);
    int count = jsmn_parse(&parser, json, length, tokens, WX_JSON_MAX_TOKENS);
    if (count < 1 || tokens[0].type != JSMN_OBJECT) {
        return -1;
    }

    memset(out_spec, 0, sizeof(*out_spec));

    int spec_id_index = json_find_key(json, tokens, count, 0, "spec_id");
    int int_value = 0;
    if (spec_id_index < 0 || json_parse_int(json, &tokens[spec_id_index], &int_value) != 0) {
        return -1;
    }
    out_spec->spec_id = (uint32_t)int_value;

    int components_index = json_find_key(json, tokens, count, 0, "components");
    if (components_index < 0 || tokens[components_index].type != JSMN_OBJECT) {
        return -1;
    }
    if (json_parse_components(json, tokens, count, components_index, out_spec) != 0) {
        return -1;
    }

    int layers_index = json_find_key(json, tokens, count, 0, "layers");
    if (layers_index < 0) {
        return -1;
    }
    if (json_parse_layers(json, tokens, count, layers_index, out_spec) != 0) {
        return -1;
    }

    int fx_index = json_find_key(json, tokens, count, 0, "fx");
    if (fx_index >= 0 && tokens[fx_index].type == JSMN_OBJECT) {
        if (json_parse_fx(json, tokens, count, fx_index, out_spec) != 0) {
            return -1;
        }
    }

    int meta_index = json_find_key(json, tokens, count, 0, "metadata");
    if (meta_index >= 0 && tokens[meta_index].type == JSMN_OBJECT) {
        int ver_index = json_find_key(json, tokens, count, meta_index, "version");
        if (ver_index < 0 || json_parse_int(json, &tokens[ver_index], &int_value) != 0) {
            return -1;
        }
        if (int_value != 1) {
            return -1;
        }
        int conf_index = json_find_key(json, tokens, count, meta_index, "confidence");
        if (conf_index >= 0) {
            double confidence = 0.0;
            if (json_parse_float(json, &tokens[conf_index], &confidence) != 0) {
                return -1;
            }
            if (confidence < 0.0) {
                confidence = 0.0;
            }
            if (confidence > 1.0) {
                confidence = 1.0;
            }
            out_spec->confidence_x1000 = (uint32_t)(confidence * 1000.0);
        }
    } else {
        return -1;
    }

    return 0;
}
