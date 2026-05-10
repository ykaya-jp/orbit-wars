## [MD]
# Orbit Wars - Matplotlib FuncAnimation Version

This notebook converts the original HTML Canvas visualizer into a pure Python `matplotlib.animation.FuncAnimation` version.

Use this version when:
- You want Kaggle Notebook compatibility.
- You want a visual demo without JavaScript Canvas.
- You want a Python-only animation cell.

## [CODE]
```python
# =========================================================
# Orbit Wars - Matplotlib FuncAnimation Version
# =========================================================
# This version is designed for Jupyter / Kaggle Notebook.
# It converts the HTML Canvas-style visualizer into a pure Python animation.
#
# Features:
# - Planet ownership colors
# - Orbiting planets inside the rotation limit
# - Moving fleets with trails
# - Sun collision detection
# - Planet capture / reinforcement logic
# - Matplotlib FuncAnimation output
# =========================================================

import math
import random
from dataclasses import dataclass, field

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Circle, Polygon
from IPython.display import HTML, display

# -----------------------------
# Global settings
# -----------------------------
WIDTH = 1200
HEIGHT = 1200
CENTER_X = WIDTH / 2
CENTER_Y = HEIGHT / 2

SUN_RADIUS = 60
ROTATION_LIMIT = 300

N_FRAMES = 360
INTERVAL_MS = 40
SPEED = 1.0

COLOR_BG = "#000814"
COLOR_GRID = "#123044"
COLOR_SUN = "#ffd60a"
COLOR_PLAYER = "#00b4d8"
COLOR_ENEMY = "#e63946"
COLOR_NEUTRAL = "#6c757d"
COLOR_FLEET = "#06ffa5"
COLOR_ORBIT = "#7209b7"
COLOR_TEXT = "#f1faee"


@dataclass
class Planet:
    id: int
    owner: int          # 0 = player, 1 = enemy, -1 = neutral
    x: float
    y: float
    radius: float
    ships: int
    production: int
    angle: float = 0.0
    orbit_radius: float = 0.0


@dataclass
class Fleet:
    owner: int
    x: float
    y: float
    target_id: int
    ships: int
    speed: float = 6.0
    trail: list = field(default_factory=list)


def distance(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


def owner_color(owner):
    if owner == 0:
        return COLOR_PLAYER
    if owner == 1:
        return COLOR_ENEMY
    return COLOR_NEUTRAL


def init_planets():
    planets = [
        Planet(0, 0, 240, 240, 30, 40, 3),
        Planet(1, 0, 960, 960, 30, 35, 3),
        Planet(2, -1, 360, 840, 24, 15, 2),
        Planet(3, -1, 840, 360, 24, 20, 4),
        Planet(4, -1, 600, 180, 18, 10, 1),
        Planet(5, -1, 420, 600, 18, 12, 2),
        Planet(6, 1, 180, 1020, 30, 30, 3),
        Planet(7, 1, 1020, 180, 30, 32, 3),
    ]

    for p in planets:
        p.orbit_radius = distance(p.x, p.y, CENTER_X, CENTER_Y)
        p.angle = math.atan2(p.y - CENTER_Y, p.x - CENTER_X)

    return planets


def is_orbiting(planet):
    return planet.orbit_radius + planet.radius < ROTATION_LIMIT


def update_orbit(planet):
    if not is_orbiting(planet):
        return

    angular_velocity = 0.012 * SPEED
    planet.angle += angular_velocity
    planet.x = CENTER_X + planet.orbit_radius * math.cos(planet.angle)
    planet.y = CENTER_Y + planet.orbit_radius * math.sin(planet.angle)


def create_fleet(planets):
    player_planets = [p for p in planets if p.owner == 0 and p.ships >= 20]
    targets = [p for p in planets if p.owner != 0]

    if not player_planets or not targets:
        return None

    source = random.choice(player_planets)
    target = random.choice(targets)

    ships = max(5, int(source.ships * 0.45))
    source.ships -= ships

    angle = math.atan2(target.y - source.y, target.x - source.x)
    start_x = source.x + math.cos(angle) * (source.radius + 8)
    start_y = source.y + math.sin(angle) * (source.radius + 8)

    return Fleet(
        owner=0,
        x=start_x,
        y=start_y,
        target_id=target.id,
        ships=ships,
        speed=6.0,
    )


def update_fleets(fleets, planets):
    alive_fleets = []

    for fleet in fleets:
        target = next((p for p in planets if p.id == fleet.target_id), None)
        if target is None:
            continue

        fleet.trail.append((fleet.x, fleet.y))
        if len(fleet.trail) > 25:
            fleet.trail.pop(0)

        # Sun collision
        if distance(fleet.x, fleet.y, CENTER_X, CENTER_Y) < SUN_RADIUS + 15:
            continue

        dx = target.x - fleet.x
        dy = target.y - fleet.y
        d = math.hypot(dx, dy)

        if d < target.radius + 5:
            # Reinforcement
            if target.owner == fleet.owner:
                target.ships += fleet.ships
            # Attack
            else:
                target.ships -= fleet.ships
                if target.ships < 0:
                    target.ships = abs(target.ships)
                    target.owner = fleet.owner
            continue

        fleet.x += (dx / d) * fleet.speed * SPEED
        fleet.y += (dy / d) * fleet.speed * SPEED
        alive_fleets.append(fleet)

    return alive_fleets


def draw_scene(ax, planets, fleets, frame):
    ax.clear()
    ax.set_facecolor(COLOR_BG)
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(0, HEIGHT)
    ax.set_aspect("equal")
    ax.set_title(
        f"Orbit Wars - FuncAnimation Demo | Frame {frame:03d} | Fleets: {len(fleets)}",
        color=COLOR_TEXT,
        fontsize=14,
        pad=12,
    )

    # Hide axis labels
    ax.set_xticks([])
    ax.set_yticks([])

    # Grid
    for g in range(0, WIDTH + 1, 100):
        ax.plot([g, g], [0, HEIGHT], color=COLOR_GRID, linewidth=0.5, alpha=0.45)
        ax.plot([0, WIDTH], [g, g], color=COLOR_GRID, linewidth=0.5, alpha=0.45)

    # Rotation limit
    ax.add_patch(
        Circle(
            (CENTER_X, CENTER_Y),
            ROTATION_LIMIT,
            fill=False,
            linestyle="--",
            linewidth=2,
            edgecolor=COLOR_ORBIT,
            alpha=0.55,
        )
    )

    # Sun glow layers
    for r, alpha in [(115, 0.05), (90, 0.08), (70, 0.14)]:
        ax.add_patch(Circle((CENTER_X, CENTER_Y), r, color=COLOR_SUN, alpha=alpha, linewidth=0))

    # Sun
    ax.add_patch(Circle((CENTER_X, CENTER_Y), SUN_RADIUS, color=COLOR_SUN, alpha=0.95))
    ax.text(CENTER_X, CENTER_Y, "SUN", ha="center", va="center", color="#3a2500", fontsize=11, fontweight="bold")

    # Planet orbit paths
    for p in planets:
        if is_orbiting(p):
            ax.add_patch(
                Circle(
                    (CENTER_X, CENTER_Y),
                    p.orbit_radius,
                    fill=False,
                    linewidth=1,
                    edgecolor=COLOR_ORBIT,
                    alpha=0.18,
                )
            )

    # Fleet trails
    for f in fleets:
        if len(f.trail) >= 2:
            xs, ys = zip(*f.trail)
            ax.plot(xs, ys, color=COLOR_FLEET, alpha=0.35, linewidth=2)

    # Fleets
    for f in fleets:
        target = next((p for p in planets if p.id == f.target_id), None)
        if target is None:
            continue

        angle = math.atan2(target.y - f.y, target.x - f.x)
        size = 18

        triangle = np.array([
            [size, 0],
            [-size * 0.65, -size * 0.45],
            [-size * 0.65, size * 0.45],
        ])

        rot = np.array([
            [math.cos(angle), -math.sin(angle)],
            [math.sin(angle), math.cos(angle)],
        ])

        points = triangle @ rot.T + np.array([f.x, f.y])

        ax.add_patch(Polygon(points, closed=True, color=COLOR_FLEET, alpha=0.95))
        ax.text(f.x, f.y - 22, str(f.ships), color=COLOR_TEXT, ha="center", fontsize=9)

    # Planets
    for p in planets:
        color = owner_color(p.owner)

        # glow
        ax.add_patch(Circle((p.x, p.y), p.radius * 1.45, color=color, alpha=0.12, linewidth=0))

        # body
        ax.add_patch(Circle((p.x, p.y), p.radius, color=color, alpha=0.95))
        ax.add_patch(Circle((p.x, p.y), p.radius, fill=False, edgecolor="white", linewidth=1.2, alpha=0.55))

        # labels
        ax.text(p.x, p.y, str(int(p.ships)), color=COLOR_TEXT, ha="center", va="center", fontsize=10, fontweight="bold")
        ax.text(p.x, p.y - p.radius - 13, f"P{p.id}", color=COLOR_TEXT, ha="center", fontsize=8, alpha=0.85)
        ax.text(p.x, p.y + p.radius + 14, f"+{p.production}", color=COLOR_TEXT, ha="center", fontsize=8, alpha=0.85)

    # Legend
    legend_text = "Blue: Player   Red: Enemy   Gray: Neutral   Green: Fleet   Yellow: Sun"
    ax.text(
        WIDTH / 2,
        35,
        legend_text,
        ha="center",
        va="center",
        color=COLOR_TEXT,
        fontsize=9,
        alpha=0.85,
    )


def run_animation():
    random.seed(7)
    planets = init_planets()
    fleets = []

    fig, ax = plt.subplots(figsize=(8, 8))
    fig.patch.set_facecolor(COLOR_BG)

    def animate(frame):
        nonlocal fleets

        # Add a fleet every 45 frames
        if frame % 45 == 5:
            new_fleet = create_fleet(planets)
            if new_fleet is not None:
                fleets.append(new_fleet)

        # Update planets and fleets
        for p in planets:
            update_orbit(p)

        fleets = update_fleets(fleets, planets)

        draw_scene(ax, planets, fleets, frame)
        return []

    anim = FuncAnimation(
        fig,
        animate,
        frames=N_FRAMES,
        interval=INTERVAL_MS,
        blit=False,
        repeat=True,
    )

    plt.close(fig)
    return anim


anim = run_animation()

# In Kaggle / Jupyter, this usually displays the animation inline.
HTML(anim.to_jshtml())
```
