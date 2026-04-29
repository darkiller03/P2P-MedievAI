#ifndef CONFLICT_RESOLUTION_H
#define CONFLICT_RESOLUTION_H

#include <stdint.h>
#include <stdbool.h>
#include <time.h>

/**
 * Lamport Clock for distributed causal ordering
 * 
 * Used to:
 * 1. Detect concurrent events
 * 2. Provide total ordering for conflict resolution
 * 3. Detect causality violations
 */

typedef uint64_t LamportClock;

typedef struct {
    LamportClock local_clock;      // This node's local clock
    const char *player_id;         // This node's player ID (for tiebreaker)
} ClockManager;

/**
 * Initialize clock manager
 * player_id: unique identifier for this player (e.g., "player_a")
 */
ClockManager* clock_manager_new(const char *player_id);

/**
 * Free clock manager
 */
void clock_manager_free(ClockManager *cm);

/**
 * Increment local clock (call before local action)
 * Returns new clock value
 */
LamportClock clock_increment(ClockManager *cm);

/**
 * Update clock based on received message clock
 * Call after receiving a message with a clock value
 * Returns new local clock value
 */
LamportClock clock_update(ClockManager *cm, LamportClock received_clock);

/**
 * Get current local clock without incrementing
 */
LamportClock clock_get_current(const ClockManager *cm);

/**
 * Conflict resolution for concurrent ownership requests
 * 
 * Returns:
 *   > 0: This player wins (grant ownership to this player)
 *   < 0: Other player wins (deny ownership to this player)
 *   0:   Tie (should not happen with proper implementation)
 * 
 * Rules (in order):
 * 1. Lower clock wins (earlier causality)
 * 2. Same clock: player_id alphabetically wins
 */
int resolve_conflict(
    LamportClock this_clock, const char *this_player_id,
    LamportClock other_clock, const char *other_player_id
);

/**
 * Detect causality violation
 * 
 * If received_clock << local_clock in a suspiciously old way,
 * might indicate message reordering or lost updates
 * 
 * Returns:
 *   true if causality looks violated (message from far past)
 *   false if message is reasonable
 */
bool causality_violated(LamportClock local_clock, LamportClock received_clock);

#endif // CONFLICT_RESOLUTION_H
