#include "message_protocol.h"
#include <string.h>
#include <errno.h>
#include <stdio.h>

#ifdef _WIN32
    #include <winsock2.h>
    #define write(fd, data, len) send(fd, data, len, 0)
#else
    #include <arpa/inet.h>
    #include <unistd.h>
#endif

Message* message_new(const char *json_payload, size_t payload_len) {
    if (payload_len > MAX_MESSAGE_SIZE) {
        fprintf(stderr, "[ERROR] Message payload too large: %zu > %d\n", payload_len, MAX_MESSAGE_SIZE);
        return NULL;
    }

    Message *msg = (Message *)malloc(sizeof(Message));
    if (!msg) {
        perror("malloc");
        return NULL;
    }

    msg->data = (char *)malloc(payload_len);
    if (!msg->data) {
        perror("malloc");
        free(msg);
        return NULL;
    }

    memcpy(msg->data, json_payload, payload_len);
    msg->len = payload_len;
    msg->capacity = payload_len;

    return msg;
}

void message_free(Message *msg) {
    if (!msg) return;
    if (msg->data) free(msg->data);
    free(msg);
}

int message_write_to_socket(int sock, const Message *msg) {
    if (!msg || !msg->data) {
        errno = EINVAL;
        return -1;
    }

    // Write header (4 bytes, network byte order = big-endian)
    uint32_t len_net = htonl((uint32_t)msg->len);
    ssize_t written = write(sock, &len_net, MSG_HEADER_SIZE);
    if (written != MSG_HEADER_SIZE) {
        perror("write header");
        return -1;
    }

    // Write payload
    written = write(sock, msg->data, msg->len);
    if (written != (ssize_t)msg->len) {
        perror("write payload");
        return -1;
    }

    return MSG_HEADER_SIZE + msg->len;
}

bool message_send_all(int sock, const Message *msg) {
    if (!msg || !msg->data) {
        errno = EINVAL;
        return false;
    }

    // Allocate temp buffer for header + payload
    size_t total_len = MSG_HEADER_SIZE + msg->len;
    uint8_t *buffer = (uint8_t *)malloc(total_len);
    if (!buffer) {
        perror("malloc");
        return false;
    }

    // Write header
    uint32_t len_net = htonl((uint32_t)msg->len);
    memcpy(buffer, &len_net, MSG_HEADER_SIZE);

    // Write payload
    memcpy(buffer + MSG_HEADER_SIZE, msg->data, msg->len);

    // Send all
    size_t sent = 0;
    while (sent < total_len) {
        ssize_t n = write(sock, buffer + sent, total_len - sent);
        if (n <= 0) {
            perror("write");
            free(buffer);
            return false;
        }
        sent += n;
    }

    free(buffer);
    return true;
}

MessageReceiver* receiver_new(size_t initial_capacity) {
    MessageReceiver *recv = (MessageReceiver *)malloc(sizeof(MessageReceiver));
    if (!recv) {
        perror("malloc");
        return NULL;
    }

    recv->buffer = (uint8_t *)malloc(initial_capacity);
    if (!recv->buffer) {
        perror("malloc");
        free(recv);
        return NULL;
    }

    recv->buffer_len = 0;
    recv->buffer_cap = initial_capacity;
    recv->current_msg_len = 0;

    return recv;
}

void receiver_free(MessageReceiver *recv) {
    if (!recv) return;
    if (recv->buffer) free(recv->buffer);
    free(recv);
}

static bool ensure_capacity(MessageReceiver *recv, size_t needed) {
    while (recv->buffer_cap < needed) {
        size_t new_cap = recv->buffer_cap * 2;
        if (new_cap > MAX_MESSAGE_SIZE + MSG_HEADER_SIZE) {
            fprintf(stderr, "[ERROR] Message receiver buffer would exceed max size\n");
            return false;
        }

        uint8_t *new_buffer = (uint8_t *)realloc(recv->buffer, new_cap);
        if (!new_buffer) {
            perror("realloc");
            return false;
        }

        recv->buffer = new_buffer;
        recv->buffer_cap = new_cap;
    }
    return true;
}

int receiver_feed_data(MessageReceiver *recv, const uint8_t *data, size_t data_len) {
    if (!recv || !data || data_len == 0) {
        errno = EINVAL;
        return -1;
    }

    // Ensure capacity for incoming data
    if (!ensure_capacity(recv, recv->buffer_len + data_len)) {
        return -1;
    }

    // Append data to buffer
    memcpy(recv->buffer + recv->buffer_len, data, data_len);
    recv->buffer_len += data_len;

    // Try to parse message
    while (recv->buffer_len > 0) {
        // If we haven't read the header yet
        if (recv->current_msg_len == 0) {
            if (recv->buffer_len < MSG_HEADER_SIZE) {
                // Not enough data for header yet
                return 0;
            }

            // Read header (network byte order)
            uint32_t msg_len_net;
            memcpy(&msg_len_net, recv->buffer, MSG_HEADER_SIZE);
            recv->current_msg_len = ntohl(msg_len_net);

            if (recv->current_msg_len == 0 || recv->current_msg_len > MAX_MESSAGE_SIZE) {
                fprintf(stderr, "[ERROR] Invalid message length: %u\n", recv->current_msg_len);
                return -1;
            }

            // Remove header from buffer
            memmove(recv->buffer, recv->buffer + MSG_HEADER_SIZE, recv->buffer_len - MSG_HEADER_SIZE);
            recv->buffer_len -= MSG_HEADER_SIZE;
        }

        // Now we know the message length, wait for full payload
        if (recv->buffer_len < recv->current_msg_len) {
            // Not enough data yet
            return 0;
        }

        // We have a complete message
        return 1;
    }

    return 0;
}

Message* receiver_get_message(MessageReceiver *recv) {
    if (!recv || recv->current_msg_len == 0 || recv->buffer_len < recv->current_msg_len) {
        errno = EINVAL;
        return NULL;
    }

    // Create message from buffer
    Message *msg = message_new((const char *)recv->buffer, recv->current_msg_len);
    if (!msg) {
        return NULL;
    }

    // Remove message from buffer
    memmove(recv->buffer, recv->buffer + recv->current_msg_len, recv->buffer_len - recv->current_msg_len);
    recv->buffer_len -= recv->current_msg_len;
    recv->current_msg_len = 0;

    return msg;
}

bool receiver_has_message(const MessageReceiver *recv) {
    if (!recv) return false;
    return recv->current_msg_len > 0 && recv->buffer_len >= recv->current_msg_len;
}
