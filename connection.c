#include "tcp_relay_server.h"
#include "connection.h"
#ifdef _WIN32
    #include <winsock2.h>
#else
    #include <unistd.h>
#endif

bool ensure_connection_capacity(ConnectionList *list) {
    if (list->count < list->cap) {
        return true;
    }

    size_t next_cap = (list->cap == 0) ? 16 : list->cap * 2;
    Connection *next = (Connection *)realloc(list->items, next_cap * sizeof(Connection));
    if (next == NULL) {
        return false;
    }

    list->items = next;
    list->cap = next_cap;
    return true;
}

#define MAX_SEEN_MESSAGE_IDS 2048
#define MAX_MESSAGE_ID_LEN 128

static char seen_message_ids[MAX_SEEN_MESSAGE_IDS][MAX_MESSAGE_ID_LEN];
static size_t seen_message_count = 0;
static size_t seen_message_next = 0;

static bool message_id_seen(const char *msg_id) {
    if (msg_id == NULL) {
        return false;
    }

    for (size_t i = 0; i < seen_message_count; i++) {
        if (strcmp(seen_message_ids[i], msg_id) == 0) {
            return true;
        }
    }
    return false;
}

static void mark_message_id_seen(const char *msg_id) {
    if (msg_id == NULL) {
        return;
    }

    if (seen_message_count < MAX_SEEN_MESSAGE_IDS) {
        strncpy(seen_message_ids[seen_message_count++], msg_id, MAX_MESSAGE_ID_LEN - 1);
        seen_message_ids[seen_message_count - 1][MAX_MESSAGE_ID_LEN - 1] = '\0';
        return;
    }

    strncpy(seen_message_ids[seen_message_next], msg_id, MAX_MESSAGE_ID_LEN - 1);
    seen_message_ids[seen_message_next][MAX_MESSAGE_ID_LEN - 1] = '\0';
    seen_message_next = (seen_message_next + 1) % MAX_SEEN_MESSAGE_IDS;
}

static bool parse_relay_message(const char *line, char *msg_id_out, size_t msg_id_cap, const char **payload_out) {
    const char *prefix = "RELAY|";
    size_t prefix_len = strlen(prefix);
    if (strncmp(line, prefix, prefix_len) != 0) {
        return false;
    }

    const char *id_start = line + prefix_len;
    const char *separator = strchr(id_start, '|');
    if (!separator) {
        return false;
    }

    size_t id_len = separator - id_start;
    if (id_len == 0 || id_len >= msg_id_cap) {
        return false;
    }

    memcpy(msg_id_out, id_start, id_len);
    msg_id_out[id_len] = '\0';
    *payload_out = separator + 1;
    return true;
}

static int create_relay_line(const char *msg_id, const char *payload, char *out, size_t out_cap) {
    if (!msg_id || !payload || !out) {
        return -1;
    }
    return snprintf(out, out_cap, "RELAY|%s|%s", msg_id, payload);
}

bool append_connection(ConnectionList *list, int sock, const char *label, bool is_local_client) {
    if (!ensure_connection_capacity(list)) {
        return false;
    }

    Connection *c = &list->items[list->count];
    c->socket = sock;
    c->line_cap = INITIAL_LINE_CAP;
    c->line_len = 0;
    c->line_buffer = (char *)malloc(c->line_cap);
    if (c->line_buffer == NULL) {
        return false;
    }
    c->line_buffer[0] = '\0';
    snprintf(c->label, sizeof(c->label), "%s", label);
    c->is_local_client = is_local_client;

    list->count++;
    return true;
}

void remove_connection(ConnectionList *list, size_t index) {
    if (index >= list->count) {
        return;
    }

    Connection *c = &list->items[index];
    printf("[INFO] disconnected: %s\n", c->label);
    close(c->socket);
    free(c->line_buffer);

    if (index != list->count - 1) {
        list->items[index] = list->items[list->count - 1];
    }
    list->count--;
}

int send_all(int sock, const char *data, int len) {
    int sent_total = 0;
    while (sent_total < len) {
        int sent_now = send(sock, data + sent_total, len - sent_total, 0);
        if (sent_now == -1) {
            return -1;
        }
        sent_total += sent_now;
    }
    return sent_total;
}

void broadcast_message(ConnectionList *list, size_t sender_index, const char *line, int line_len) {
    size_t i = 0;
    while (i < list->count) {
        if (i == sender_index) {
            i++;
            continue;
        }

        Connection *peer = &list->items[i];
        if (send_all(peer->socket, line, line_len) == -1) {
            printf("[WARN] send failed to %s (err=%d)\n", peer->label, errno);
            remove_connection(list, i);
            if (sender_index == list->count) {
                break;
            }
            if (i < sender_index) {
                sender_index--;
            }
            continue;
        }
        i++;
    }
}

void send_to_all_connections(ConnectionList *list, const char *line, int line_len) {
    if (!list) {
        return;
    }

    for (size_t i = 0; i < list->count; i++) {
        Connection *c = &list->items[i];
        if (send_all(c->socket, line, line_len) == -1) {
            printf("[WARN] send failed to %s (err=%d)\n", c->label, errno);
            remove_connection(list, i);
            i--;
        }
    }
}

bool grow_line_buffer(Connection *c) {
    size_t next_cap = c->line_cap * 2;
    char *next = (char *)realloc(c->line_buffer, next_cap);
    if (next == NULL) {
        return false;
    }
    c->line_buffer = next;
    c->line_cap = next_cap;
    return true;
}

static void append_char_to_line(Connection *sender, char ch) {
    if (sender->line_len + 1 >= sender->line_cap) {
        if (!grow_line_buffer(sender)) {
            fprintf(stderr, "[ERROR] out of memory growing line buffer for %s\n", sender->label);
            return;
        }
    }
    sender->line_buffer[sender->line_len++] = ch;
}

static void create_message_id(char *msg_id, size_t msg_id_cap, unsigned short port, unsigned int counter) {
    snprintf(msg_id, msg_id_cap, "%u:%u", (unsigned int)port, counter);
}

static bool parse_relay_message(const char *line, char *msg_id_out, size_t msg_id_cap, const char **payload_out) {
    const char *prefix = "RELAY|";
    size_t prefix_len = strlen(prefix);
    if (strncmp(line, prefix, prefix_len) != 0) {
        return false;
    }

    const char *id_start = line + prefix_len;
    const char *separator = strchr(id_start, '|');
    if (!separator) {
        return false;
    }

    size_t id_len = separator - id_start;
    if (id_len == 0 || id_len >= msg_id_cap) {
        return false;
    }

    memcpy(msg_id_out, id_start, id_len);
    msg_id_out[id_len] = '\0';
    *payload_out = separator + 1;
    return true;
}

static bool message_id_seen(const char *msg_id) {
    if (!msg_id) {
        return false;
    }

    for (size_t i = 0; i < seen_message_count; i++) {
        if (strcmp(seen_message_ids[i], msg_id) == 0) {
            return true;
        }
    }
    return false;
}

static void mark_message_id_seen(const char *msg_id) {
    if (!msg_id) {
        return;
    }

    if (seen_message_count < MAX_SEEN_MESSAGE_IDS) {
        strncpy(seen_message_ids[seen_message_count], msg_id, MAX_MESSAGE_ID_LEN - 1);
        seen_message_ids[seen_message_count][MAX_MESSAGE_ID_LEN - 1] = '\0';
        seen_message_count++;
        return;
    }

    strncpy(seen_message_ids[seen_message_next], msg_id, MAX_MESSAGE_ID_LEN - 1);
    seen_message_ids[seen_message_next][MAX_MESSAGE_ID_LEN - 1] = '\0';
    seen_message_next = (seen_message_next + 1) % MAX_SEEN_MESSAGE_IDS;
}

static int create_relay_line(const char *msg_id, const char *payload, char *out, size_t out_cap) {
    if (!msg_id || !payload || !out) {
        return -1;
    }
    return snprintf(out, out_cap, "RELAY|%s|%s", msg_id, payload);
}

static bool handle_peer_line(ConnectionList *peer_list, ConnectionList *ipc_list, size_t sender_index, const char *line, unsigned short node_port) {
    char msg_id[MAX_MESSAGE_ID_LEN];
    const char *payload = NULL;

    if (parse_relay_message(line, msg_id, sizeof(msg_id), &payload)) {
        if (message_id_seen(msg_id)) {
            return true;
        }

        mark_message_id_seen(msg_id);
        printf("[RELAY] received message %s from peer %s\n", msg_id, peer_list->items[sender_index].label);

        broadcast_message(peer_list, sender_index, line, (int)strlen(line));
        if (ipc_list && ipc_list->count > 0) {
            send_to_all_connections(ipc_list, payload, (int)strlen(payload));
        }
        return true;
    }

    static unsigned int local_seq = 1;
    char local_msg_id[MAX_MESSAGE_ID_LEN];
    create_message_id(local_msg_id, sizeof(local_msg_id), node_port, local_seq++);
    mark_message_id_seen(local_msg_id);

    char wrapped_line[4096];
    if (create_relay_line(local_msg_id, line, wrapped_line, sizeof(wrapped_line)) < 0) {
        return false;
    }

    broadcast_message(peer_list, sender_index, wrapped_line, (int)strlen(wrapped_line));
    if (ipc_list && ipc_list->count > 0) {
        send_to_all_connections(ipc_list, line, (int)strlen(line));
    }
    return true;
}

static bool handle_ipc_line(ConnectionList *peer_list, size_t sender_index, const char *line, unsigned short node_port) {
    static unsigned int local_seq = 1;
    char local_msg_id[MAX_MESSAGE_ID_LEN];
    create_message_id(local_msg_id, sizeof(local_msg_id), node_port, local_seq++);
    mark_message_id_seen(local_msg_id);

    char wrapped_line[4096];
    if (create_relay_line(local_msg_id, line, wrapped_line, sizeof(wrapped_line)) < 0) {
        return false;
    }

    broadcast_message(peer_list, (size_t)-1, wrapped_line, (int)strlen(wrapped_line));
    return true;
}

bool handle_peer_incoming_data(ConnectionList *peer_list, ConnectionList *ipc_list, size_t sender_index, const char *data, int len) {
    Connection *sender = &peer_list->items[sender_index];

    for (int i = 0; i < len; i++) {
        char ch = data[i];
        append_char_to_line(sender, ch);

        if (ch == '\n') {
            sender->line_buffer[sender->line_len] = '\0';
            printf("[RECV] peer %s -> %s", sender->label, sender->line_buffer);
            if (!handle_peer_line(peer_list, ipc_list, sender_index, sender->line_buffer, 0)) {
                return false;
            }
            sender->line_len = 0;
        }
    }

    return true;
}

bool handle_ipc_incoming_data(ConnectionList *peer_list, ConnectionList *ipc_list, size_t sender_index, const char *data, int len) {
    Connection *sender = &ipc_list->items[sender_index];

    for (int i = 0; i < len; i++) {
        char ch = data[i];
        append_char_to_line(sender, ch);

        if (ch == '\n') {
            sender->line_buffer[sender->line_len] = '\0';
            printf("[RECV] local client %s -> %s", sender->label, sender->line_buffer);
            if (!handle_ipc_line(peer_list, sender_index, sender->line_buffer, 0)) {
                return false;
            }
            sender->line_len = 0;
        }
    }

    return true;
}

void free_connection_list(ConnectionList *list) {
    for (size_t i = 0; i < list->count; i++) {
        close(list->items[i].socket);
        free(list->items[i].line_buffer);
    }
    free(list->items);
    list->items = NULL;
    list->count = 0;
    list->cap = 0;
}