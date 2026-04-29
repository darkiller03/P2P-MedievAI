#include "p2p_node.h"
#include "peer_discovery.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/select.h>
#include <json-c/json.h>

P2PNode* p2p_node_new(const char *player_id, uint16_t listen_port) {
    if (!player_id) {
        fprintf(stderr, "[ERROR] p2p_node_new: player_id is NULL\n");
        return NULL;
    }

    P2PNode *node = (P2PNode *)malloc(sizeof(P2PNode));
    if (!node) {
        perror("malloc");
        return NULL;
    }

    node->peers = peer_manager_new(player_id, listen_port);
    if (!node->peers) {
        free(node);
        return NULL;
    }

    node->ipc = ipc_server_new(player_id);
    if (!node->ipc) {
        peer_manager_free(node->peers);
        free(node);
        return NULL;
    }

    node->clock = clock_manager_new(player_id);
    if (!node->clock) {
        ipc_server_free(node->ipc);
        peer_manager_free(node->peers);
        free(node);
        return NULL;
    }

    node->running = false;

    return node;
}

void p2p_node_free(P2PNode *node) {
    if (!node) return;

    if (node->clock) clock_manager_free(node->clock);
    if (node->ipc) ipc_server_free(node->ipc);
    if (node->peers) peer_manager_free(node->peers);

    free(node);
}

bool p2p_node_init(P2PNode *node) {
    if (!node) return false;

    if (!peer_manager_init_listen(node->peers)) {
        fprintf(stderr, "[ERROR] Failed to initialize peer listening socket\n");
        return false;
    }

    if (!ipc_server_init(node->ipc)) {
        fprintf(stderr, "[ERROR] Failed to initialize IPC server\n");
        return false;
    }

    printf("[INFO] P2P Node initialized for player %s\n", node->peers->my_player_id);
    return true;
}

bool p2p_node_connect_initial_peers(P2PNode *node, const char *config_file) {
    if (!node || !config_file) {
        return false;
    }

    PeerList *peers = load_peers_from_file(config_file);
    if (!peers) {
        fprintf(stderr, "[WARN] No peers to connect to\n");
        return true;  // Not critical if no peers
    }

    for (size_t i = 0; i < peer_list_count(peers); i++) {
        const DiscoveredPeer *peer = peer_list_get(peers, i);
        if (peer) {
            peer_manager_connect_to_peer(node->peers, peer->ip, peer->port, peer->player_id);
        }
    }

    peer_list_free(peers);
    return true;
}

static void process_ipc_message(P2PNode *node, const char *json_str, size_t json_len) {
    if (!node || !json_str) return;

    // Parse JSON
    json_object *obj = json_tokener_parse_ex(
        json_tokener_new(),
        json_str,
        (int)json_len
    );

    if (!obj) {
        fprintf(stderr, "[WARN] Failed to parse IPC JSON message\n");
        return;
    }

    const char *cmd = json_object_get_string(json_object_object_get(obj, "cmd"));
    if (!cmd) {
        fprintf(stderr, "[WARN] IPC message missing 'cmd' field\n");
        json_object_put(obj);
        return;
    }

    printf("[DEBUG] IPC message: cmd=%s\n", cmd);

    if (strcmp(cmd, "ACTION") == 0) {
        // Python is requesting an action (move, attack, etc.)
        const char *type = json_object_get_string(json_object_object_get(obj, "type"));
        
        // Increment clock for local action
        LamportClock clock = clock_increment(node->clock);

        // Create outgoing message to peers
        json_object *out_msg = json_object_new_object();
        json_object_object_add(out_msg, "type", json_object_new_string(type));
        
        // Copy relevant fields
        json_object_object_add(out_msg, "clock", json_object_new_int64(clock));
        json_object_object_add(out_msg, "player_id", json_object_new_string(node->peers->my_player_id));

        // Copy unit_id, coordinates, etc. from Python message
        struct json_object_iterator it = json_object_iter_begin(obj);
        struct json_object_iterator it_end = json_object_iter_end(obj);
        while (!json_object_iter_equal(&it, &it_end)) {
            const char *key = json_object_iter_peek_name(&it);
            if (strcmp(key, "cmd") != 0 && strcmp(key, "type") != 0) {
                json_object *val = json_object_iter_peek_value(&it);
                json_object_object_add(out_msg, key, json_object_get(val));
            }
            json_object_iter_next(&it);
        }

        // Broadcast to all peers
        const char *out_str = json_object_to_json_string(out_msg);
        Message *net_msg = message_new(out_str, strlen(out_str));
        if (net_msg) {
            peer_manager_broadcast(node->peers, (size_t)-1, net_msg);
            message_free(net_msg);
        }

        json_object_put(out_msg);

    } else if (strcmp(cmd, "QUERY") == 0) {
        // Python is querying state (not yet used, for future)
        printf("[DEBUG] Query command (not yet implemented)\n");
    }

    json_object_put(obj);
}

static void process_peer_message(P2PNode *node, size_t peer_index, const char *json_str, size_t json_len) {
    if (!node || !json_str || peer_index >= peer_manager_count(node->peers)) {
        return;
    }

    // Parse JSON
    json_object *obj = json_tokener_parse_ex(
        json_tokener_new(),
        json_str,
        (int)json_len
    );

    if (!obj) {
        fprintf(stderr, "[WARN] Failed to parse peer JSON message\n");
        return;
    }

    const char *type = json_object_get_string(json_object_object_get(obj, "type"));
    if (!type) {
        fprintf(stderr, "[WARN] Peer message missing 'type' field\n");
        json_object_put(obj);
        return;
    }

    // Update clock based on received message
    json_object *clock_obj = json_object_object_get(obj, "clock");
    if (clock_obj) {
        LamportClock received_clock = (LamportClock)json_object_get_int64(clock_obj);
        clock_update(node->clock, received_clock);
    }

    printf("[DEBUG] Peer %s message: type=%s\n", 
           peer_manager_get_peer(node->peers, peer_index)->player_id, type);

    // Forward to Python
    Message *ipc_msg = message_new(json_str, json_len);
    if (ipc_msg) {
        ipc_server_send(node->ipc, ipc_msg);
        message_free(ipc_msg);
    }

    // Relay to other peers (except sender)
    Message *relay_msg = message_new(json_str, json_len);
    if (relay_msg) {
        peer_manager_broadcast(node->peers, peer_index, relay_msg);
        message_free(relay_msg);
    }

    json_object_put(obj);
}

void p2p_node_run(P2PNode *node) {
    if (!node) return;

    node->running = true;
    printf("[INFO] P2P Node starting main event loop\n");

    while (node->running) {
        // Try to accept new peer connections
        while (peer_manager_accept_inbound(node->peers)) {
            // Keep accepting while connections are available
        }

        // Try to accept Python client
        if (!ipc_server_is_connected(node->ipc)) {
            ipc_server_accept(node->ipc);
        }

        // Try to receive from Python
        if (ipc_server_is_connected(node->ipc)) {
            if (ipc_server_recv(node->ipc)) {
                Message *msg = ipc_server_get_message(node->ipc);
                if (msg) {
                    process_ipc_message(node, (const char *)msg->data, msg->len);
                    message_free(msg);
                }
            }
        }

        // Try to receive from any peer
        size_t sender_index = peer_manager_recv_any(node->peers);
        if (sender_index != (size_t)-1) {
            Message *msg = peer_manager_get_message(node->peers, sender_index);
            if (msg) {
                process_peer_message(node, sender_index, (const char *)msg->data, msg->len);
                message_free(msg);
            }
        }

        // Small sleep to avoid busy-waiting
        usleep(10000);  // 10ms
    }

    printf("[INFO] P2P Node shutting down\n");
}

void p2p_node_stop(P2PNode *node) {
    if (!node) return;
    node->running = false;
}
