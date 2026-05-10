## [MD]
# Orbit Wars - My Learning Journey: First Rule-based Agent

**Final Score: 444 points** | Submission ID: 52509890 | Date: May 10, 2026

This notebook documents my first serious attempt at the Orbit Wars competition. I'm learning game strategy and sharing my approach publicly to get feedback and help others learning too!

## [MD]
## My Learning Process

As a beginner in this competition, I wanted to build a solid rule-based agent before trying more complex approaches. This is my first submission with actual strategy (not just random moves).

### What I Tried to Implement

After reading the competition rules and looking at some discussions, I tried to implement these ideas:

1. **Don't drain all planets** - Keep some ships for defense
2. **Attack close targets first** - Minimize travel time
3. **Prefer neutral planets early** - Build up before fighting
4. **Avoid the sun** - Don't send fleets that will crash

I know there are much better strategies out there (top scores are 1500+!), but I wanted to start simple and understand the basics.

## [MD]
## My Results

### Submission Performance
- **Public Score: 444 points**
- Status: Complete
- Submission: main.py

### What Worked
- Basic expansion to neutral planets 鉁揬n- Sun avoidance 鉁揬n- No crashes or timeouts 鉁揬n
### What Didn't Work Well
- Defense was too weak - lost planets quickly 鉁梊n- Didn't coordinate multiple planets 鉁梊n- No fleet interception logic 鉁梊n- Completely ignored comets 鉁梊n
### Comparison to Leaderboard
- Top score: ~1700 points
- My score: 444 points
- **Lots of room to improve!**

## [MD]
## The Agent Code

Here's my complete agent. It's not fancy, but it's a start!

## [CODE]
```python
"""
My First Rule-based Agent for Orbit Wars

Learning approach:
- Keep planets safe (don't drain them)
- Attack nearby neutrals first
- Avoid the sun
- Be more aggressive in mid-game
"""

import math
from collections import namedtuple

# Game constants
BOARD = 100.0
CENTER = 50.0
SUN_R = 10.0
MAX_SPEED = 6.0
MAX_TURNS = 500

Planet = namedtuple('Planet', ['id', 'owner', 'x', 'y', 'radius', 'ships', 'production'])
Fleet = namedtuple('Fleet', ['id', 'owner', 'x', 'y', 'angle', 'from_planet_id', 'ships'])

class ImprovedAgent:
    def __init__(self):
        self.turn = 0
        self.player = None
        self.opponent_style = 'unknown'
        self.opponent_action_history = []

    def get_game_phase(self):
        """Return game phase: 0=early, 1=mid, 2=late."""
        if self.turn < 80:
            return 0
        elif self.turn < 350:
            return 1
        else:
            return 2

    def estimate_opponent_style(self, obs):
        """Try to detect if opponent is aggressive."""
        fleets = [Fleet(*f) for f in obs.get('fleets', [])]

        enemy_fleets = [f for f in fleets if f.owner != self.player and f.owner != -1]

        # Simple detection: many fleets = aggressive
        if self.turn < 100 and len(enemy_fleets) > 5:
            self.opponent_style = 'aggressive'
        elif self.turn < 100 and len(enemy_fleets) < 2:
            self.opponent_style = 'conservative'

        return self.opponent_style

    def crosses_sun(self, x1, y1, x2, y2):
        """Check if path crosses the sun."""
        dx = x2 - x1
        dy = y2 - y1
        fx = CENTER - x1
        fy = CENTER - y1

        a = dx * dx + dy * dy
        if a < 1e-6:
            return False

        b = 2 * (fx * dx + fy * dy)
        c = fx * fx + fy * fy - SUN_R * SUN_R

        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            return False

        sqrt_disc = math.sqrt(discriminant)
        t1 = (-b - sqrt_disc) / (2 * a)
        t2 = (-b + sqrt_disc) / (2 * a)

        return (0 <= t1 <= 1) or (0 <= t2 <= 1) or (t1 < 0 and t2 > 1)

    def get_eta(self, source, target, ships):
        """Estimate arrival time."""
        dist = math.hypot(target.x - source.x, target.y - source.y)
        speed = 1.0 + (MAX_SPEED - 1.0) * (math.log(max(1, ships)) / math.log(1000)) ** 1.5
        return dist / speed

    def classify_source_type(self, source, planets):
        """Classify planet by distance to enemies."""
        enemies = [p for p in planets if p.owner != self.player and p.owner != -1]

        if not enemies:
            return 'rear'

        min_enemy_dist = min(
            math.hypot(source.x - e.x, source.y - e.y)
            for e in enemies
        )

        if min_enemy_dist < 25:
            return 'frontier'
        elif min_enemy_dist < 40:
            return 'staging'
        else:
            return 'rear'

    def calculate_safe_surplus(self, source, planets, fleets, source_type):
        """Calculate how many ships we can safely send."""
        phase = self.get_game_phase()

        # Keep enough for defense
        base_keep = 8 + source.production * 2

        # Check nearby threats
        enemies = [p for p in planets if p.owner != self.player and p.owner != -1]
        nearby_enemy_ships = sum(
            p.ships * 0.4 for p in enemies
            if math.hypot(p.x - source.x, p.y - source.y) < 30
        )

        enemy_fleets = [f for f in fleets if f.owner != self.player]
        incoming_threat = sum(
            f.ships * 1.2 for f in enemy_fleets
            if math.hypot(f.x - source.x, f.y - source.y) < 20
        )

        # Different keeps for different planet types
        if source_type == 'frontier':
            keep_need = max(
                base_keep,
                source.production * 5,
                nearby_enemy_ships,
                incoming_threat
            )
        elif source_type == 'staging':
            keep_need = max(
                base_keep,
                source.production * 3,
                nearby_enemy_ships * 0.7,
                incoming_threat
            )
        else:  # rear
            keep_need = max(
                base_keep,
                source.production * 2,
                incoming_threat * 0.5
            )

        # Be more aggressive mid-game
        if phase == 1 and source_type == 'rear':
            keep_need *= 0.8

        surplus = max(0, source.ships - keep_need)
        return int(surplus)

    def score_target(self, source, target, planets, source_surplus):
        """Score how good a target is."""
        phase = self.get_game_phase()

        if target.owner == self.player:
            return -1

        dist = math.hypot(target.x - source.x, target.y - source.y)

        if dist > 70:
            return -1

        if self.crosses_sun(source.x, source.y, target.x, target.y):
            return -1

        cost = target.ships + 1

        if cost > source_surplus:
            return -1

        eta = self.get_eta(source, target, cost)
        prod_value = target.production

        remaining_turns = MAX_TURNS - self.turn - eta
        if remaining_turns < 0:
            return -1

        time_value = remaining_turns * prod_value
        efficiency = (time_value + prod_value * 10) / (cost + 1) / (dist + 1)

        # Prefer neutrals
        if target.owner == -1:
            efficiency *= 1.4
            if phase == 0:
                efficiency *= 1.3

        if phase == 0 and dist > 40:
            efficiency *= 0.7

        if phase == 1 and prod_value >= 3:
            efficiency *= 1.2

        if phase == 2 and eta < 20:
            efficiency *= 1.3

        # Check for friendly support
        nearby_allies = sum(
            1 for p in planets
            if p.owner == self.player and p.id != source.id
            and math.hypot(p.x - target.x, p.y - target.y) < 25
        )
        if nearby_allies >= 2:
            efficiency *= 1.15

        nearby_enemies = sum(
            1 for p in planets
            if p.owner != self.player and p.owner != -1
            and math.hypot(p.x - target.x, p.y - target.y) < 25
        )
        if nearby_enemies >= 2:
            efficiency *= 0.85

        return efficiency

    def act(self, obs):
        """Main decision function."""
        self.player = obs.get('player', 0) if isinstance(obs, dict) else obs.player

        planets = [Planet(*p) for p in obs.get('planets', [])]
        fleets = [Fleet(*f) for f in obs.get('fleets', [])]

        my_planets = [p for p in planets if p.owner == self.player]

        self.estimate_opponent_style(obs)

        moves = []

        for source in my_planets:
            source_type = self.classify_source_type(source, planets)
            surplus = self.calculate_safe_surplus(source, planets, fleets, source_type)

            if surplus < 3:
                continue

            target_scores = []
            for target in planets:
                if target.id == source.id:
                    continue

                score = self.score_target(source, target, planets, surplus)
                if score > 0:
                    target_scores.append((score, target))

            if not target_scores:
                continue

            target_scores.sort(reverse=True)
            best_score, best_target = target_scores[0]

            cost = best_target.ships + 1

            phase = self.get_game_phase()
            if best_target.owner == -1:
                margin = 1.1
            elif phase == 2:
                margin = 1.15
            else:
                margin = 1.2

            ships_to_send = min(surplus, int(cost * margin))

            if ships_to_send >= 1:
                angle = math.atan2(
                    best_target.y - source.y,
                    best_target.x - source.x
                )
                moves.append([source.id, angle, ships_to_send])

        self.turn += 1
        return moves

# Entry point
_agent = None

def agent(obs):
    """Main agent function."""
    global _agent
    if _agent is None:
        _agent = ImprovedAgent()

    try:
        return _agent.act(obs)
    except Exception:
        return []
```

## [MD]
## What I Learned

### Key Takeaways
1. **Defense matters more than I thought** - I kept losing planets I just captured
2. **Distance is expensive** - Long-range attacks often failed
3. **Sun avoidance is critical** - Lost several fleets early on
4. **Production value >> immediate gains** - Should prioritize high-production planets

### What I'll Try Next
- Better defense logic (detect incoming fleets)
- Comet capture strategy
- Fleet interception
- Multi-planet coordination
- Study top players' replays

## [MD]
## Resources That Helped Me

- [Orbit Wars Competition](https://www.kaggle.com/competitions/orbit-wars)
- [Game Rules](https://www.kaggle.com/competitions/orbit-wars/overview)
- Discussion forums for strategy tips

---

**Feedback Welcome!** I'm still learning and would love suggestions on how to improve.

**Author**: Dreamurr
**Date**: May 10, 2026
**Score**: 444 points
**Status**: Learning in progress!
