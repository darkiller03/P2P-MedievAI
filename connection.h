#ifndef CONNECTION_H
#define CONNECTION_H

#include "tcp_relay_server.h"

bool ensure_connection_capacity(ConnectionList *list);
bool append_connection(ConnectionList *list, int sock, const char *label, bool is_local_client);
void remove_connection(ConnectionList *list, size_t index);
int send_all(int sock, const char *data, int len);
void broadcast_message(ConnectionList *list, size_t sender_index, const char *line, int line_len);
void send_to_all_connections(ConnectionList *list, const char *line, int line_len);
bool grow_line_buffer(Connection *c);
bool handle_peer_incoming_data(ConnectionList *peer_list, ConnectionList *ipc_list, size_t sender_index, const char *data, int len);
bool handle_ipc_incoming_data(ConnectionList *peer_list, ConnectionList *ipc_list, size_t sender_index, const char *data, int len);
void free_connection_list(ConnectionList *list);

#endif // CONNECTION_H