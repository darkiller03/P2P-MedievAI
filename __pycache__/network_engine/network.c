#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include "network.h"

#define MAX_PEERS 10

char NODE_ID[32];
int server_socket;
int peer_sockets[MAX_PEERS];    
int peer_count = 0;             

int start_server(int port)
{
    struct sockaddr_in server_addr;

    server_socket = socket(AF_INET, SOCK_STREAM, 0);

    if (server_socket < 0)
    {
        perror("socket failed");
        exit(1);
    }

    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(port);

    if (bind(server_socket, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0)
    {
        perror("bind failed");
        exit(1);
    }

    if (listen(server_socket, 5) < 0)
    {
        perror("listen failed");
        exit(1);
    }

    printf("Node listening on port %d\n", port);

    return server_socket;
}

void network_loop()
{
    fd_set read_fds;
    int max_sd;
    char buffer[1024];

    while (1)
    {
        FD_ZERO(&read_fds);
        FD_SET(server_socket, &read_fds);
        max_sd = server_socket;

        for (int i = 0; i < peer_count; i++)
        {
            FD_SET(peer_sockets[i], &read_fds);
            if (peer_sockets[i] > max_sd)
                max_sd = peer_sockets[i];
        }

        int activity = select(max_sd + 1, &read_fds, NULL, NULL, NULL);
        if (activity < 0)
        {
            perror("select error");
            continue;
        }

        if (FD_ISSET(server_socket, &read_fds))
        {
            int new_socket = accept(server_socket, NULL, NULL);
            if (new_socket >= 0)
            {
                if (peer_count < MAX_PEERS)
                {
                    peer_sockets[peer_count++] = new_socket;
                    printf("New peer connected\n");
                    char join_msg[128];
                    snprintf(join_msg, sizeof(join_msg), "%s has joined the battle!", NODE_ID);
                    send_update_to_peers(join_msg, new_socket);
                }
                else
                {
                    close(new_socket);
                    printf("Max peers reached, connection refused\n");
                }
            }
        }

        for (int i = 0; i < peer_count; i++)
        {
            if (FD_ISSET(peer_sockets[i], &read_fds))
            {
                int n = recv(peer_sockets[i], buffer, sizeof(buffer) - 1, 0);
                if (n <= 0)
                {
                    close(peer_sockets[i]);
                    printf("Peer disconnected\n");
                    for (int j = i; j < peer_count - 1; j++)
                        peer_sockets[j] = peer_sockets[j + 1];
                    peer_count--;
                    i--;
                    continue;
                }

                buffer[n] = '\0';
                char* sender = strtok(buffer, "|");
                char* text = strtok(NULL, "|");

                if (sender && text && strcmp(sender, NODE_ID) != 0)
                {
                    printf("Message from %s: %s\n", sender, text);
                    send_update_to_peers(text, peer_sockets[i]);
                }
            }
        }
    }
}

void connect_to_peer(const char *ip, int port)
{
    if (peer_count >= MAX_PEERS)
    {
        printf("Cannot connect: max peers reached\n");
        return;
    }

    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0)
    {
        perror("socket failed");
        return;
    }

    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    if (inet_pton(AF_INET, ip, &addr.sin_addr) <= 0)
    {
        printf("Invalid IP address: %s\n", ip);
        close(sock);
        return;
    }

    if (connect(sock, (struct sockaddr*)&addr, sizeof(addr)) < 0)
    {
        perror("connect failed");
        close(sock);
        return;
    }

    peer_sockets[peer_count++] = sock;
    printf("Connected to peer %s:%d\n", ip, port);
}

void send_update_to_peers(const char* update, int sender_sock)
{
    char message[1024];
    snprintf(message, sizeof(message), "%s|%s", NODE_ID, update);

    for (int i = 0; i < peer_count; i++)
    {
        if (peer_sockets[i] != sender_sock)  // don't send back to the sender
        {
            send(peer_sockets[i], message, strlen(message), 0);
        }
    }
}