#include "network.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>

void* network_thread(void* arg)
{
    network_loop();
    return NULL;
}

int main(int argc, char *argv[])
{
    if (argc < 2)
    {
        printf("Usage: %s <listen_port> [peer_ip peer_port]\n", argv[0]);
        return 1;
    }

    int listen_port = atoi(argv[1]);
    start_server(listen_port);
    sprintf(NODE_ID, "node%d", listen_port);

    if (argc == 4)
    {
        const char* peer_ip = argv[2];
        int peer_port = atoi(argv[3]);
        connect_to_peer(peer_ip, peer_port);
        send_update_to_peers("Node joined the battle!", -1);
    }

    pthread_t net_thread;
    pthread_create(&net_thread, NULL, network_thread, NULL);

    char input[256];
    while (1)
    {
        printf("Enter message: ");
        if (fgets(input, sizeof(input), stdin) != NULL)
        {
            input[strcspn(input, "\n")] = 0; // remove newline
            if (strlen(input) > 0)
                send_update_to_peers(input, -1);
        }
    }

    pthread_join(net_thread, NULL);
    return 0;
}