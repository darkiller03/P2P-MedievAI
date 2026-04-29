#ifndef TCP_RELAY_SERVER_H
#define TCP_RELAY_SERVER_H

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")
    typedef int socklen_t;
#else
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <arpa/inet.h>
    #include <unistd.h>
#endif

#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define RECV_CHUNK 2048
#define INITIAL_LINE_CAP 1024

typedef struct Connection {
    int socket;
    char label[64];
    char *line_buffer;
    size_t line_len;
    size_t line_cap;
    bool is_local_client;  // True if IPC connection, false if peer connection
} Connection;

typedef struct ConnectionList {
    Connection *items;
    size_t count;
    size_t cap;
} ConnectionList;

// Function prototypes
bool init_winsock(void);
bool parse_port(const char *text, unsigned short *port_out);
bool parse_peer_target(const char *peer, char *ip_out, size_t ip_out_size, unsigned short *port_out);
bool ensure_connection_capacity(ConnectionList *list);
// Deprecated old relay architecture - replaced by two-socket design in server.h
// These prototypes are kept only for reference and should not be used.

#endif // TCP_RELAY_SERVER_H