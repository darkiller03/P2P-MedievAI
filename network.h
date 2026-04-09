#ifndef NETWORK_H
#define NETWORK_H

#define MAX_PEERS 10
extern char NODE_ID[32];
extern int server_socket;

int start_server(int port);
void connect_to_peer(const char *ip, int port);
void network_loop();
void send_update_to_peers(const char* update, int sender_sock);

#endif