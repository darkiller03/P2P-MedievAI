#include "tcp_relay_server.h"
#include "utils.h"

bool init_winsock(void) {
#ifdef _WIN32
    WSADATA wsa_data;
    int result = WSAStartup(MAKEWORD(2, 2), &wsa_data);
    if (result != 0) {
        printf("[ERROR] WSAStartup failed: %d\n", result);
        return false;
    }
#endif
    return true;
}

bool parse_port(const char *text, unsigned short *port_out) {
    long value = strtol(text, NULL, 10);
    if (value <= 0 || value > 65535) {
        return false;
    }
    *port_out = (unsigned short)value;
    return true;
}

bool parse_peer_target(const char *peer, char *ip_out, size_t ip_out_size, unsigned short *port_out) {
    const char *sep = strrchr(peer, ':');
    if (sep == NULL) {
        return false;
    }

    size_t ip_len = (size_t)(sep - peer);
    if (ip_len == 0 || ip_len >= ip_out_size) {
        return false;
    }

    memcpy(ip_out, peer, ip_len);
    ip_out[ip_len] = '\0';

    return parse_port(sep + 1, port_out);
}