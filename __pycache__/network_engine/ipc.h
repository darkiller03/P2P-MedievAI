#ifndef IPC_H
#define IPC_H

#define IPC_QUEUE_SIZE 50
#define IPC_MSG_SIZE 256

void ipc_init();
int ipc_send(const char* msg);
int ipc_receive(char* buffer);

#endif