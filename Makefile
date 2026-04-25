CC = gcc
CFLAGS = -Wall -Wextra -O2
TARGET = tcp_relay_server
SRCS = tcp_relay_server.c utils.c connection.c server.c
HEADERS = tcp_relay_server.h utils.h connection.h server.h

$(TARGET): $(SRCS) $(HEADERS)
	$(CC) $(CFLAGS) -o $(TARGET) $(SRCS)

clean:
	rm -f $(TARGET)

.PHONY: clean