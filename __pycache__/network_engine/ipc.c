#include <stdio.h>
#include <string.h>
#include "ipc.h"

static char queue[IPC_QUEUE_SIZE][IPC_MSG_SIZE];
static int head = 0;
static int tail = 0;

void ipc_init()
{
    head = 0;
    tail = 0;
}

int ipc_send(const char* msg)
{
    int next = (tail + 1) % IPC_QUEUE_SIZE;

    if (next == head)
    {
        printf("IPC queue full\n");
        return -1;
    }

    strncpy(queue[tail], msg, IPC_MSG_SIZE - 1);
    queue[tail][IPC_MSG_SIZE - 1] = '\0';

    tail = next;
    return 0;
}

int ipc_receive(char* buffer)
{
    if (head == tail)
    {
        return -1;
    }

    strncpy(buffer, queue[head], IPC_MSG_SIZE);
    head = (head + 1) % IPC_QUEUE_SIZE;

    return 0;
}