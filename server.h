#ifndef SERVER_H
#define SERVER_H

#include "tcp_relay_server.h"

int init_server(unsigned short listen_port);
bool accept_new_connection(int listen_sock, ConnectionList *list);
bool connect_to_peer(ConnectionList *list, const char *ip, unsigned short port);
void run_event_loop(int listen_sock, ConnectionList *connections);

#endif // SERVER_H