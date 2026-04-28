#ifndef UTILS_H
#define UTILS_H

#include <stdbool.h>

bool init_winsock(void);
bool parse_port(const char *text, unsigned short *port_out);
bool parse_peer_target(const char *peer, char *ip_out, size_t ip_out_size, unsigned short *port_out);

#endif // UTILS_H