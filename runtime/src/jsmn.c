#include "jsmn.h"

#include <stddef.h>

enum {
    JSMN_ERROR_NOMEM = -1,
    JSMN_ERROR_INVAL = -2,
    JSMN_ERROR_PART = -3
};

static jsmntok_t* jsmn_alloc_token(jsmn_parser* parser, jsmntok_t* tokens, unsigned int num_tokens) {
    if (parser->toknext >= num_tokens) {
        return NULL;
    }
    jsmntok_t* tok = &tokens[parser->toknext++];
    tok->start = -1;
    tok->end = -1;
    tok->size = 0;
    tok->parent = -1;
    tok->type = JSMN_UNDEFINED;
    return tok;
}

static void jsmn_fill_token(jsmntok_t* token, jsmntype_t type, int start, int end) {
    token->type = type;
    token->start = start;
    token->end = end;
    token->size = 0;
}

static int jsmn_parse_primitive(
    jsmn_parser* parser,
    const char* js,
    size_t len,
    jsmntok_t* tokens,
    unsigned int num_tokens
) {
    int start = (int)parser->pos;
    for (; parser->pos < len; parser->pos++) {
        char c = js[parser->pos];
        if (c == '\t' || c == '\r' || c == '\n' || c == ' ' || c == ',' || c == ']' || c == '}') {
            jsmntok_t* token = jsmn_alloc_token(parser, tokens, num_tokens);
            if (!token) {
                parser->pos = start;
                return JSMN_ERROR_NOMEM;
            }
            jsmn_fill_token(token, JSMN_PRIMITIVE, start, (int)parser->pos);
            token->parent = parser->toksuper;
            parser->pos--;
            return 0;
        }
        if (c < 32 || c == '\"' || c == '\\') {
            parser->pos = start;
            return JSMN_ERROR_INVAL;
        }
    }
    parser->pos = start;
    return JSMN_ERROR_PART;
}

static int jsmn_parse_string(
    jsmn_parser* parser,
    const char* js,
    size_t len,
    jsmntok_t* tokens,
    unsigned int num_tokens
) {
    int start = (int)parser->pos;
    parser->pos++;
    for (; parser->pos < len; parser->pos++) {
        char c = js[parser->pos];
        if (c == '\"') {
            jsmntok_t* token = jsmn_alloc_token(parser, tokens, num_tokens);
            if (!token) {
                parser->pos = start;
                return JSMN_ERROR_NOMEM;
            }
            jsmn_fill_token(token, JSMN_STRING, start + 1, (int)parser->pos);
            token->parent = parser->toksuper;
            return 0;
        }
        if (c == '\\' && parser->pos + 1 < len) {
            parser->pos++;
            continue;
        }
    }
    parser->pos = start;
    return JSMN_ERROR_PART;
}

void jsmn_init(jsmn_parser* parser) {
    parser->pos = 0;
    parser->toknext = 0;
    parser->toksuper = -1;
}

int jsmn_parse(
    jsmn_parser* parser,
    const char* js,
    size_t len,
    jsmntok_t* tokens,
    unsigned int num_tokens
) {
    for (; parser->pos < len; parser->pos++) {
        char c = js[parser->pos];
        switch (c) {
            case '{':
            case '[': {
                jsmntok_t* token = jsmn_alloc_token(parser, tokens, num_tokens);
                if (!token) {
                    return JSMN_ERROR_NOMEM;
                }
                token->type = (c == '{') ? JSMN_OBJECT : JSMN_ARRAY;
                token->start = (int)parser->pos;
                token->parent = parser->toksuper;
                parser->toksuper = (int)(parser->toknext - 1);
                break;
            }
            case '}':
            case ']': {
                jsmntype_t type = (c == '}') ? JSMN_OBJECT : JSMN_ARRAY;
                int i = (int)parser->toknext - 1;
                for (; i >= 0; i--) {
                    if (tokens[i].start != -1 && tokens[i].end == -1) {
                        if (tokens[i].type != type) {
                            return JSMN_ERROR_INVAL;
                        }
                        tokens[i].end = (int)parser->pos + 1;
                        parser->toksuper = tokens[i].parent;
                        break;
                    }
                }
                if (i < 0) {
                    return JSMN_ERROR_INVAL;
                }
                break;
            }
            case '\"': {
                int r = jsmn_parse_string(parser, js, len, tokens, num_tokens);
                if (r < 0) {
                    return r;
                }
                if (parser->toksuper != -1) {
                    tokens[parser->toksuper].size++;
                }
                break;
            }
            case '\t':
            case '\r':
            case '\n':
            case ' ':
            case ':':
            case ',': {
                break;
            }
            default: {
                int r = jsmn_parse_primitive(parser, js, len, tokens, num_tokens);
                if (r < 0) {
                    return r;
                }
                if (parser->toksuper != -1) {
                    tokens[parser->toksuper].size++;
                }
                break;
            }
        }
    }

    for (unsigned int i = parser->toknext; i > 0; i--) {
        if (tokens[i - 1].start != -1 && tokens[i - 1].end == -1) {
            return JSMN_ERROR_PART;
        }
    }

    return (int)parser->toknext;
}
