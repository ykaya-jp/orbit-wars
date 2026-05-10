# =============================================================================
# Orbit Wars - Kaggle Competition Agent
# Competition: https://www.kaggle.com/competitions/orbit-wars
#
# Strategy overview:
#   - Orbital intercept: iteratively solve for target planet's future position
#   - Threat assessment: track incoming enemy fleets per planet
#   - Garrison management: keep ships proportional to threat + production value
#   - Target priority scoring: production / (distance * enemy_ships + 1)
#   - Sun avoidance: deflect fleet path if it crosses sun exclusion zone
#   - Multi-planet coordination: avoid over-committing one planet to a target
#   - Retreat logic: evacuate planets that can't be saved
# =============================================================================

import math
import itertools
from typing import List, Tuple, Optional, Dict

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SUN_X, SUN_Y = 50.0, 50.0
SUN_RADIUS = 5.0          # fleets crossing inside this radius are destroyed
MAX_TURNS = 500
FLEET_SPEED_BASE = 1.0
FLEET_SPEED_MAX = 6.0
FLEET_SPEED_LOG_BASE = 1000.0
FLEET_SPEED_EXP = 1.5

# Garrison fraction — keep this share of ships as local defence
GARRISON_FRACTION = 0.35
# Minimum garrison ships regardless of threat
MIN_GARRISON = 3
# Maximum intercept iterations for orbital prediction
MAX_INTERCEPT_ITERS = 10
INTERCEPT_CONVERGE_TOL = 0.5   # pixels — stop iterating when delta < this


# ---------------------------------------------------------------------------
# Physics helpers
# ---------------------------------------------------------------------------

def fleet_speed(num_ships: int) -> float:
    """Return fleet travel speed given ship count."""
    ships = max(num_ships, 1)
    ratio = math.log(ships) / math.log(FLEET_SPEED_LOG_BASE)
    return FLEET_SPEED_BASE + (FLEET_SPEED_MAX - FLEET_SPEED_BASE) * (ratio ** FLEET_SPEED_EXP)


def distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def angle_to(x1: float, y1: float, x2: float, y2: float) -> float:
    """Angle in radians from (x1,y1) to (x2,y2)."""
    return math.atan2(y2 - y1, x2 - x1)


def travel_time(dist: float, num_ships: int) -> float:
    """Turns needed to travel dist with a fleet of num_ships."""
    spd = fleet_speed(num_ships)
    if spd <= 0:
        return float('inf')
    return dist / spd


def planet_future_pos(px: float, py: float, base_angle: float,
                      radius: float, omega: float, turns: float,
                      is_comet: bool) -> Tuple[float, float]:
    """
    Return planet (x, y) after `turns` turns.
    Planets orbit the sun at a fixed angular velocity omega (rad/turn).
    Comet 'planets' are treated as stationary for targeting purposes
    (they move unpredictably; just aim at current position).
    """
    if is_comet or omega == 0.0:
        return px, py
    # Current angle of this planet around the sun
    new_angle = base_angle + omega * turns
    return (SUN_X + radius * math.cos(new_angle),
            SUN_Y + radius * math.sin(new_angle))


def orbital_angle(px: float, py: float) -> float:
    """Return current orbital angle of a planet around the sun."""
    return math.atan2(py - SUN_Y, px - SUN_X)


def orbital_radius(px: float, py: float) -> float:
    """Return orbital radius of a planet around the sun."""
    return distance(px, py, SUN_X, SUN_Y)


def intercept_angle(src_x: float, src_y: float,
                    tgt_x: float, tgt_y: float,
                    tgt_base_angle: float, tgt_orbital_radius: float,
                    omega: float, num_ships: int,
                    is_comet: bool) -> Tuple[float, float, float]:
    """
    Iteratively solve for the intercept point of a moving (orbiting) target.

    Returns (fire_angle_radians, intercept_x, intercept_y).
    Uses Newton-style fixed-point iteration:
        1. Estimate travel time to current target position.
        2. Advance planet position by that time.
        3. Recompute travel time to new position.
        4. Repeat until convergence.
    """
    ix, iy = tgt_x, tgt_y  # initial guess: current position

    for _ in range(MAX_INTERCEPT_ITERS):
        dist = distance(src_x, src_y, ix, iy)
        t = travel_time(dist, num_ships)
        new_ix, new_iy = planet_future_pos(
            tgt_x, tgt_y, tgt_base_angle, tgt_orbital_radius, omega, t, is_comet)
        if distance(ix, iy, new_ix, new_iy) < INTERCEPT_CONVERGE_TOL:
            ix, iy = new_ix, new_iy
            break
        ix, iy = new_ix, new_iy

    return angle_to(src_x, src_y, ix, iy), ix, iy


# ---------------------------------------------------------------------------
# Sun avoidance
# ---------------------------------------------------------------------------

def path_crosses_sun(x1: float, y1: float, x2: float, y2: float,
                     sun_x: float = SUN_X, sun_y: float = SUN_Y,
                     sun_r: float = SUN_RADIUS) -> bool:
    """
    Return True if the straight-line segment from (x1,y1) to (x2,y2)
    passes within sun_r of the sun centre.
    Uses point-to-segment distance formula.
    """
    dx, dy = x2 - x1, y2 - y1
    fx, fy = x1 - sun_x, y1 - sun_y
    a = dx * dx + dy * dy
    if a < 1e-9:
        return False
    b = 2 * (fx * dx + fy * dy)
    c = fx * fx + fy * fy - sun_r * sun_r
    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        return False
    t0 = (-b - math.sqrt(discriminant)) / (2 * a)
    t1 = (-b + math.sqrt(discriminant)) / (2 * a)
    return (t0 <= 1 and t1 >= 0)  # segment overlaps with chord inside sun


def safe_angle(src_x: float, src_y: float,
               tgt_x: float, tgt_y: float,
               raw_angle: float) -> float:
    """
    If the direct path crosses the sun, offset the fire angle by a small
    amount to skirt around the sun exclusion zone.
    Choose the deflection direction that adds the smallest total offset.
    """
    if not path_crosses_sun(src_x, src_y, tgt_x, tgt_y):
        return raw_angle

    # Try both clockwise and counter-clockwise offsets in increasing steps
    for delta in [0.15, 0.25, 0.40, 0.60, 0.80, 1.0]:
        for sign in (1, -1):
            angle = raw_angle + sign * delta
            ex = src_x + 200 * math.cos(angle)
            ey = src_y + 200 * math.sin(angle)
            if not path_crosses_sun(src_x, src_y, ex, ey):
                return angle
    # Fallback: return raw angle (should rarely happen)
    return raw_angle


# ---------------------------------------------------------------------------
# Observation parsing
# ---------------------------------------------------------------------------

class Planet:
    __slots__ = ('id', 'owner', 'x', 'y', 'radius', 'ships', 'production',
                 'orbital_angle', 'orbital_radius', 'is_comet')

    def __init__(self, row, comet_ids):
        self.id = int(row[0])
        self.owner = int(row[1])
        self.x = float(row[2])
        self.y = float(row[3])
        self.radius = float(row[4])
        self.ships = float(row[5])
        self.production = float(row[6])
        self.orbital_angle = orbital_angle(self.x, self.y)
        self.orbital_radius = orbital_radius(self.x, self.y)
        self.is_comet = self.id in comet_ids


class Fleet:
    __slots__ = ('id', 'owner', 'x', 'y', 'angle', 'from_planet_id', 'ships')

    def __init__(self, row):
        self.id = int(row[0])
        self.owner = int(row[1])
        self.x = float(row[2])
        self.y = float(row[3])
        self.angle = float(row[4])
        self.from_planet_id = int(row[5])
        self.ships = float(row[6])


def parse_obs(obs: dict):
    """Parse raw observation dict into lists of Planet and Fleet objects."""
    comet_ids = set(obs.get('comet_planet_ids', []))
    planets = [Planet(row, comet_ids) for row in obs.get('planets', [])]
    fleets = [Fleet(row) for row in obs.get('fleets', [])]
    player = int(obs.get('player', 0)) + 1   # obs uses 0-indexed; owners are 1-indexed
    omega = float(obs.get('angular_velocity', 0.0))
    return planets, fleets, player, omega


# ---------------------------------------------------------------------------
# Threat / support assessment
# ---------------------------------------------------------------------------

def compute_incoming(planets: List[Planet],
                     fleets: List[Fleet],
                     player: int) -> Dict[int, Dict[str, float]]:
    """
    For each planet, compute net incoming ships broken down by:
      'enemy'  — enemy fleet ships inbound (threat)
      'friend' — friendly fleet ships inbound (reinforcement)

    Returns dict keyed by planet_id.
    """
    incoming: Dict[int, Dict[str, float]] = {
        p.id: {'enemy': 0.0, 'friend': 0.0} for p in planets
    }
    planet_map = {p.id: p for p in planets}

    for f in fleets:
        # Find which planet this fleet is heading toward (nearest planet
        # in the direction the fleet is travelling that matches destination).
        # We approximate by finding the planet whose angle from fleet matches
        # the fleet's travel angle most closely — this is an approximation;
        # the simulation doesn't give us a destination directly.
        best_pid = _fleet_target_planet(f, planet_map)
        if best_pid is None:
            continue
        if f.owner == player:
            incoming[best_pid]['friend'] += f.ships
        else:
            incoming[best_pid]['enemy'] += f.ships

    return incoming


def _fleet_target_planet(fleet: Fleet,
                          planet_map: Dict[int, Planet]) -> Optional[int]:
    """
    Heuristic: the fleet is heading toward the planet that best aligns with
    its travel angle and is in front of it (not behind).
    """
    best_pid = None
    best_score = float('inf')
    fx, fy = fleet.x, fleet.y
    fa = fleet.angle

    for pid, p in planet_map.items():
        dx, dy = p.x - fx, p.y - fy
        dist = math.hypot(dx, dy)
        if dist < 0.1:
            continue
        a = math.atan2(dy, dx)
        angle_diff = abs(math.atan2(math.sin(a - fa), math.cos(a - fa)))
        if angle_diff > math.pi / 2:
            continue   # planet is behind the fleet
        score = angle_diff * 10 + dist * 0.01
        if score < best_score:
            best_score = score
            best_pid = pid

    return best_pid


# ---------------------------------------------------------------------------
# Garrison calculation
# ---------------------------------------------------------------------------

def required_garrison(planet: Planet, incoming: Dict[int, Dict[str, float]],
                      planets: List[Planet]) -> float:
    """
    Determine how many ships to keep at a planet for defence.
    Base = max(MIN_GARRISON, enemy_incoming * 1.2)
    Scaled by production value: higher-production planets merit more defence.
    """
    enemy_incoming = incoming[planet.id]['enemy']
    # Scale garrison with production value
    prod_factor = 1.0 + planet.production * 0.5
    garrison = max(MIN_GARRISON, enemy_incoming * 1.2) * prod_factor
    # Don't garrison more than we have
    return min(garrison, planet.ships * 0.8)


# ---------------------------------------------------------------------------
# Target prioritisation
# ---------------------------------------------------------------------------

def score_target(src: Planet, tgt: Planet, player: int,
                 omega: float, num_ships: int) -> float:
    """
    Score a potential attack target.
    Higher is better.

    Formula: production / (travel_turns * (tgt.ships + 1))
    Bonus for neutral planets (easier to capture).
    Penalty for friendly planets (no point attacking own).
    """
    if tgt.owner == player:
        return -1.0   # never attack own planet here

    _, ix, iy = intercept_angle(src.x, src.y,
                                tgt.x, tgt.y,
                                tgt.orbital_angle, tgt.orbital_radius,
                                omega, num_ships, tgt.is_comet)
    dist = distance(src.x, src.y, ix, iy)
    t = travel_time(dist, num_ships)
    if t <= 0:
        return 0.0

    enemy_ships = tgt.ships if tgt.owner != 0 else tgt.ships * 0.3
    score = (tgt.production + 1.0) / (t * (enemy_ships + 1.0))
    return score


# ---------------------------------------------------------------------------
# Retreat logic
# ---------------------------------------------------------------------------

def find_safe_retreat(planet: Planet, planets: List[Planet],
                      player: int) -> Optional[Planet]:
    """
    Find the nearest friendly planet to retreat to.
    Returns None if no friendly planet exists (other than self).
    """
    best = None
    best_dist = float('inf')
    for p in planets:
        if p.id == planet.id or p.owner != player:
            continue
        d = distance(planet.x, planet.y, p.x, p.y)
        if d < best_dist:
            best_dist = d
            best = p
    return best


# ---------------------------------------------------------------------------
# Core agent logic
# ---------------------------------------------------------------------------

def compute_moves(obs: dict) -> List[List]:
    """
    Main decision function. Returns a list of move commands:
        [[from_planet_id, direction_angle_radians, num_ships], ...]
    """
    planets, fleets, player, omega = parse_obs(obs)

    my_planets = [p for p in planets if p.owner == player]
    if not my_planets:
        return []

    planet_map = {p.id: p for p in planets}
    incoming = compute_incoming(planets, fleets, player)

    moves = []
    # Track how many ships are already being sent to each target this turn
    # to avoid massive over-commitment from multiple sources.
    ships_en_route: Dict[int, float] = {}

    for src in my_planets:
        # ------------------------------------------------------------------
        # Step 1: Determine how many ships are available to dispatch.
        # ------------------------------------------------------------------
        garrison = required_garrison(src, incoming, planets)
        available = src.ships - garrison

        # ------------------------------------------------------------------
        # Step 2: Retreat check — if we're overwhelmed and can't hold,
        # evacuate all ships to the nearest friendly planet.
        # ------------------------------------------------------------------
        net_defence = src.ships + incoming[src.id]['friend'] - incoming[src.id]['enemy']
        if net_defence < 0 and available > MIN_GARRISON:
            retreat_planet = find_safe_retreat(src, planets, player)
            if retreat_planet is not None:
                evacuate = max(1, int(src.ships * 0.9))
                fire_angle, _, _ = intercept_angle(
                    src.x, src.y,
                    retreat_planet.x, retreat_planet.y,
                    retreat_planet.orbital_angle, retreat_planet.orbital_radius,
                    omega, evacuate, retreat_planet.is_comet)
                fire_angle = safe_angle(src.x, src.y,
                                        retreat_planet.x, retreat_planet.y,
                                        fire_angle)
                moves.append([src.id, fire_angle, evacuate])
                continue   # skip normal attack logic for this planet

        if available < 1:
            continue

        # ------------------------------------------------------------------
        # Step 3: Score all potential targets and pick the best one.
        # ------------------------------------------------------------------
        candidates = [p for p in planets if p.owner != player]
        if not candidates:
            # All planets owned — reinforce weakest own planet
            weakest = min(my_planets,
                          key=lambda p: p.ships if p.id != src.id else float('inf'))
            if weakest.id != src.id and weakest.ships < src.ships * 0.5:
                fire_angle, _, _ = intercept_angle(
                    src.x, src.y,
                    weakest.x, weakest.y,
                    weakest.orbital_angle, weakest.orbital_radius,
                    omega, int(available), weakest.is_comet)
                fire_angle = safe_angle(src.x, src.y, weakest.x, weakest.y, fire_angle)
                moves.append([src.id, fire_angle, int(available // 2)])
            continue

        scored = []
        for tgt in candidates:
            s = score_target(src, tgt, player, omega, int(available))
            if s > 0:
                scored.append((s, tgt))

        if not scored:
            continue

        scored.sort(key=lambda x: -x[0])
        best_score, best_tgt = scored[0]

        # ------------------------------------------------------------------
        # Step 4: Compute ships to send.
        # Coordinate with other planets already sending to this target —
        # don't send more than needed.
        # ------------------------------------------------------------------
        already_en_route = ships_en_route.get(best_tgt.id, 0.0)
        # Ships needed to capture: defenders + a buffer
        needed = max(0, best_tgt.ships - already_en_route + 5)
        ships_to_send = min(int(available), int(needed))

        if ships_to_send < 1:
            continue

        # ------------------------------------------------------------------
        # Step 5: Compute intercept angle with orbital prediction.
        # ------------------------------------------------------------------
        fire_angle, ix, iy = intercept_angle(
            src.x, src.y,
            best_tgt.x, best_tgt.y,
            best_tgt.orbital_angle, best_tgt.orbital_radius,
            omega, ships_to_send, best_tgt.is_comet)

        # ------------------------------------------------------------------
        # Step 6: Sun avoidance — deflect if path crosses sun zone.
        # ------------------------------------------------------------------
        fire_angle = safe_angle(src.x, src.y, ix, iy, fire_angle)

        moves.append([src.id, fire_angle, ships_to_send])
        ships_en_route[best_tgt.id] = ships_en_route.get(best_tgt.id, 0.0) + ships_to_send

    return moves


# ---------------------------------------------------------------------------
# Public agent entry point
# ---------------------------------------------------------------------------

def agent(obs: dict) -> List[List]:
    """
    Kaggle Orbit Wars agent entry point.

    Accepts the observation dict each turn and returns a list of moves:
        [[from_planet_id, direction_angle_radians, num_ships], ...]

    The function is wrapped in a top-level try/except so it NEVER crashes
    the simulation — in the absolute worst case it returns [] (pass).
    """
    try:
        return compute_moves(obs)
    except Exception:
        # Safe fallback: pass the turn rather than crash
        return []


# =============================================================================
# Test harness — run with:  python orbit_wars_agent.py
# =============================================================================

if __name__ == '__main__':
    import json

    # -------------------------------------------------------------------------
    # Mock observation — 2-player game, turn 1
    # -------------------------------------------------------------------------
    mock_obs = {
        "player": 0,           # we are player index 0 => owner ID 1
        "angular_velocity": 0.008,
        "comet_planet_ids": [5],
        "remainingOverageTime": 60.0,
        "planets": [
            # [id, owner, x,    y,    radius, ships, production]
            [0,  1,  20.0, 50.0, 15.0,  30.0,  3.0],   # our starting planet
            [1,  2,  80.0, 50.0, 15.0,  30.0,  3.0],   # enemy starting planet
            [2,  0,  50.0, 20.0, 10.0,  10.0,  2.0],   # neutral planet (north)
            [3,  0,  50.0, 80.0, 10.0,  10.0,  2.0],   # neutral planet (south)
            [4,  0,  35.0, 35.0,  8.0,   5.0,  1.0],   # neutral small planet
            [5,  0,  65.0, 65.0,  6.0,   3.0,  0.5],   # comet planet
        ],
        "fleets": [
            # [id, owner, x,    y,    angle, from_planet_id, ships]
            [0,  2,  75.0, 50.0, math.pi, 1, 10.0],   # enemy fleet heading west
        ],
    }

    print("=" * 60)
    print("Orbit Wars Agent — Test Harness")
    print("=" * 60)
    print(f"\nMock observation (player=0 => owner ID 1):")
    print(f"  My planets : {[p[0] for p in mock_obs['planets'] if p[1] == 1]}")
    print(f"  Enemy planets: {[p[0] for p in mock_obs['planets'] if p[1] == 2]}")
    print(f"  Neutral planets: {[p[0] for p in mock_obs['planets'] if p[1] == 0]}")
    print(f"  Comet planet IDs: {mock_obs['comet_planet_ids']}")
    print(f"  Angular velocity: {mock_obs['angular_velocity']} rad/turn")

    moves = agent(mock_obs)

    print(f"\nAgent returned {len(moves)} move(s):")
    for m in moves:
        pid, angle, ships = m
        print(f"  Planet {pid} -> fire at {math.degrees(angle):.1f} deg "
              f"with {ships} ships")

    # -------------------------------------------------------------------------
    # Verify output format
    # -------------------------------------------------------------------------
    assert isinstance(moves, list), "agent() must return a list"
    for m in moves:
        assert len(m) == 3, "Each move must be [planet_id, angle, ships]"
        assert isinstance(m[0], int), "planet_id must be int"
        assert isinstance(m[1], float), "angle must be float"
        assert isinstance(m[2], int), "ships must be int"

    print("\nAll format assertions passed.")

    # -------------------------------------------------------------------------
    # Physics sanity checks
    # -------------------------------------------------------------------------
    print("\nPhysics checks:")
    for n in [1, 10, 100, 500, 1000]:
        spd = fleet_speed(n)
        print(f"  fleet_speed({n:4d} ships) = {spd:.3f} px/turn")

    print("\nSun avoidance check:")
    # Path from (20,50) to (80,50) passes through sun at (50,50)
    crosses = path_crosses_sun(20, 50, 80, 50)
    print(f"  (20,50) -> (80,50) crosses sun: {crosses}  (expected True)")
    deflected = safe_angle(20, 50, 80, 50, 0.0)
    print(f"  Deflected angle: {math.degrees(deflected):.1f} deg  (raw was 0.0 deg)")

    print("\nOrbital intercept check:")
    # Target orbiting at radius ~28 from sun, starting at (20,50)
    fa, ix, iy = intercept_angle(
        src_x=80.0, src_y=50.0,
        tgt_x=20.0, tgt_y=50.0,
        tgt_base_angle=orbital_angle(20.0, 50.0),
        tgt_orbital_radius=orbital_radius(20.0, 50.0),
        omega=0.008,
        num_ships=15,
        is_comet=False
    )
    print(f"  Intercept point: ({ix:.2f}, {iy:.2f})")
    print(f"  Fire angle: {math.degrees(fa):.1f} deg")

    print("\nTest harness complete.")
