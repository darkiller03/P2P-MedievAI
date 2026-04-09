#ifndef PEER_H
#define PEER_H

#define MAX_PEERS 32

typedef struct {
    int socket;
    char ip[16];
    int port;
} Peer;

void add_peer(int socket, char *ip, int port);
void remove_peer(int socket);
void broadcast_message(char *msg);

#endif