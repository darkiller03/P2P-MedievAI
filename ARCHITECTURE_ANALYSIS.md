# P2P-MedievAI Project Architecture Analysis

## Executive Summary

The P2P-MedievAI project implements a **hybrid network architecture** combining centralized relay forwarding with distributed game state ownership. Each player runs their own Python game engine with a network bridge that synchronizes state via a TCP relay server. While labeled "P2P," the implementation is more accurately described as a **relay-based distributed game** with **per-unit ownership enforcement**.

---

## 1. Current Architecture

### 1.1 Architecture Type: **Relay-Based Distributed Game (Hybrid P2P)**

```
Player 1 (Python)          Player 2 (Python)           Player 3 (Python)
    ↓                           ↓                            ↓
 P2PClient                  P2PClient                    P2PClient
 (Socket)                   (Socket)                     (Socket)
    ↓                           ↓                            ↓
    └───────────────────────────┴────────────────────────────┘
                          ↓
              TCP Relay Server (C)
              [tcp_relay_server.c]
              - Accepts incoming connections
              - Broadcasts messages to all peers
              - No game logic, purely relay
```

**Key Characteristics:**
- **Centralized relay**: TCP relay server at fixed address/port forwards all messages
- **Distributed game engines**: Each player has independent Python `SimpleEngine` instance
- **Distributed authority**: Each player has ultimate authority over their own units (via ownership)
- **No persistent server state**: Relay does not maintain game state, only forwards messages
- **Stateless forwarding**: Relay is protocol-agnostic and doesn't interpret game messages

### 1.2 Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│  Player 1's Game Instance (Python)                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Main.py                                                │
│    ├─ NetworkBridgeV2                                  │
│    │   ├─ P2PClient (TCP socket to relay)              │
│    │   ├─ OwnershipTracker (unit_id → player_id)       │
│    │   └─ NetworkIntegrator                            │
│    │       ├─ Processes incoming messages              │
│    │       ├─ Publishes local state                    │
│    │       └─ Enforces ownership rules                 │
│    │                                                   │
│    ├─ SimpleEngine (local copy)                        │
│    │   ├─ Units list (all alive units)                │
│    │   ├─ units_by_id (fast lookup)                   │
│    │   ├─ unit_ownership (owner per unit)             │
│    │   └─ step(dt, generals)                          │
│    │                                                   │
│    └─ General (AI decision maker)                      │
│        └─ give_orders(engine) → produce Actions       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 1.3 Alternative Implementation: network_engine/ (Unused)

The `network_engine/` directory contains a more elaborate P2P implementation:
- `network.c`: Multi-peer networking with peer-to-peer connections
- `main.c`: Standalone P2P node executable
- `ipc.c/h`: In-process message queue for IPC between threads
- `peer.c`, `protocol.c`: Stubs (empty, not implemented)

**Status**: This appears to be experimental/legacy code. The main project uses `tcp_relay_server` exclusively.

---

## 2. Python and C Component Interaction

### 2.1 Communication Model: **Text-Based Network Protocol**

**No Direct IPC**: Python and C components do NOT run in the same process. Instead:
- Python game instances connect via TCP socket to the relay server
- All communication uses **newline-delimited text messages**
- Messages are **pipe-delimited** fields: `TYPE|field1|field2|...`

### 2.2 Connection Flow

```
Python (Main.py)
    ↓
P2PClient.__init__(host="127.0.0.1", port=9001)
    ↓
socket.create_connection((host, port))  # TCP socket
    ↓
TCP Relay Server (C)
    ├─ Accepts socket
    ├─ Adds to ConnectionList
    ├─ Enters select() event loop
    └─ Broadcasts received messages to other peers
```

**Code Flow** [Main.py::run_battle]:
```python
# 1. Create bridge
net_bridge = NetworkBridgeV2(host="127.0.0.1", port=9001, local_player=0)

# 2. Connect
net_bridge.connect()                      # Opens TCP socket
net_bridge.client.start_receiver_thread() # Background thread receives messages

# 3. Send initial greeting
client.send_message("HELLO|python|player0")  # Newline-delimited

# 4. Game loop
while t < max_ticks:
    net_bridge.integrate_network(engine)  # Process incoming messages
    engine.step(dt, generals)             # Local game step
    net_bridge.publish_local_actions()    # Send updates
```

### 2.3 Relay Server Operation [tcp_relay_server.c]

**Core Loop** [server.c::run_event_loop]:
```c
while (1) {
    fd_set read_set;
    // Monitor listening socket + all peer sockets
    FD_SET(listen_sock, &read_set);
    for (size_t i = 0; i < connections->count; i++)
        FD_SET(connections->items[i].socket, &read_set);
    
    select(FD_SETSIZE, &read_set, NULL, NULL, NULL);
    
    // Accept new connections
    if (FD_ISSET(listen_sock, &read_set))
        accept_new_connection(listen_sock, connections);
    
    // Receive and relay messages
    for (size_t i = 0; i < connections->count; i++) {
        if (FD_ISSET(connections->items[i].socket, &read_set)) {
            recv(socket, recv_buf, RECV_CHUNK, 0);
            broadcast_message(connections, sender_index, recv_buf, len);
        }
    }
}
```

**Key Function** [connection.c::broadcast_message]:
```c
void broadcast_message(ConnectionList *list, size_t sender_index, 
                       const char *line, int line_len) {
    for (size_t i = 0; i < list->count; i++) {
        if (i == sender_index) continue;  // Don't echo to sender
        
        Connection *peer = &list->items[i];
        send_all(peer->socket, line, line_len);  // Forward to other peers
    }
}
```

### 2.4 Message Reception [p2p_client.py]

**Background Receiver Thread**:
```python
def receive_messages(self) -> None:
    """Continuously receive messages and enqueue complete lines."""
    buffer = ""
    while not self._stop_event.is_set():
        data = self.sock.recv(4096)
        if not data:
            break
        
        buffer += data.decode("utf-8", errors="replace")
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            if line:
                self.incoming_queue.put(line)  # Thread-safe queue
```

**Main Thread Polling**:
```python
def integrate_network(self, engine):
    # Process one tick of network messages
    while True:
        msg = self.client.try_get_message()
        if msg is None:
            break
        self.integrator.process_incoming_message(msg)  # Handle each message
```

---

## 3. Network Message Protocol

### 3.1 Protocol Overview

**Format**: Pipe-delimited text, newline-terminated

All messages follow: `MESSAGE_TYPE|arg1|arg2|...` + `\n`

Example:
```
MOVE|42|10.50|20.75
ATTACK|42|99
REQUEST_OWNERSHIP|42
GRANT_OWNERSHIP|42|10.50|20.75|45.0|1|-1
STATE_HASH|a1b2c3d4e5f6789
PLAYER_JOINED|1
```

### 3.2 Defined Message Types

#### Game Action Messages

| Message | Direction | Args | Purpose |
|---------|-----------|------|---------|
| `MOVE\|unit_id\|x\|y` | Broadcast | unit_id, x, y | Remote unit movement |
| `ATTACK\|unit_id\|target_id` | Broadcast | unit_id, target_id | Unit attacks target |
| `STATE\|unit_id\|x\|y\|hp\|alive\|target_id` | Broadcast | Full unit state | Complete state update |

#### Ownership Messages

| Message | Direction | Args | Purpose |
|---------|-----------|------|---------|
| `REQUEST_OWNERSHIP\|unit_id` | To owner | unit_id | Request ownership transfer |
| `GRANT_OWNERSHIP\|unit_id\|x\|y\|hp\|alive\|target_id` | To requester | unit_id, state | Grant ownership + state snapshot |

#### Synchronization Messages

| Message | Direction | Args | Purpose |
|---------|-----------|------|---------|
| `PLAYER_JOINED\|player_id` | Broadcast | player_id | Announce new player |
| `REQUEST_FULL_STATE\|player_id` | To remote | player_id | Request full game state |
| `UNIT\|unit_id\|player\|x\|y\|hp\|target_id` | Unicast reply | Full unit data | Individual unit in sync |
| `FULL_STATE_SYNC\|end` | Unicast reply | End marker | State sync complete |
| `STATE_HASH\|hash` | Broadcast | MD5 hash | Coherence verification |

#### Control Messages

| Message | Direction | Args | Purpose |
|---------|-----------|------|---------|
| `HELLO\|component\|label` | On connect | component, label | Identify connecting client |

### 3.3 Protocol Grammar (BNF)

```bnf
message         := message_type "|" args "\n"

action_msg      := "MOVE" "|" unit_id "|" float "|" float
                 | "ATTACK" "|" unit_id "|" target_id
                 | "STATE" "|" unit_id "|" float "|" float "|" float "|" alive "|" target_id_or_minus1

ownership_msg   := "REQUEST_OWNERSHIP" "|" unit_id
                 | "GRANT_OWNERSHIP" "|" unit_id "|" float "|" float "|" float "|" alive "|" target_id_or_minus1

sync_msg        := "PLAYER_JOINED" "|" player_id
                 | "REQUEST_FULL_STATE" "|" player_id
                 | "UNIT" "|" unit_id "|" player_id "|" float "|" float "|" float "|" target_id_or_minus1
                 | "FULL_STATE_SYNC" "|" "end"
                 | "STATE_HASH" "|" hex_string

unit_id         := integer
target_id       := integer
target_id_or_minus1 := integer  (use -1 for no target)
alive           := "0" | "1"
player_id       := integer
hex_string      := [0-9a-f]+
float           := floating point number, formatted to 3 decimal places
```

### 3.4 Message Processing Flow

[network_integration.py::process_incoming_message]:

```python
def process_incoming_message(self, msg: str) -> None:
    """Route incoming message to appropriate handler."""
    parts = msg.strip().split("|")
    msg_type = parts[0].upper()
    
    # New player arrival
    if msg_type == "PLAYER_JOINED":
        self._handle_player_joined(parts)
    
    # Ownership workflow
    elif msg_type == "REQUEST_OWNERSHIP":
        self._handle_request_ownership(parts)  # Phase 2
    elif msg_type == "GRANT_OWNERSHIP":
        self._handle_grant_ownership(parts)    # Phase 3
    
    # State sync
    elif msg_type == "PLAYER_JOINED":
        self._handle_player_joined(parts)
    elif msg_type == "REQUEST_FULL_STATE":
        self._handle_request_full_state(parts)
    elif msg_type == "UNIT":
        self._handle_synced_unit(parts)
    elif msg_type == "FULL_STATE_SYNC":
        self._handle_full_state_sync(parts)
    
    # Coherence check
    elif msg_type == "STATE_HASH":
        self._handle_state_hash(parts)
    
    # State updates (from remote owners)
    elif msg_type == "STATE":
        self._handle_state(parts)
    elif msg_type == "MOVE":
        self._handle_move(parts)
    elif msg_type == "ATTACK":
        self._handle_attack(parts)
```

---

## 4. Network Ownership System

### 4.1 Ownership Concept

**Every unit has exactly ONE owner** (a player_id):
- Unit spawned by Player X → Player X owns it initially
- Ownership can be transferred to another player via explicit protocol
- Only the owner can modify the unit's state locally
- Remote players see the unit but cannot modify it directly

**Storage** [Engine.py::SimpleEngine]:
```python
unit_ownership: Dict[int, int]  # unit_id → player_id (owner)
```

### 4.2 Ownership Tracker Implementation [network_integration.py::OwnershipTracker]

```python
@dataclass
class OwnershipTracker:
    local_player: int
    entity_owner: Dict[int, int]           # unit_id → owner_id
    ownership_state: Dict[int, OwnershipState]  # UNOWNED | REQUESTING | OWNED
    granted_state: Dict[int, Dict]         # unit_id → state snapshot
    
    def can_modify_local(self, unit_id: int) -> bool:
        """True if local_player owns this unit."""
        return self.entity_owner.get(unit_id) == self.local_player
    
    def request_ownership(self, unit_id: int, client: P2PClient) -> None:
        """Phase 1: Request ownership from current owner."""
        self.ownership_state[unit_id] = OwnershipState.REQUESTING
        client.send_message(f"REQUEST_OWNERSHIP|{unit_id}")
    
    def grant_ownership(self, unit_id: int, new_owner: int, 
                        unit_state: Optional[Dict] = None) -> None:
        """Phase 3: Grant ownership with state snapshot."""
        self.entity_owner[unit_id] = new_owner
        self.ownership_state[unit_id] = OwnershipState.OWNED
        if unit_state:
            self.granted_state[unit_id] = unit_state
```

### 4.3 Ownership Workflow

**5-Phase Protocol**:

```
Phase 1: REQUEST
├─ Local player wants to modify unit owned by Remote player
├─ Local sends: REQUEST_OWNERSHIP|unit_id
└─ Local state: OwnershipState.REQUESTING

Phase 2: VERIFY (remote side)
├─ Remote receives REQUEST_OWNERSHIP
├─ Remote checks unit owner: entity_owner[unit_id] == remote_player_id
├─ Remote verifies action is valid (implicit - always grants if owner)
└─ Remote prepares to send grant

Phase 3: GRANT (remote → local)
├─ Remote sends: GRANT_OWNERSHIP|unit_id|x|y|hp|alive|target_id
├─ Remote attaches current unit state snapshot
└─ Local receives and updates OwnershipState.OWNED

Phase 4: EXECUTE (local side)
├─ Local can now modify unit
├─ Local verifies action is still valid (position, target alive, etc.)
├─ Local performs action (MOVE/ATTACK)
└─ Local updates unit in local engine

Phase 5: PUBLISH (local → all)
├─ Local broadcasts result: MOVE|unit_id|new_x|new_y or ATTACK|unit_id|target
├─ All remote players receive and apply (IF they don't own it)
└─ State converges
```

**Code** [network_integration.py]:

```python
# Phase 1 & 4: REQUEST + EXECUTE (local)
def send_action_with_ownership(self, action: Dict) -> bool:
    unit_id = action.get("unit_id")
    
    if self.ownership.is_unowned(unit_id):
        # Phase 1: Request
        self.ownership.request_ownership(unit_id, self.client)
        return False
    
    if not self.ownership.can_modify_local(unit_id):
        # Already owned by someone else
        return False
    
    # Phase 4: Verify and execute
    can_exec, reason = self.can_execute_action(action)
    if not can_exec:
        return False
    
    # Phase 5: Publish result
    msg = self._action_to_protocol(action)
    if msg:
        self.client.send_message(msg)
    return True


# Phase 2 & 3: VERIFY + GRANT (remote side)
def _handle_request_ownership(self, parts: list) -> None:
    """Phase 2: Remote player requests ownership."""
    unit_id = int(parts[1])
    unit = self.engine.units_by_id.get(unit_id)
    
    # Check if we own it
    owner = self.ownership.entity_owner.get(unit_id)
    if owner != self.local_player:
        return  # We don't own it, ignore
    
    # Phase 3: Grant with state snapshot
    msg = f"GRANT_OWNERSHIP|{unit_id}|{unit.x:.3f}|{unit.y:.3f}|{unit.hp:.3f}|{1 if unit.alive else 0}|{unit.target_id if unit.target_id else -1}"
    self.client.send_message(msg)

def _handle_grant_ownership(self, parts: list) -> None:
    """Phase 3: Receive ownership grant."""
    unit_id = int(parts[1])
    # Parse state
    state = {
        "x": float(parts[2]),
        "y": float(parts[3]),
        # ... etc
    }
    self.ownership.grant_ownership(unit_id, self.local_player, state)
```

### 4.4 Ownership Enforcement

**Local Modifications** [network_integration.py::can_execute_action]:
```python
def can_execute_action(self, action: Dict) -> Tuple[bool, Optional[str]]:
    unit_id = action.get("unit_id")
    unit = self.engine.units_by_id.get(unit_id)
    
    # OWNERSHIP CHECK
    if not self.ownership.can_modify_local(unit_id):
        return False, f"Unit {unit_id} owned by player {self.ownership.entity_owner.get(unit_id)}"
    
    # ACTION VALIDATION
    if action_type == "MOVE":
        if not (0 <= target_x < self.engine.w and 0 <= target_y < self.engine.h):
            return False, f"Target outside map bounds"
    
    if action_type == "ATTACK":
        dist = unit.distance_to(target)
        if dist > unit.range + 5:
            return False, f"Target too far"
    
    return True, None
```

**Remote Updates** [network_integration.py::_handle_state]:
```python
def _handle_state(self, parts: list) -> None:
    """Apply remote state update."""
    unit_id = int(parts[1])
    
    # OWNERSHIP CHECK: Only apply if we DON'T own it
    if self.ownership.can_modify_local(unit_id):
        return  # We own it - ignore remote update (we're authoritative)
    
    # Apply remote state (remote player is authoritative for their unit)
    unit.x = float(parts[2])
    unit.y = float(parts[3])
    unit.hp = float(parts[4])
    # ...
```

---

## 5. State Synchronization

### 5.1 Synchronization Mechanisms

**Three types of state updates**:

#### 1. **Continuous Incremental Updates** (During gameplay)
- Player 1 moves unit 42 locally
- Player 1 broadcasts: `MOVE|42|15.5|20.3`
- Relay forwards to all others
- Players 2, 3 receive and update their local engine copy of unit 42
- If unit 42 is owned by Player 1, they are authoritative

#### 2. **On-Demand Full State Sync** (New player joins)
```python
def integrate_network(self, engine):
    if not self._join_announced:
        self.integrator.announce_join()                    # Broadcast: PLAYER_JOINED|0
        self.integrator.request_full_state_from_remote()   # Send: REQUEST_FULL_STATE|0
        self._join_announced = True
    
    # ... receive multiple UNIT messages ...
```

Remote player receives `REQUEST_FULL_STATE|0` and responds:
```python
def _handle_request_full_state(self, parts):
    self.publish_full_state()  # Send all alive units as UNIT messages

def publish_full_state(self):
    for unit in self.engine.units:
        if unit.alive:
            msg = f"UNIT|{unit.id}|{unit.player}|{unit.x:.3f}|{unit.y:.3f}|{unit.hp:.1f}|{unit.target_id if unit.target_id else -1}"
            self.client.send_message(msg)
    self.client.send_message("FULL_STATE_SYNC|end")
```

#### 3. **Periodic Coherence Verification** (State hash exchange)
```python
self._coherence_check_interval = 30  # Every 30 ticks

if self._tick_counter % self._coherence_check_interval == 0:
    self.integrator.publish_state_hash()
```

### 5.2 Coherence Validator [network_integration.py::CoherenceValidator]

**State Hash Computation**:
```python
def compute_state_hash(self, engine) -> str:
    """Deterministic hash of game state."""
    state_items = []
    for unit in sorted(engine.units, key=lambda u: u.id):
        if unit.alive:
            item = f"{unit.id}:{unit.player}:{unit.x:.2f}:{unit.y:.2f}:{unit.hp:.1f}:{unit.target_id}"
            state_items.append(item)
    
    state_str = "|".join(state_items)
    return hashlib.md5(state_str.encode()).hexdigest()
```

**Example Hash Sequence**:
```
Player 1 tick 30: PLAYER_JOINED|0
Player 1 tick 60: STATE_HASH|a1b2c3d4e5f6789012345678901234ab
Player 2 receives: STATE_HASH|a1b2c3d4e5f6789012345678901234ab
  → Computes local hash
  → If match: "✓ State coherence verified"
  → If mismatch: "✗ STATE DIVERGENCE: local=xxx vs remote=yyy"
```

### 5.3 Authority Model

**Per-Unit Authority**:
- Player 1 owns unit 42 → Player 1 is authoritative for unit 42's state
- Player 1 moves unit 42 locally → computes new position
- Player 1 broadcasts: `MOVE|42|new_x|new_y`
- Player 2 receives → applies update (doesn't overwrite its own computation since it doesn't own unit 42)

**Code Enforcement** [network_integration.py]:
```python
def _handle_move(self, parts):
    """Process remote move."""
    unit_id = int(parts[1])
    x, y = float(parts[2]), float(parts[3])
    
    unit = self.engine.units_by_id.get(unit_id)
    if not unit:
        return
    
    # AUTHORITY CHECK: Only apply if we DON'T own it
    if self.ownership.can_modify_local(unit_id):
        return  # We own it - we're authoritative, ignore remote
    
    # Apply remote state
    unit.x = x
    unit.y = y
```

### 5.4 Initial State Placement [network_integration.py::PlayerJoinHandler]

When new player joins and receives full state:
```python
def _handle_synced_unit(self, parts):
    """Process unit from full state sync."""
    unit_id, player, x, y, hp, target_id = parse(parts)
    
    # If unit already exists locally, keep it
    if unit_id in self.engine.units_by_id:
        return
    
    # Resolve placement conflicts (avoid overlaps)
    resolved_x, resolved_y = self.join_handler.handle_unit_placement_conflict(
        x, y,
        self.engine.units,
        collision_radius=2.0
    )
    
    # Spawn unit
    new_unit = self.engine.spawn_unit(player, resolved_x, resolved_y, hp=hp, target_id=target_id)
    self.ownership.grant_ownership(unit_id, player)
```

---

## 6. Missing/Incomplete Features

### 6.1 Architectural Gaps

| Issue | Impact | Severity |
|-------|--------|----------|
| No conflict resolution for concurrent ownership requests | Two players may try to gain ownership simultaneously; unclear who wins | HIGH |
| No rollback mechanism | If invalid action is executed before ownership verification completes, no way to undo | MEDIUM |
| No deterministic ordering | Messages may arrive out-of-order; no total ordering guaranteed | MEDIUM |
| No action queuing | If action can't execute (waiting for ownership), it's silently dropped | MEDIUM |
| No message ACK/NAK protocol | No way to know if message was received/processed by remote | LOW |
| No heartbeat/keepalive | Disconnects may not be detected immediately | LOW |

### 6.2 Unused Code

**network_engine/ directory**:
- Contains more elaborate P2P networking code with peer-to-peer connections
- Implements IPC (inter-process communication) queue
- Not integrated with main game
- `peer.c` and `protocol.c` are empty stubs
- Appears to be experimental/alternative implementation

**Status**: Recommend either:
1. Delete if not needed (cleanup)
2. Integrate and use instead of relay server (true P2P)
3. Keep as documentation of alternative approach

### 6.3 Potential Enhancements

**Short-term**:
- Add conflict resolution policy (first-come-first-served or consensus)
- Implement message acknowledgments for reliability
- Add deterministic ordering for concurrent actions

**Medium-term**:
- Implement rollback mechanism for bad ownership transitions
- Add heartbeat/keepalive for connection monitoring
- Implement action queue with replay capability

**Long-term**:
- Consider migrating from relay server to true P2P networking
- Implement Byzantine-fault-tolerant consensus for critical state
- Add data compression for large state updates

---

## 7. Summary Table

| Aspect | Implementation |
|--------|-----------------|
| **Architecture** | Relay-based distributed game (hybrid P2P) |
| **Relay Server** | TCP relay [tcp_relay_server.c] — stateless forwarding only |
| **Game Engines** | Per-player instances [Main.py] — distributed authority |
| **Inter-Process Communication** | TCP sockets with text protocol (newline-delimited, pipe-separated fields) |
| **IPC Mechanism** | No direct IPC; message-based async communication |
| **Network Protocol** | Custom text-based protocol (15+ message types defined) |
| **Message Format** | `TYPE\|arg1\|arg2\|...\n` (pipe-delimited, newline-terminated) |
| **Ownership System** | YES — Per-unit ownership with 5-phase protocol (REQUEST→VERIFY→GRANT→EXECUTE→PUBLISH) |
| **Authority Model** | Per-unit (owner is authoritative); remote units are read-only for non-owners |
| **State Sync** | Incremental updates + on-demand full sync + periodic coherence hashing (MD5) |
| **Coherence Verification** | State hash comparison via `STATE_HASH\|hash` messages |
| **Player Join Workflow** | PLAYER_JOINED → REQUEST_FULL_STATE → receive UNIT messages → FULL_STATE_SYNC |
| **Conflict Resolution** | None (concurrent access attempts not explicitly handled) |
| **Rollback/Undo** | None |
| **Message Ordering** | No guarantees (potential out-of-order delivery) |
| **Completeness** | ~85% (core loop works; missing conflict resolution and error recovery) |

---

## Conclusion

The P2P-MedievAI project successfully implements a **relay-based distributed game** with **per-unit ownership enforcement**. While not "true" P2P (uses centralized relay), it effectively distributes game logic across player instances using a well-designed ownership workflow and message protocol. The architecture is functional for turn-based or slow-paced games, but would benefit from:

1. **Conflict resolution policies** for concurrent access attempts
2. **Deterministic ordering** for actions arriving out-of-sequence
3. **Error recovery mechanisms** for handling invalid state transitions

The codebase is generally well-structured, with clear separation between relay logic (C) and game logic (Python), though some experimental code (`network_engine/`) could be cleaned up or better integrated.
