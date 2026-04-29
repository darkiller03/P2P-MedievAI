#ifndef MESSAGE_PROTOCOL_H
#define MESSAGE_PROTOCOL_H

#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>

/**
 * Length-prefixed message protocol for P2P network communication
 * 
 * Format: [4 bytes: uint32_t length (network byte order)][length bytes: UTF-8 JSON payload]
 * 
 * This ensures TCP stream safety by explicitly framing messages.
 */

#define MAX_MESSAGE_SIZE (1024 * 1024)  // 1MB max message
#define MSG_HEADER_SIZE 4

typedef struct {
    char *data;      // JSON payload (NOT null-terminated, use len for length)
    size_t len;      // Payload length in bytes
    size_t capacity; // Allocated capacity
} Message;

/**
 * Create a new message with given JSON content
 * Returns NULL on failure
 */
Message* message_new(const char *json_payload, size_t payload_len);

/**
 * Free a message
 */
void message_free(Message *msg);

/**
 * Write a message to socket in length-prefixed format
 * Returns number of bytes written on success, -1 on error
 */
int message_write_to_socket(int sock, const Message *msg);

/**
 * Send a complete length-prefixed message (all at once)
 * Returns true on success, false on error
 */
bool message_send_all(int sock, const Message *msg);

/**
 * Message receiver state for handling TCP stream fragmentation
 */
typedef struct {
    uint8_t *buffer;       // Receive buffer
    size_t buffer_len;     // Current bytes in buffer
    size_t buffer_cap;     // Allocated capacity
    uint32_t current_msg_len; // Length of current message being received (0 = reading header)
} MessageReceiver;

/**
 * Create a new message receiver
 */
MessageReceiver* receiver_new(size_t initial_capacity);

/**
 * Free a receiver
 */
void receiver_free(MessageReceiver *recv);

/**
 * Feed data into receiver from socket recv()
 * Returns:
 *   1 if a complete message is ready (call receiver_get_message)
 *   0 if more data needed
 *  -1 on error
 */
int receiver_feed_data(MessageReceiver *recv, const uint8_t *data, size_t data_len);

/**
 * Get the next complete message (only call after receiver_feed_data returns 1)
 * Caller owns the returned Message
 */
Message* receiver_get_message(MessageReceiver *recv);

/**
 * Check if receiver has a complete message ready
 */
bool receiver_has_message(const MessageReceiver *recv);

#endif // MESSAGE_PROTOCOL_H
