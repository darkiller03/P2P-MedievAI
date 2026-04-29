CC = gcc
CFLAGS = -Wall -Wextra -O2 -D_POSIX_C_SOURCE=200809L
TARGET = p2p_node
SRCS = main.c utils.c connection.c server.c
OBJS = $(SRCS:.c=.o)
HEADERS = tcp_relay_server.h utils.h connection.h server.h

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(OBJS) $(HEADERS)
	$(CC) $(CFLAGS) -o $(TARGET) $(OBJS)

%.o: %.c $(HEADERS)
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(TARGET) $(OBJS) *.o

# For development: compile without message_protocol/conflict_resolution for now
# These can be added later when their dependencies are resolved
