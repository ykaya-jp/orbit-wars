## [MD]
# Sun-Signal Alliance Protocol (SSAP) — Draft Spec

A lightweight in-game communication system for Orbit Wars using ship sacrifices to the sun. Total cost for a full alliance negotiation: **6–8 ships**.

---

## How it works

Ships sent into the sun are observable by all players. By sending them in deliberate bursts with short pauses between, we can encode messages. The **number of ships per burst** carries meaning; the **pause between bursts** separates symbols.

A "burst" = ships dispatched to the sun within the same turn.
A "pause" = one turn with no sun-dispatch from that player.

---

## Signal dictionary

| Signal | Pattern | Meaning |
|---|---|---|
| **Propose** | 1 ship → pause → 2 ships | "I want to form an alliance with you" |
| **Target** | N ships (immediately after propose) | "Our target is player N" |
| **Accept** | 2 ships simultaneously | "Alliance accepted" |
| **Decline** | 1 ship only | "Not interested" |
| **Strike** | 3 ships simultaneously | "I'm attacking the target now — move with me" |

---

## Full exchange example (4-player game)

**Turn T** — Player A sends 1 ship to sun, waits one turn.
**Turn T+1** — Player A sends 2 ships to sun. *(Propose signal complete.)*
**Turn T+2** — Player A sends 3 ships to sun. *(Target burst: "attack player 3".)*
**Turn T+3 to T+5** — Player B has 3 turns to reply before the proposal expires.
**Turn T+4** — Player B sends 2 ships to sun simultaneously. *(Accept. Alliance is live.)*
**Turn T+N** — Either ally sends 3 ships to sun. *(Strike signal — coordinated attack begins.)*

Total ships burned: **6 by proposer, 2 by acceptor.**

---

## Rules

**Simultaneity:** Ships dispatched in the same turn count as one burst. Ships dispatched one turn apart are two separate symbols with a pause between them.

**Expiry:** A proposal with no reply within 3 turns is considered declined. Prevents indefinite ambiguity.

**Noise immunity:** Single stray ships are common in normal play. The propose pattern (1-pause-2) is distinct enough not to be confused with combat losses.

**Termination:** No explicit break signal. Attacking your ally's planet terminates the alliance. The protocol has no appeal mechanism — trust accordingly.

**Observability:** All players can read these signals. Keep the negotiation window short and strike quickly after the accept to limit the warning you give to the target.

---

## Cost summary

| Action | Ships lost |
|---|---|
| Full propose + target | 6 |
| Accept | 2 |
| Decline | 1 |
| Strike signal | 3 |

---

*Open to feedback — particularly on whether the propose pattern is distinct enough, and whether we need additional signals (e.g. "break alliance" or "request reinforcement").*

---

## Python helper — drop this into your agent

The helper tracks signal state across turns using a small dict. Call `ssap_observe()` each turn to decode incoming signals, and `ssap_act()` to get any sun-dispatch actions your agent should append to its normal moves.

```python
# ── Sun-Signal Alliance Protocol (SSAP) helper ──────────────────────────────
# State persists across turns via a mutable dict — initialise once outside
# your agent function and pass it in each call.
#
# ssap_state = ssap_init()
#
# Each turn:
#   signals  = ssap_observe(obs, ssap_state, my_player_id)
#   actions  = ssap_act(ssap_state, obs, my_player_id)
#   # append actions to your normal dispatch list

SUN_ID = -1   # sentinel for the sun target; adjust if your env uses a real ID

def ssap_init():
    """Return a fresh SSAP state dict. Create once, reuse every turn."""
    return {
        "turn": 0,
        # outbound queue: list of (turn_to_send, n_ships) tuples
        "out_queue": [],
        # inbound tracking: {player_id: [(turn, n_ships), ...]} rolling window
        "in_bursts": {},
        # active alliance: None or {"ally": player_id, "target": player_id, "since": turn}
        "alliance": None,
        # proposal we sent, waiting for reply
        "pending_out": None,   # {"to": player_id, "target": player_id, "sent_turn": turn}
        # proposal we received, waiting for our decision
        "pending_in": None,    # {"from": player_id, "target": player_id, "recv_turn": turn}
    }


# ── Observation: read sun-bound fleets sent by other players ─────────────────

def _sun_bursts_this_turn(obs, my_player_id, turn):
    """
    Return {player_id: n_ships} for every player (not us) who sent ships
    toward the sun this turn.

    Assumes obs.fleets is a list of fleet objects with:
        .owner          (int player id)
        .target_id      (int; SUN_ID for sun-bound fleets)
        .ships          (int)
        .turns_remaining (int; 1 means arrives next turn — adjust if needed)
    """
    bursts = {}
    for fleet in obs.fleets:
        if fleet.owner == my_player_id:
            continue
        if fleet.target_id != SUN_ID:
            continue
        # count fleets dispatched THIS turn (turns_remaining == travel distance;
        # for the sun assume 1 turn travel — tweak if your env differs)
        if fleet.turns_remaining == 1:
            bursts[fleet.owner] = bursts.get(fleet.owner, 0) + fleet.ships
    return bursts


def ssap_observe(obs, state, my_player_id):
    """
    Call every turn BEFORE ssap_act. Updates state with incoming signals.
    Returns a list of decoded signal dicts:
        {"type": "propose"|"accept"|"decline"|"strike"|"target",
         "from": player_id, "target": player_id or None}
    """
    turn = state["turn"]
    bursts = _sun_bursts_this_turn(obs, my_player_id, turn)
    signals = []

    for pid, n in bursts.items():
        history = state["in_bursts"].setdefault(pid, [])
        history.append((turn, n))
        # keep only last 4 turns
        state["in_bursts"][pid] = [b for b in history if b[0] >= turn - 3]

    # decode per-player burst history
    PROPOSAL_EXPIRY = 3
    for pid, history in state["in_bursts"].items():
        if len(history) < 1:
            continue
        last_turn, last_n = history[-1]
        if last_turn != turn:
            continue   # nothing new from this player this turn

        # ── Strike: 3 ships in one burst ─────────────────────────────────────
        if last_n == 3:
            signals.append({"type": "strike", "from": pid, "target": None})
            continue

        # ── Accept: 2 ships, and we have a pending_out to this player ────────
        if last_n == 2 and state["pending_out"] and state["pending_out"]["to"] == pid:
            po = state["pending_out"]
            signals.append({"type": "accept", "from": pid, "target": po["target"]})
            state["alliance"] = {"ally": pid, "target": po["target"], "since": turn}
            state["pending_out"] = None
            continue

        # ── Decline: 1 ship, and we have a pending_out to this player ────────
        if last_n == 1 and state["pending_out"] and state["pending_out"]["to"] == pid:
            signals.append({"type": "decline", "from": pid, "target": None})
            state["pending_out"] = None
            continue

        # ── Propose: 1 ship last turn, 2 ships this turn (pause pattern) ─────
        if last_n == 2 and len(history) >= 2:
            prev_turn, prev_n = history[-2]
            if prev_n == 1 and last_turn - prev_turn == 1:
                # next burst (target) may come next turn — mark pending_in
                state["pending_in"] = {"from": pid, "target": None, "recv_turn": turn}
                signals.append({"type": "propose", "from": pid, "target": None})
                continue

        # ── Target burst: N ships, and we have a pending_in from this player ─
        if state["pending_in"] and state["pending_in"]["from"] == pid:
            pi = state["pending_in"]
            if turn - pi["recv_turn"] <= 2 and last_n not in (1, 2, 3):
                # N ships = player N (target id)
                pi["target"] = last_n
                signals.append({"type": "target", "from": pid, "target": last_n})
            elif last_n in range(1, 5) and state["pending_in"]["target"] is None:
                # target encoded as 1-4 ships
                pi["target"] = last_n
                signals.append({"type": "target", "from": pid, "target": last_n})

        # expire stale pending_in
        if state["pending_in"] and turn - state["pending_in"]["recv_turn"] > PROPOSAL_EXPIRY:
            state["pending_in"] = None

    # expire stale pending_out
    if state["pending_out"] and turn - state["pending_out"]["sent_turn"] > PROPOSAL_EXPIRY:
        state["pending_out"] = None

    return signals


# ── Action: generate sun-dispatch actions from the out_queue ─────────────────

def ssap_act(state, obs, my_player_id):
    """
    Returns a list of dispatch dicts to send ships to the sun this turn.
    Append these to your agent's normal action list.
    Format: [{"source": planet_id, "target": SUN_ID, "ships": n}, ...]
    """
    turn = state["turn"]
    due = [item for item in state["out_queue"] if item[0] == turn]
    state["out_queue"] = [item for item in state["out_queue"] if item[0] != turn]

    actions = []
    my_planets = [p for p in obs.planets if p.owner == my_player_id]
    if not my_planets:
        return actions

    # pick the source planet with the most ships (minimise strategic impact)
    source = max(my_planets, key=lambda p: p.ships)

    for _, n_ships in due:
        if source.ships <= n_ships + 10:   # safety: don't denude the planet
            continue
        actions.append({"source": source.id, "target": SUN_ID, "ships": n_ships})
        source.ships -= n_ships   # track locally so multi-burst doesn't over-spend

    state["turn"] += 1
    return actions


# ── High-level helpers: propose, accept, decline, strike ─────────────────────

def ssap_propose(state, ally_player_id, target_player_id):
    """
    Queue a full proposal: propose pattern + target burst.
    Call this once when you decide to initiate an alliance.
    """
    turn = state["turn"]
    state["out_queue"].append((turn,     1))              # burst 1: 1 ship
    state["out_queue"].append((turn + 1, 2))              # burst 2: 2 ships (after pause)
    state["out_queue"].append((turn + 2, target_player_id))  # target burst
    state["pending_out"] = {
        "to": ally_player_id,
        "target": target_player_id,
        "sent_turn": turn,
    }

def ssap_accept(state):
    """Queue an accept signal (2 ships this turn)."""
    state["out_queue"].append((state["turn"], 2))
    state["pending_in"] = None

def ssap_decline(state):
    """Queue a decline signal (1 ship this turn)."""
    state["out_queue"].append((state["turn"], 1))
    state["pending_in"] = None

def ssap_strike(state):
    """Queue a strike signal (3 ships this turn) — tells ally to attack now."""
    state["out_queue"].append((state["turn"], 3))


# ── Example integration skeleton ─────────────────────────────────────────────
#
# ssap_state = ssap_init()
#
# def agent(obs, config):
#     my_id = config.my_player_id
#
#     signals = ssap_observe(obs, ssap_state, my_id)
#     for sig in signals:
#         if sig["type"] == "propose":
#             # simple policy: accept if we have no alliance yet and a target is named
#             if ssap_state["alliance"] is None and ssap_state["pending_in"]["target"]:
#                 ssap_accept(ssap_state)
#         elif sig["type"] == "strike" and ssap_state["alliance"]:
#             pass  # your attack logic against ssap_state["alliance"]["target"]
#
#     # initiate an alliance on turn 5 if we haven't already
#     if obs.turn == 5 and ssap_state["alliance"] is None and ssap_state["pending_out"] is None:
#         ssap_propose(ssap_state, ally_player_id=2, target_player_id=3)
#
#     sun_actions = ssap_act(ssap_state, obs, my_id)
#     normal_actions = your_normal_agent_logic(obs, config)
#     return normal_actions + sun_actions
```

## [CODE]
```python

```

## [MD]
