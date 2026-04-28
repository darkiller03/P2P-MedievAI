#ifndef TCP_RELAY_SERVER_H
#define TCP_RELAY_SERVER_H

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
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
bool append_connection(ConnectionList *list, int sock, const char *label);
void remove_connection(ConnectionList *list, size_t index);
int send_all(int sock, const char *data, int len);
void broadcast_message(ConnectionList *list, size_t sender_index, const char *line, int line_len);
bool grow_line_buffer(Connection *c);
bool handle_incoming_data(ConnectionList *list, size_t sender_index, const char *data, int len);
int init_server(unsigned short listen_port);
bool accept_new_connection(int listen_sock, ConnectionList *list);
bool connect_to_peer(ConnectionList *list, const char *ip, unsigned short port);
void free_connection_list(ConnectionList *list);
void run_event_loop(int listen_sock, ConnectionList *connections);

#endif // TCP_RELAY_SERVER_H