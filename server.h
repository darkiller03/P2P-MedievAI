#ifndef SERVER_H
#define SERVER_H

#include "tcp_relay_server.h"

int init_server(unsigned short listen_port);
bool accept_new_connection(int listen_sock, ConnectionList *list, bool is_local_client);
bool connect_to_peer(ConnectionList *list, const char *ip, unsigned short port);
void run_event_loop(int peer_listen_sock, int ipc_listen_sock, ConnectionList *peer_connections, ConnectionList *ipc_connections, unsigned short node_port);

#endif // SERVER_H