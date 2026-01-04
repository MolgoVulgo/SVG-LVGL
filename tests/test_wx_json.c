#include <assert.h>
#include <string.h>

#include "wx_json.h"

static void test_parse_minimal(void) {
    const char* json =
        "{"
        "\"spec_id\":1234,"
        "\"name\":\"clear_day\","
        "\"components\":{"
        "\"decor\":\"SUN\","
        "\"cover\":\"NONE\","
        "\"particles\":\"NONE\","
        "\"atmos\":\"NONE\","
        "\"event\":\"NONE\""
        "},"
        "\"layers\":["
        "{\"id\":\"sun\",\"asset\":\"sun_core\",\"fx\":[\"ROTATE\"]}"
        "],"
        "\"fx\":{"
        "\"ROTATE\":{\"period_ms\":45000,\"pivot_x\":32,\"pivot_y\":32}"
        "},"
        "\"metadata\":{\"version\":1,\"confidence\":0.75}"
        "}";

    wx_icon_spec_t spec;
    int rc = wx_json_parse_spec(json, strlen(json), &spec);
    assert(rc == 0);
    assert(spec.spec_id == 1234u);
    assert(spec.decor == WX_DECOR_SUN);
    assert(spec.cover == WX_COVER_NONE);
    assert(spec.particles == WX_PART_NONE);
    assert(spec.atmos == WX_ATMOS_NONE);
    assert(spec.event == WX_EVENT_NONE);
    assert(spec.layer_count == 1);
    assert(strcmp(spec.layers[0].asset_key, "sun_core") == 0);
    assert(spec.layers[0].fx_mask & WX_FX_MASK(WX_FX_ROTATE));
    assert(spec.fx[WX_FX_ROTATE].period_ms == 45000);
    assert(spec.fx[WX_FX_ROTATE].pivot_x == 32);
    assert(spec.fx[WX_FX_ROTATE].pivot_y == 32);
    assert(spec.confidence_x1000 == 750);
}

static void test_parse_particles_fx(void) {
    const char* json =
        "{"
        "\"spec_id\":5678,"
        "\"name\":\"rain\","
        "\"components\":{"
        "\"decor\":\"NONE\","
        "\"cover\":\"CLOUD\","
        "\"particles\":\"RAIN\","
        "\"atmos\":\"NONE\","
        "\"event\":\"NONE\""
        "},"
        "\"layers\":["
        "{\"id\":\"cloud\",\"asset\":\"cloud\",\"fx\":[]},"
        "{\"id\":\"drop\",\"asset\":\"drop\",\"fx\":[\"FALL\"]}"
        "],"
        "\"fx\":{"
        "\"FALL\":{\"period_ms\":700,\"fall_dy\":15,\"phase_ms\":[0,200,400]}"
        "},"
        "\"metadata\":{\"version\":1}"
        "}";

    wx_icon_spec_t spec;
    int rc = wx_json_parse_spec(json, strlen(json), &spec);
    assert(rc == 0);
    assert(spec.cover == WX_COVER_CLOUD);
    assert(spec.particles == WX_PART_RAIN);
    assert(spec.layer_count == 2);
    assert(strcmp(spec.layers[1].asset_key, "drop") == 0);
    assert(spec.layers[1].fx_mask & WX_FX_MASK(WX_FX_FALL));
    assert(spec.fx[WX_FX_FALL].period_ms == 700);
    assert(spec.fx[WX_FX_FALL].fall_dy == 15);
    assert(spec.fx[WX_FX_FALL].phase_count == 3);
    assert(spec.fx[WX_FX_FALL].phase_ms[0] == 0);
    assert(spec.fx[WX_FX_FALL].phase_ms[1] == 200);
    assert(spec.fx[WX_FX_FALL].phase_ms[2] == 400);
}

int main(void) {
    test_parse_minimal();
    test_parse_particles_fx();
    return 0;
}
