/*
 * reseau.c — Routeur UDP P2P Multi-plateforme (Windows / Mac / Linux)
 *
 * Fait le pont entre le jeu Python local et l'adversaire distant.
 * Supporte le mode P2P avec une configuration de ports flexible.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

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
    #include <errno.h>
    typedef int SOCKET;
    #define INVALID_SOCKET -1
    #define SOCKET_ERROR -1
    #define closesocket close
#endif

/* --- Configuration par défaut -------------------------------------------- */
#define PORT_IPC_IN   5000          /* Le C écoute le Python local ici        */
#define PORT_IPC_OUT  5001          /* Le C renvoie vers le Python local ici  */
#define BUFFER_SIZE   65536         /* Buffer augmenté pour les grosses armées */
#define ACK_MSG       "{\"type\": \"ack\", \"status\": \"ok\"}"

/* --- Variables de session ------------------------------------------------ */
int g_local_port_net = 6000;
int g_remote_port_net = 6001;
char g_remote_ip[64] = "127.0.0.1";
int g_port_ipc_in = 5000;
int g_port_ipc_out = 5001;
int g_is_initialized = 0;

/* ------------------------------------------------------------------------- */

static void print_error(const char *msg) {
#ifdef _WIN32
    fprintf(stderr, "[ERREUR] %s : %d\n", msg, WSAGetLastError());
#else
    fprintf(stderr, "[ERREUR] %s : %s\n", msg, strerror(errno));
#endif
}

static SOCKET create_udp_socket(const char *bind_ip, int port) {
    SOCKET sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == INVALID_SOCKET) {
        print_error("socket()");
        return INVALID_SOCKET;
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family      = AF_INET;
    addr.sin_port        = htons((u_short)port);
    addr.sin_addr.s_addr = inet_addr(bind_ip);

    if (bind(sock, (struct sockaddr *)&addr, sizeof(addr)) == SOCKET_ERROR) {
        print_error("bind()");
        closesocket(sock);
        return INVALID_SOCKET;
    }
    return sock;
}

int main(int argc, char *argv[]) {
    /* Paramètres : [port_local_net] [remote_ip] [remote_port] [port_ipc_in] [port_ipc_out] */
    if (argc >= 2) g_local_port_net = atoi(argv[1]);
    if (argc >= 3) strncpy(g_remote_ip, argv[2], 63);
    if (argc >= 4) g_remote_port_net = atoi(argv[3]);
    if (argc >= 5) g_port_ipc_in = atoi(argv[4]);
    if (argc >= 6) g_port_ipc_out = atoi(argv[5]);

#ifdef _WIN32
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        print_error("WSAStartup");
        return 1;
    }
#endif

    SOCKET socket_ipc = create_udp_socket("127.0.0.1", g_port_ipc_in);
    SOCKET socket_net = create_udp_socket("0.0.0.0",   g_local_port_net);
    
    if (socket_ipc == INVALID_SOCKET || socket_net == INVALID_SOCKET) {
#ifdef _WIN32
        WSACleanup();
#endif
        return 1;
    }

    printf("==================================================\n");
    printf("       ROUTEUR P2P MULTI-PLATEFORME              \n");
    printf("==================================================\n");
    printf("  [IPC] Port locale   : %d (In) / %d (Out)\n", g_port_ipc_in, g_port_ipc_out);
    printf("  [NET] Ecoute P2P    : %d\n", g_local_port_net);
    printf("  [NET] Destinataire  : %s:%d\n", g_remote_ip, g_remote_port_net);
    printf("==================================================\n\n");

    struct sockaddr_in remote_addr;
    memset(&remote_addr, 0, sizeof(remote_addr));
    remote_addr.sin_family      = AF_INET;
    remote_addr.sin_port        = htons(g_remote_port_net);
    remote_addr.sin_addr.s_addr = inet_addr(g_remote_ip);

    struct sockaddr_in local_python_addr;
    memset(&local_python_addr, 0, sizeof(local_python_addr));
    local_python_addr.sin_family      = AF_INET;
    local_python_addr.sin_port        = htons(g_port_ipc_out);
    local_python_addr.sin_addr.s_addr = inet_addr("127.0.0.1");

    char buffer[BUFFER_SIZE];
    struct sockaddr_in sender_addr;
    socklen_t sender_len;

    while (1) {
        fd_set read_fds;
        FD_ZERO(&read_fds);
        FD_SET(socket_ipc, &read_fds);
        FD_SET(socket_net, &read_fds);

        int max_fd = (socket_ipc > socket_net) ? (int)socket_ipc : (int)socket_net;
        int ready = select(max_fd + 1, &read_fds, NULL, NULL, NULL);

        if (ready == SOCKET_ERROR) {
            print_error("select()");
            break;
        }

        /* --- Flux SORTANT : Python -> Réseau --- */
        if (FD_ISSET(socket_ipc, &read_fds)) {
            sender_len = sizeof(sender_addr);
            int n = recvfrom(socket_ipc, buffer, BUFFER_SIZE - 1, 0, (struct sockaddr *)&sender_addr, &sender_len);
            if (n > 0) {
                buffer[n] = '\0';
                printf("[IPC -> NET] Envoi vers %s:%d\n", g_remote_ip, g_remote_port_net);
                sendto(socket_net, buffer, n, 0, (struct sockaddr *)&remote_addr, sizeof(remote_addr));
                
                /* Confirmation au Python (toujours envoyee pour ne pas bloquer localement) */
                sendto(socket_ipc, ACK_MSG, (int)strlen(ACK_MSG), 0, (struct sockaddr *)&sender_addr, sender_len);
            }
        }

        /* --- Flux ENTRANT : Réseau -> Python --- */
        if (FD_ISSET(socket_net, &read_fds)) {
            sender_len = sizeof(sender_addr);
            int n = recvfrom(socket_net, buffer, BUFFER_SIZE - 1, 0, (struct sockaddr *)&sender_addr, &sender_len);
            if (n > 0) {
                buffer[n] = '\0';
                printf("[NET -> IPC] Recu de %s:%d\n", inet_ntoa(sender_addr.sin_addr), ntohs(sender_addr.sin_port));
                
                /* Mise a jour dynamique de l'IP distante si on recoit un paquet */
                strncpy(g_remote_ip, inet_ntoa(sender_addr.sin_addr), 63);
                remote_addr.sin_port = sender_addr.sin_port; /* Mise a jour aussi du port P2P source */
                g_remote_port_net = ntohs(remote_addr.sin_port);
                
                sendto(socket_ipc, buffer, n, 0, (struct sockaddr *)&local_python_addr, sizeof(local_python_addr));
            }
        }
    }

    closesocket(socket_ipc);
    closesocket(socket_net);
#ifdef _WIN32
    WSACleanup();
#endif
    return 0;
}
