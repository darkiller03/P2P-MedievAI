#include "tcp_relay_server.h"
#include "utils.h"
#include "connection.h"
#include "server.h"

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("Usage: %s <listen_port> [peer_ip:peer_port ...]\n", argv[0]);
        printf("Example: %s 9001 127.0.0.1:9002 127.0.0.1:9003\n", argv[0]);
        return 1;
    }

    unsigned short listen_port = 0;
    if (!parse_port(argv[1], &listen_port)) {
        printf("[ERROR] invalid listen port: %s\n", argv[1]);
        return 1;
    }

    if (!init_winsock()) {
        return 1;
    }

    int listen_sock = init_server(listen_port);
    if (listen_sock == -1) {
        return 1;
    }

    printf("[INFO] listening on 0.0.0.0:%u\n", listen_port);

    ConnectionList connections;
    memset(&connections, 0, sizeof(connections));

    for (int i = 2; i < argc; i++) {
        char peer_ip[64];
        unsigned short peer_port = 0;
        if (!parse_peer_target(argv[i], peer_ip, sizeof(peer_ip), &peer_port)) {
            printf("[WARN] skip invalid peer target: %s\n", argv[i]);
            continue;
        }
        connect_to_peer(&connections, peer_ip, peer_port);
    }

    run_event_loop(listen_sock, &connections);

    free_connection_list(&connections);
    close(listen_sock);
    return 0;
}
