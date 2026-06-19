#ifndef URI_DISPATCH_H
#define URI_DISPATCH_H

#include <stddef.h>

typedef struct {
  char scheme[16];
  char target[32];
  char resource[32];
  char kind[12];
  char operation[32];
} uri_parts_t;

int uri_parse(const char *uri, uri_parts_t *out);

#endif
