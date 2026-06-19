#include "uri_dispatch.h"

#include <stdio.h>
#include <string.h>

static int copy_part(char *dst, size_t dst_size, const char *start, size_t len) {
  if (len == 0 || len >= dst_size) {
    return 0;
  }
  memcpy(dst, start, len);
  dst[len] = '\0';
  return 1;
}

int uri_parse(const char *uri, uri_parts_t *out) {
  const char *scheme_end = strstr(uri, "://");
  if (!scheme_end) {
    return 0;
  }
  memset(out, 0, sizeof(*out));
  if (!copy_part(out->scheme, sizeof(out->scheme), uri, (size_t)(scheme_end - uri))) {
    return 0;
  }

  const char *cursor = scheme_end + 3;
  const char *target_end = strchr(cursor, '/');
  if (!target_end || !copy_part(out->target, sizeof(out->target), cursor, (size_t)(target_end - cursor))) {
    return 0;
  }

  char path[128];
  if (!copy_part(path, sizeof(path), target_end + 1, strlen(target_end + 1))) {
    return 0;
  }

  char *parts[3] = {0};
  size_t count = 0;
  char *token = strtok(path, "/");
  while (token && count < 3) {
    parts[count++] = token;
    token = strtok(NULL, "/");
  }

  if (count == 2) {
    snprintf(out->resource, sizeof(out->resource), "%s", out->scheme);
    snprintf(out->kind, sizeof(out->kind), "%s", parts[0]);
    snprintf(out->operation, sizeof(out->operation), "%s", parts[1]);
    return strcmp(parts[0], "command") == 0 || strcmp(parts[0], "query") == 0;
  }
  if (count == 3) {
    snprintf(out->resource, sizeof(out->resource), "%s", parts[0]);
    snprintf(out->kind, sizeof(out->kind), "%s", parts[1]);
    snprintf(out->operation, sizeof(out->operation), "%s", parts[2]);
    return strcmp(parts[1], "command") == 0 || strcmp(parts[1], "query") == 0;
  }
  return 0;
}
