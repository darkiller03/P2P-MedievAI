#include "tcp_relay_server.h"
#include "connection.h"

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

bool append_connection(ConnectionList *list, socket_t sock, const char *label) {
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

int send_all(socket_t sock, const char *data, int len) {
    int sent_total = 0;
    while (sent_total < len) {
        int sent_now = send(sock, data + sent_total, len - sent_total, 0);
        if (sent_now
#ifdef _WIN32
            == SOCKET_ERROR
#else
            == -1
#endif
        ) {
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
            printf("[WARN] send failed to %s (err=%d)\n", peer->label, SOCKET_ERRNO);
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

bool handle_incoming_data(ConnectionList *list, size_t sender_index, const char *data, int len) {
    Connection *sender = &list->items[sender_index];

    for (int i = 0; i < len; i++) {
        char ch = data[i];

        if (sender->line_len + 1 >= sender->line_cap) {
            if (!grow_line_buffer(sender)) {
                printf("[ERROR] out of memory growing line buffer for %s\n", sender->label);
                return false;
            }
        }

        sender->line_buffer[sender->line_len++] = ch;

        if (ch == '\n') {
            sender->line_buffer[sender->line_len] = '\0';
            printf("[RECV] %s -> %s", sender->label, sender->line_buffer);
            broadcast_message(list, sender_index, sender->line_buffer, (int)sender->line_len);
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