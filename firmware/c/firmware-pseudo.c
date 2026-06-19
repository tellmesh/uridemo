#include "uri_dispatch.h"

#include <stdio.h>
#include <string.h>

static void led_set(int on) {
  printf("LED %s\n", on ? "on" : "off");
}

void on_command(const char *uri, const char *json_payload) {
  uri_parts_t parts;
  if (!uri_parse(uri, &parts)) {
    return;
  }
  if (strcmp(parts.scheme, "device") != 0 || strcmp(parts.target, "device-01") != 0) {
    return;
  }
  if (strcmp(parts.resource, "led") == 0 && strcmp(parts.kind, "command") == 0 && strcmp(parts.operation, "set") == 0) {
    led_set(strstr(json_payload, "true") != NULL);
  }
  if (strcmp(parts.resource, "ping") == 0 && strcmp(parts.kind, "command") == 0) {
    printf("pong\n");
  }
}
