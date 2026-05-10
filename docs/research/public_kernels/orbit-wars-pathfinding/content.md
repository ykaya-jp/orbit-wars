## [MD]
# Goal

The goal of this notebook is to find a way to say, given $A$ if, and how, it is possible to send a fleet from $A$ to $B$.

## [CODE]
```python
from IPython.display import HTML, display
import html

path = "/kaggle/input/datasets/vincentcaujolle/orbit-wars-pathfinding-exemple/exemple.html"

with open(path, "r", encoding="utf-8") as f:
  content = f.read()

display(HTML(f"""
<iframe
  srcdoc="{html.escape(content, quote=True)}"
  width="100%"
  height="750"
  style="border:0; background:#212121;"
></iframe>
"""))
```

## [MD]
# Simplified Setting (No Collision Assumption)

We first consider a simplified setting where only $A$ and $B$ exist. All other bodies (sun, other planets, comets) are ignored. \
Let
- $A \in \mathbb{R}^2$ the center of the source
- $B(t) \in \mathbb{R}^2$ the center of the target at time $t$
- $r_A, r_B > 0$ the radius of $A$ and $B$
- $v$ the speed of the fleet

## Distance Model

Define the distance between the centers of the two planets at time t

$$ d(t) = \| B(t) - A \|_2 $$

At time $t$, the fleet can reach any point at distance

$$ r(t) = r_A + vt $$

from the center of $A$. This corresponds to the set of all positions reachable by a fleet launched from the surface of $A$.

## Interception Condition

A collision occurs if the reachable set of the fleet intersects the closed disk of planet B, i.e

$$ \partial B_0(A, r(t)) \cap B_0(B(t), r_B) \neq \emptyset $$

This is equivalent to the scalar condition

$$ |d(t) - r(t)| \leq r_B $$

or explicitly

$$ |d(t) - r_A - vt| \leq r_B $$

## Earliest Feasible Interception Time

We define the interception problem as finding the earliest time $t>0$ at which the fleet can reach the target planet. This leads to the following constrained optimization problem:

$$
\text{(P0)}
\quad
\min_{t>0} t \quad \text{s.t.}
\quad
|d(t) - r_A - vt| \leq r_B
$$

A solution $t^\star$ corresponds to the earliest time at which the reachable set of the fleet intersects the target planet.

## Feasible Angles

Once a feasible time $t^\star$ is found, define

$$
r^\star = r_A + vt^\star,
\quad
d^\star = \|B(t^\star)-A\|_2
$$

At time $t^\star$, the fleet lies on the circle $\partial B_0(A, r^\star)$, while the target occupies the disk $B_0(B(t^\star), r_B)$. An interception corresponds to choosing a point $Q$ in the intersection of these two sets. \
Let

$$
\phi =
\operatorname{atan2}
\left(
B_y(t^\star) - A_y,\,
B_x(t^\star) - A_x
\right)
$$

be the direction from $A$ to the center of $B(t^\star)$. The set of admissible directions is an interval centered at $\phi$, whose half-width is given by

$$
\delta =
\arccos\left(
\frac{
(d^\star)^2 + (r^\star)^2 - r_B^2
}{
2 d^\star r^\star
}
\right)
$$

Therefore, the admissible angles are

$$
\alpha \in [\phi - \delta,\ \phi + \delta]
$$

## [CODE]
```python
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import math
from matplotlib.patches import Arc, Wedge

def plot_interception_geometry(A_coords, B_coords, r_A, r_B, r_star):
    fig, ax = plt.subplots(figsize=(12, 12))

    A = np.array(A_coords)
    B_pos = np.array(B_coords)

    d_star = np.linalg.norm(B_pos - A)
    phi = math.atan2(B_pos[1] - A[1], B_pos[0] - A[0])

    cos_val = (d_star**2 + r_star**2 - r_B**2) / (2 * d_star * r_star)
    cos_val = max(-1.0, min(1.0, cos_val))
    delta = math.acos(cos_val)


    A_circle = patches.Circle(A, r_A, color='blue', alpha=0.5, label='Planet A')
    ax.add_patch(A_circle)

    B_circle = patches.Circle(B_pos, r_B, color='red', alpha=0.5, label=r'Target B($t^\star$)')
    ax.add_patch(B_circle)

    fleet_range = patches.Circle(A, r_star, color='blue', fill=False, linestyle='--', label=r"Fleet Range $r^\star$")
    ax.add_patch(fleet_range)

    angle_min_deg = math.degrees(phi - delta)
    angle_max_deg = math.degrees(phi + delta)
    launch_sector = Wedge(A, r_star, angle_min_deg, angle_max_deg,
                          fill=False, hatch='//', edgecolor='green', alpha=0.4, zorder=1)
    ax.add_patch(launch_sector)

    ax.plot(*A, 'ko', zorder=5)
    ax.plot(*B_pos, 'ko', zorder=5)

    ax.plot([A[0], B_pos[0]], [A[1], B_pos[1]], 'k-.', linewidth=1.5, zorder=4, label=r'Line of Sight $\phi$')

    arc_radius = d_star * 0.5

    visual_arc = Arc(A, arc_radius * 2, arc_radius * 2, angle=0,
                    theta1=math.degrees(phi), theta2=math.degrees(phi + delta),
                    color='purple', linewidth=1.5, linestyle='-', zorder=10)
    ax.add_patch(visual_arc)

    mid_angle_rad = (phi + (phi + delta)) / 2.0
    x_delta_text = A[0] + (arc_radius * 1.15) * np.cos(mid_angle_rad)
    y_delta_text = A[1] + (arc_radius * 1.15) * np.sin(mid_angle_rad)

    ax.text(x_delta_text, y_delta_text, r'$\delta$',
            color='purple', fontsize=12, fontweight='bold',
            ha='center', va='center', zorder=11)

    ax.set_aspect('equal')
    ax.set_title(r"Interception Geometry at Time $t^\star$")

    handles, labels = ax.get_legend_handles_labels()

    handles.append(launch_sector)
    labels.append(r"Admissible Launch Sector")


    ax.legend(handles=handles, labels=labels, loc='lower left')
    ax.grid(True, linestyle=':')

    plt.tight_layout()
    plt.show()

plot_interception_geometry(A_coords=(10, 10), B_coords=(40, 50), r_A=5, r_B=8, r_star=45)
```

## [MD]
# Full Model With Collision Constraints

We now include the other bodies of the game: the sun, planets, and comets. Each body is modeled as a disk whose center may depend on time. \
Let

$$
\mathcal O(t)=\{O_1(t),\ldots,O_m(t)\}
$$

be the set of obstacles at time $t$, where each obstacle $O_i(t)$ is described by a center $C_i(t)\in\mathbb R^2$ and a radius $r_i>0$. The target $B$ is excluded from this obstacle set.

A fleet launched from $A$ with angle $\alpha$ follows the straight-line trajectory

$$
F_\alpha(s)
=
A + (r_A+vs)
\begin{pmatrix}
\cos\alpha\\
\sin\alpha
\end{pmatrix},
\qquad s\ge 0
$$

and if the fleet does not collide with any obstacle before reaching $B$. This means that for every obstacle $O_i$ and every time $s\in[0,t[$,

$$
\|F_\alpha(s)-C_i(s)\|_2 > r_i.
$$

Therefore, the complete feasibility condition is

$$
\exists \alpha \in [\phi - \delta,\ \phi + \delta]
\quad
\text{s.t.}
\quad
\forall i,\ \forall s\in]0,t[,
\|F_\alpha(s)-C_i(s)\|_2 > r_i
$$

## Iterative Search

The complete problem can be solved by searching feasible interception times in increasing order.

We start with $t_0=0$. At iteration $n$, we solve

$$
\text{(Pn)}
\quad t_n
=
\min_{t>t_{n-1}}
t
\quad
\text{s.t.}
\quad
|d(t)-r_A-vt|\le r_B.
$$

For this time $t_n$, we compute the associated admissible angle interval

$$
\alpha_n \in [\phi(t_n)-\delta(t_n),\phi(t_n)+\delta(t_n)].
$$

We then check whether there exists an angle $\alpha_n$ such that the trajectory $F_\alpha$ is collision-free on $[0,t_n[$. If such an angle exists, then $(t_n,\alpha)$ is a valid solution. If no such angle exists, the current interception opportunity is rejected and the search continues with the next feasible time.

To make the search finite, we need to restrict the interception time to a bounded interval. Since the board is a $100 \times 100$ square, the maximum possible distance a fleet can travel while remaining inside the board is bounded by the board diagonal $L_{\max}=100\sqrt{2}$. Since the fleet moves at speed $v$, any useful trajectory must satisfy

$$
vt \le L_{\max}.
$$

Therefore, it is enough to search for interception times in

$$
t \in ]0,t_{\max}],
$$

where

$$
t_{\max}
=
\min\left(
t_{\mathrm{remaining}},
\frac{100\sqrt{2}}{v}
\right)
$$

Better $t_{max}$ are easy to find.
## Final Problem

The complete problem is therefore

$$
\min_{0<t<t_{max}} t
\quad
\text{s.t.}
\quad
|d(t)-r_A-vt|\le r_B,
\quad
\text{and}
\quad
\exists \alpha \in [\phi - \delta,\ \phi + \delta]
\quad
\text{s.t.}
\quad
\forall i,\ \forall s\in]0,t[,
\|F_\alpha(s)-C_i(s)\|_2 > r_i
$$

This formulation separates the problem into three parts:

1. finding feasible interception times
2. computing the admissible angle interval for each feasible time
3. filtering candidate trajectories using collision constraints.

## [MD]
## Complexity Analysis

We analyze the computational complexity of the proposed approach.
Let
- $N_t$ the number of candidate times,
- $N_\alpha$ the number of angles tested per time,
- $P$ the number of obstacles (sun, planets, comets).

### Per Pair Complexity

For each candidate time, a constant number of angles is tested (typically the center direction and the two boundary angles). Hence $N_\alpha = O(1)$. \
Each angle requires checking for collisions against all obstacles. Therefore, the complexity per pair $(A,B)$ is

$$
O(P N_t)
$$

### Global Complexity

Let
- $P_A$ the number of source planets (owned by the player),
- $P_B$ the number of target planets (potential objectives),

Then the total complexity is

$$
O(P_A P_B N_t P)
$$

In the worst case, if all planets are considered as both sources and targets, this becomes

$$
O(P^3 N_t)
$$

### Practical Complexity

If time is discretized with step $\Delta t$, then

$$
N_t \approx \frac{t_{\max}}{\Delta t}
$$

Given that $v \in [1,6]$, we have $t_{\max} \leq 142$ \
In practice
- $P \leq 40$
- $N_\alpha = O(1)$
- $N_t \Delta t \leq 142$

This yields a total number of operations on the order of a few million per turn, which is computationally tractable.

## [MD]
## Dimensionality Reduction with Geometric Filters

The complete collision condition requires checking whether a fleet trajectory intersects any obstacle before the interception time. For a candidate time $t$ and angle $\alpha$, this condition can be written as

$$
\forall i,\ \forall s\in]0,t[,\quad
\|F_\alpha(s)-C_i(s)\|_2 > r_i
$$

This is the most accurate formulation, but it may be unnecessarily expensive if applied to every obstacle. In practice, most obstacles are geometrically unable to collide with the fleet trajectory. We can therefore use cheap geometric filters to discard them before running the exact collision check. \
These filters are not required for correctness, but they can significantly accelerate large-scale simulations and training.

### Fleet Segment

For a fixed angle $\alpha$, the fleet follows the segment $\overline{SE}$ where

$$
S = A + r_A
\begin{pmatrix}
\cos\alpha\\
\sin\alpha
\end{pmatrix}
$$

is the launch point, and

$$
E = S + vt
\begin{pmatrix}
\cos\alpha\\
\sin\alpha
\end{pmatrix}
$$

is the fleet position at time $t$.

### Static Obstacles

For a static obstacle with center $C_i$ and radius $r_i$, the collision test is exact and cheap. A collision occurs if and only if

$$
\operatorname{dist}(C_i,\overline{SE}) \leq r_i.
$$

This can be computed in constant time using the projection of $C_i$ onto the segment $\overline{SE}$.\
Let

$$
\lambda_i^\star
=
\frac{\langle C_i-S,E-S\rangle}{\|E-S\|_2^2}.
$$

Since the closest point must lie on the segment, we clamp this value to $[0,1]$:

$$
\bar{\lambda}_i
=
\min\left(1,\max\left(0,\lambda_i^\star\right)\right).
$$

The closest point on the segment is

$$
P_i^\star
=
S+\bar{\lambda}_i(E-S).
$$

Therefore, the collision condition is

$$
\|P_i^\star-C_i\|_2 \le r_i.
$$

## [CODE]
```python
import html
from IPython.display import display, HTML

html_source = r"""
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>

    <style>
        html, body {
            margin: 0;
            padding: 0;
            background: transparent;
            font-family: Arial, sans-serif;
        }

        .interactive-container {
            position: relative;
            width: 720px;
            height: 760px;
            margin: 0 auto;

            background: white;
            border: 1px solid #ddd;
            border-radius: 0px;
            box-sizing: border-box;
        }

        .title {
            text-align: center;
            padding-top: 12px;
            margin: 0;
            color: #222;
            font-size: 18px;
        }

        .plot-layer {
            position: absolute;
            top: 45px;
            left: 25px;
            width: 620px;
            height: 620px;
            background: white;
        }

        #sliderX {
            position: absolute;
            top: 680px;
            left: 85px;
            width: 500px;
            margin: 0;
            cursor: pointer;
        }

        #labelX {
            position: absolute;
            top: 705px;
            left: 85px;
            width: 500px;
            text-align: center;
            color: #222;
        }

        #sliderY {
            position: absolute;
            top: 105px;
            left: 660px;
            height: 500px;
            width: 20px;
            margin: 0;
            cursor: pointer;
            -webkit-appearance: slider-vertical;
            writing-mode: bt-lr;
        }

        #labelY {
            position: absolute;
            top: 60px;
            left: 632px;
            width: 75px;
            text-align: center;
            color: #222;
        }
    </style>
</head>

<body>
    <div class="interactive-container">
        <h3 class="title">Geometric Collision Filter for Static Obstacles</h3>

        <div id="plotly-div" class="plot-layer"></div>

        <input type="range" id="sliderX" min="0" max="50" step="0.5" value="30">
        <div id="labelX"><b>X C_i :</b> <span id="valX">30.0</span></div>

        <input type="range" id="sliderY" min="0" max="50" step="0.5" value="20" orient="vertical">
        <div id="labelY"><b>Y C_i :</b><br><span id="valY">20.0</span></div>
    </div>

    <script>
    const S = [10.0, 10.0];
    const E = [40.0, 40.0];
    const r_i = 6.0;

    function getCircleCoords(cx, cy, r) {
        let x = [];
        let y = [];

        for (let i = 0; i <= 100; i++) {
            let theta = (i / 100) * 2.0 * Math.PI;
            x.push(cx + r * Math.cos(theta));
            y.push(cy + r * Math.sin(theta));
        }

        return {x, y};
    }

    function computeProjection(cx, cy) {
        let vec_SE = [E[0] - S[0], E[1] - S[1]];
        let vec_SCi = [cx - S[0], cy - S[1]];

        let dot_product = vec_SCi[0] * vec_SE[0] + vec_SCi[1] * vec_SE[1];
        let norm_SE_sq = vec_SE[0] * vec_SE[0] + vec_SE[1] * vec_SE[1];

        let lambda_star = dot_product / norm_SE_sq;
        let lambda_bar = Math.max(0.0, Math.min(1.0, lambda_star));

        let P_star = [
            S[0] + lambda_bar * vec_SE[0],
            S[1] + lambda_bar * vec_SE[1]
        ];

        let dist = Math.hypot(P_star[0] - cx, P_star[1] - cy);

        return {P_star, dist};
    }

    function drawPlot() {
        let cx = parseFloat(document.getElementById("sliderX").value);
        let cy = parseFloat(document.getElementById("sliderY").value);

        document.getElementById("valX").innerText = cx.toFixed(1);
        document.getElementById("valY").innerText = cy.toFixed(1);

        let result = computeProjection(cx, cy);
        let P_star = result.P_star;
        let dist = result.dist;

        let collision = dist <= r_i;

        let obstacle_line_color = collision ? "red" : "green";
        let obstacle_fill_color = collision
            ? "rgba(255, 0, 0, 0.45)"
            : "rgba(0, 128, 0, 0.45)";

        let circle = getCircleCoords(cx, cy, r_i);

        let trace_obstacle = {
            x: circle.x,
            y: circle.y,
            mode: "lines",
            fill: "toself",
            line: {
                color: obstacle_line_color,
                width: 2
            },
            fillcolor: obstacle_fill_color,
            name: "Obstacle C_i",
            hoverinfo: "skip"
        };

        let trace_trajectory = {
            x: [S[0], E[0]],
            y: [S[1], E[1]],
            mode: "lines",
            line: {
                color: "blue",
                width: 3
            },
            name: "Trajectory SE",
            hoverinfo: "skip"
        };

        let trace_distance = {
            x: [cx, P_star[0]],
            y: [cy, P_star[1]],
            mode: "lines",
            line: {
                color: "black",
                width: 2,
                dash: "dashdot"
            },
            name: "Distance ||P_i* - C_i||₂",
            hoverinfo: "skip"
        };

        let trace_projection = {
            x: [P_star[0]],
            y: [P_star[1]],
            mode: "markers+text",
            marker: {
                color: "purple",
                size: 11
            },
            text: ["P_i*"],
            textposition: "bottom right",
            textfont: {
                size: 15,
                color: "purple"
            },
            name: "Projection P_i*",
            hovertemplate:
                "P_i* = (" +
                P_star[0].toFixed(2) +
                ", " +
                P_star[1].toFixed(2) +
                ")<extra></extra>"
        };

        let trace_points = {
            x: [S[0], E[0], cx],
            y: [S[1], E[1], cy],
            mode: "markers+text",
            marker: {
                color: "black",
                size: 10
            },
            text: ["S", "E", "C_i"],
            textposition: ["middle left", "middle right", "top right"],
            textfont: {
                size: 15,
                color: "black"
            },
            name: "Points",
            showlegend: false,
            hoverinfo: "skip"
        };

        let data = [
            trace_obstacle,
            trace_trajectory,
            trace_distance,
            trace_projection,
            trace_points
        ];

        let layout = {
            width: 620,
            height: 620,

            title: {
                text: "dist = " + dist.toFixed(2) + " ; collision = " + collision,
                font: {
                    size: 14
                },
                y: 0.96
            },

            xaxis: {
                range: [0, 50],
                scaleanchor: "y",
                scaleratio: 1,
                showgrid: true,
                gridcolor: "rgba(120,120,120,0.35)",
                griddash: "dot",
                zeroline: false
            },

            yaxis: {
                range: [0, 50],
                showgrid: true,
                gridcolor: "rgba(120,120,120,0.35)",
                griddash: "dot",
                zeroline: false
            },

            plot_bgcolor: "white",
            paper_bgcolor: "white",

            showlegend: true,

            legend: {
                x: 0.98,
                y: 0.02,
                xanchor: "right",
                yanchor: "bottom",
                bgcolor: "rgba(255,255,255,0.75)",
                bordercolor: "rgba(0,0,0,0.15)",
                borderwidth: 1,
                font: {
                    size: 12
                }
            },

            margin: {
                l: 55,
                r: 45,
                t: 60,
                b: 45
            }
        };

        let config = {
            displayModeBar: false,
            responsive: true
        };

        Plotly.react("plotly-div", data, layout, config);
    }

    function init() {
        if (typeof Plotly !== "undefined") {
            document.getElementById("sliderX").addEventListener("input", drawPlot);
            document.getElementById("sliderY").addEventListener("input", drawPlot);
            drawPlot();
        } else {
            setTimeout(init, 100);
        }
    }

    init();
    </script>
</body>
</html>
"""

iframe_html = f"""
<iframe
    srcdoc="{html.escape(html_source)}"
    style="width: 100%; height: 790px; border: none; background: transparent;"
></iframe>
"""

display(HTML(iframe_html))
```

## [MD]
### Orbiting Obstacles
#### Radial Filter

For an orbiting obstacle, let
- $C_{sun} = (50,50)$ be the center of the orbit (sun center),
- $r_{\mathrm{orb}}$ be the orbital radius,
- $r_i$ be the physical radius of the obstacle.

The obstacle center always remains on the circle $\partial B_0(C_{sun},r_{\mathrm{orb}})$. A necessary condition for collision is that the fleet segment passes close enough to this orbital circle. \
Let

$$
r_{\min} = \operatorname{dist}(C_{sun},\overline{SE})
\quad
\text{and}
\quad
r_{\max} = \max(\|S-C_{sun}\|_2,\|E-C_{sun}\|_2)
$$


The fleet segment can only intersect the obstacle's orbital corridor if

$$
r_{\min} \le r_{\mathrm{orb}}+r_i
\quad
\text{and}
\quad
r_{\max} \ge r_{\mathrm{orb}}-r_i
$$


If either condition fails, the obstacle cannot collide with the fleet and can be safely ignored.

## [CODE]
```python
import html
from IPython.display import display, HTML

html_source = r"""
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>

    <style>
        html, body {
            margin: 0;
            padding: 0;
            background: transparent;
            font-family: Arial, sans-serif;
        }

        .interactive-container {
            position: relative;
            width: 760px;
            height: 800px;
            margin: 0 auto;
            background: white;
            border: 1px solid #ddd;
            box-sizing: border-box;
        }

        .title {
            text-align: center;
            padding-top: 12px;
            margin: 0;
            color: #222;
            font-size: 18px;
        }

        .plot-layer {
            position: absolute;
            top: 45px;
            left: 45px;
            width: 660px;
            height: 660px;
            background: white;
        }

        #sliderRorb {
            position: absolute;
            top: 720px;
            left: 130px;
            width: 500px;
            margin: 0;
            cursor: pointer;
        }

        #labelRorb {
            position: absolute;
            top: 745px;
            left: 130px;
            width: 500px;
            text-align: center;
            color: #222;
        }
    </style>
</head>

<body>
    <div class="interactive-container">
        <h3 class="title">Radial Filter for Orbiting Obstacles</h3>

        <div id="plotly-div" class="plot-layer"></div>

        <input type="range" id="sliderRorb" min="0" max="50" step="1" value="35">
        <div id="labelRorb"><b>r_orb :</b> <span id="valRorb">35.0</span></div>
    </div>

    <script>
    const C_sun = [50.0, 50.0];
    const S = [40.0, 80.0];
    const E = [80.0, 70.0];
    const r_i = 6.0;

    function norm2(v) {
        return Math.hypot(v[0], v[1]);
    }

    function dot(u, v) {
        return u[0] * v[0] + u[1] * v[1];
    }

    function add(u, v) {
        return [u[0] + v[0], u[1] + v[1]];
    }

    function sub(u, v) {
        return [u[0] - v[0], u[1] - v[1]];
    }

    function mul(a, v) {
        return [a * v[0], a * v[1]];
    }

    function polarPoint(center, radius, thetaDeg) {
        let theta = thetaDeg * Math.PI / 180.0;
        return [
            center[0] + radius * Math.cos(theta),
            center[1] + radius * Math.sin(theta)
        ];
    }

    function getCircleCoords(center, radius, n=160) {
        let x = [];
        let y = [];

        for (let i = 0; i <= n; i++) {
            let theta = (i / n) * 2.0 * Math.PI;
            x.push(center[0] + radius * Math.cos(theta));
            y.push(center[1] + radius * Math.sin(theta));
        }

        return {x, y};
    }

    function getAnnulusCoords(center, rInner, rOuter, n=220) {
        let x = [];
        let y = [];

        for (let i = 0; i <= n; i++) {
            let theta = (i / n) * 2.0 * Math.PI;
            x.push(center[0] + rOuter * Math.cos(theta));
            y.push(center[1] + rOuter * Math.sin(theta));
        }

        for (let i = n; i >= 0; i--) {
            let theta = (i / n) * 2.0 * Math.PI;
            x.push(center[0] + rInner * Math.cos(theta));
            y.push(center[1] + rInner * Math.sin(theta));
        }

        return {x, y};
    }

    function computeGeometry(r_orb) {
        let vec_SE = sub(E, S);
        let vec_SC = sub(C_sun, S);

        let lambda_star = dot(vec_SC, vec_SE) / dot(vec_SE, vec_SE);
        let lambda_bar = Math.max(0.0, Math.min(1.0, lambda_star));

        let P_min = add(S, mul(lambda_bar, vec_SE));
        let r_min = norm2(sub(P_min, C_sun));

        let dist_S = norm2(sub(S, C_sun));
        let dist_E = norm2(sub(E, C_sun));

        let P_max;
        let r_max;

        if (dist_S > dist_E) {
            P_max = S;
            r_max = dist_S;
        } else {
            P_max = E;
            r_max = dist_E;
        }

        let is_possible = (r_min <= r_orb + r_i) && (r_max >= r_orb - r_i);

        return {
            P_min,
            r_min,
            P_max,
            r_max,
            is_possible
        };
    }

    function drawPlot() {
        let r_orb = parseFloat(document.getElementById("sliderRorb").value);
        document.getElementById("valRorb").innerText = r_orb.toFixed(1);

        let geom = computeGeometry(r_orb);

        let P_min = geom.P_min;
        let P_max = geom.P_max;
        let r_min = geom.r_min;
        let r_max = geom.r_max;
        let is_possible = geom.is_possible;

        let R_outer = r_orb + r_i;
        let R_inner = Math.max(0.0, r_orb - r_i);

        let corridor_fill_color = is_possible
            ? "rgba(255, 0, 0, 0.30)"
            : "rgba(0, 128, 0, 0.30)";

        let annulus = getAnnulusCoords(C_sun, R_inner, R_outer);
        let orbit = getCircleCoords(C_sun, r_orb);

        let p_inner = polarPoint(C_sun, R_inner, 240);
        let p_outer = polarPoint(C_sun, R_outer, 300);

        let mid_min = [
            (C_sun[0] + P_min[0]) / 2.0,
            (C_sun[1] + P_min[1]) / 2.0
        ];

        let mid_max = [
            (C_sun[0] + P_max[0]) / 2.0,
            (C_sun[1] + P_max[1]) / 2.0
        ];

        let mid_inner = [
            (C_sun[0] + p_inner[0]) / 2.0,
            (C_sun[1] + p_inner[1]) / 2.0
        ];

        let mid_outer = [
            (C_sun[0] + p_outer[0]) / 2.0,
            (C_sun[1] + p_outer[1]) / 2.0
        ];

        // Corridor orbital : remplissage sans contour
        let trace_corridor = {
            x: annulus.x,
            y: annulus.y,
            mode: "lines",
            fill: "toself",
            line: {
                width: 0
            },
            fillcolor: corridor_fill_color,
            name: "Orbital Corridor (r_orb ± r_i)",
            hoverinfo: "skip"
        };

        let trace_orbit = {
            x: orbit.x,
            y: orbit.y,
            mode: "lines",
            line: {
                color: "blue",
                width: 2,
                dash: "dash"
            },
            name: "Orbit (r_orb)",
            hoverinfo: "skip"
        };

        let trace_trajectory = {
            x: [S[0], E[0]],
            y: [S[1], E[1]],
            mode: "lines",
            line: {
                color: "blue",
                width: 3
            },
            name: "Trajectory SE",
            hoverinfo: "skip"
        };

        let trace_points = {
            x: [S[0], E[0], P_min[0]],
            y: [S[1], E[1], P_min[1]],
            mode: "markers+text",
            marker: {
                color: ["black", "black", "purple"],
                size: [10, 10, 10]
            },
            text: ["S", "E", ""],
            textposition: ["middle left", "middle right", "top right"],
            textfont: {
                size: 15,
                color: "black"
            },
            name: "Points",
            showlegend: false,
            hoverinfo: "skip"
        };

        // Soleil dans une trace séparée, dessinée en dernier
        let trace_sun = {
            x: [C_sun[0]],
            y: [C_sun[1]],
            mode: "markers+text",
            marker: {
                color: "orange",
                size: 14
            },
            text: ["C_sun"],
            textposition: "top left",
            textfont: {
                size: 15,
                color: "black"
            },
            name: "Sun",
            showlegend: false,
            hoverinfo: "skip"
        };

        let trace_r_min = {
            x: [C_sun[0], P_min[0]],
            y: [C_sun[1], P_min[1]],
            mode: "lines",
            line: {
                color: "black",
                width: 2
            },
            name: "r_min",
            showlegend: false,
            hoverinfo: "skip"
        };

        let trace_r_max = {
            x: [C_sun[0], P_max[0]],
            y: [C_sun[1], P_max[1]],
            mode: "lines",
            line: {
                color: "black",
                width: 2
            },
            name: "r_max",
            showlegend: false,
            hoverinfo: "skip"
        };

        let trace_r_inner = {
            x: R_inner > 0 ? [C_sun[0], p_inner[0]] : [],
            y: R_inner > 0 ? [C_sun[1], p_inner[1]] : [],
            mode: "lines",
            line: {
                color: "darkgreen",
                width: 2
            },
            name: "r_orb - r_i",
            showlegend: false,
            hoverinfo: "skip"
        };

        let trace_r_outer = {
            x: [C_sun[0], p_outer[0]],
            y: [C_sun[1], p_outer[1]],
            mode: "lines",
            line: {
                color: "darkred",
                width: 2
            },
            name: "r_orb + r_i",
            showlegend: false,
            hoverinfo: "skip"
        };

        let trace_radius_labels = {
            x: R_inner > 0
                ? [mid_min[0] - 3, mid_max[0] + 1, mid_inner[0], mid_outer[0]]
                : [mid_min[0] - 3, mid_max[0] + 1, mid_outer[0]],

            y: R_inner > 0
                ? [mid_min[1], mid_max[1], mid_inner[1] - 2, mid_outer[1] - 2]
                : [mid_min[1], mid_max[1], mid_outer[1] - 2],

            mode: "text",
            text: R_inner > 0
                ? ["r_min", "r_max", "r_orb - r_i", "r_orb + r_i"]
                : ["r_min", "r_max", "r_orb + r_i"],

            textfont: R_inner > 0
                ? {
                    size: 13,
                    color: ["black", "black", "darkgreen", "darkred"]
                }
                : {
                    size: 13,
                    color: ["black", "black", "darkred"]
                },

            showlegend: false,
            hoverinfo: "skip"
        };

        let data = [
            trace_corridor,
            trace_orbit,
            trace_trajectory,
            trace_r_min,
            trace_r_max,
            trace_r_inner,
            trace_r_outer,
            trace_radius_labels,
            trace_points,
            trace_sun   // dernier = devant les autres
        ];

        let annotations = [
            {
                x: P_min[0],
                y: P_min[1],
                ax: C_sun[0],
                ay: C_sun[1],
                xref: "x",
                yref: "y",
                axref: "x",
                ayref: "y",
                showarrow: true,
                arrowhead: 2,
                arrowside: "end+start",
                arrowwidth: 1.5,
                arrowcolor: "black",
                opacity: 1
            },
            {
                x: P_max[0],
                y: P_max[1],
                ax: C_sun[0],
                ay: C_sun[1],
                xref: "x",
                yref: "y",
                axref: "x",
                ayref: "y",
                showarrow: true,
                arrowhead: 2,
                arrowside: "end+start",
                arrowwidth: 1.5,
                arrowcolor: "black",
                opacity: 1
            },
            {
                x: p_outer[0],
                y: p_outer[1],
                ax: C_sun[0],
                ay: C_sun[1],
                xref: "x",
                yref: "y",
                axref: "x",
                ayref: "y",
                showarrow: true,
                arrowhead: 2,
                arrowside: "end+start",
                arrowwidth: 1.5,
                arrowcolor: "darkred",
                opacity: 1
            }
        ];

        if (R_inner > 0) {
            annotations.push({
                x: p_inner[0],
                y: p_inner[1],
                ax: C_sun[0],
                ay: C_sun[1],
                xref: "x",
                yref: "y",
                axref: "x",
                ayref: "y",
                showarrow: true,
                arrowhead: 2,
                arrowside: "end+start",
                arrowwidth: 1.5,
                arrowcolor: "darkgreen",
                opacity: 1
            });
        }

        let layout = {
            width: 660,
            height: 660,

            title: {
                text:
                    "r_orb = " + r_orb.toFixed(1) +
                    " ; r_min = " + r_min.toFixed(2) +
                    " ; r_max = " + r_max.toFixed(2) +
                    " ; possible = " + is_possible,
                font: {
                    size: 14
                },
                y: 0.96
            },

            xaxis: {
                range: [0, 100],
                scaleanchor: "y",
                scaleratio: 1,
                showgrid: true,
                gridcolor: "rgba(120,120,120,0.35)",
                griddash: "dot",
                zeroline: false
            },

            yaxis: {
                range: [0, 100],
                showgrid: true,
                gridcolor: "rgba(120,120,120,0.35)",
                griddash: "dot",
                zeroline: false
            },

            plot_bgcolor: "white",
            paper_bgcolor: "white",

            showlegend: true,

            legend: {
                x: 0.98,
                y: 0.02,
                xanchor: "right",
                yanchor: "bottom",
                bgcolor: "rgba(255,255,255,0.75)",
                bordercolor: "rgba(0,0,0,0.15)",
                borderwidth: 1,
                font: {
                    size: 12
                }
            },

            annotations: annotations,

            margin: {
                l: 60,
                r: 45,
                t: 70,
                b: 55
            }
        };

        let config = {
            displayModeBar: false,
            responsive: true
        };

        Plotly.react("plotly-div", data, layout, config);
    }

    function init() {
        if (typeof Plotly !== "undefined") {
            document.getElementById("sliderRorb").addEventListener("input", drawPlot);
            drawPlot();
        } else {
            setTimeout(init, 100);
        }
    }

    init();
    </script>
</body>
</html>
"""

iframe_html = f"""
<iframe
    srcdoc="{html.escape(html_source)}"
    style="width: 100%; height: 820px; border: none; background: transparent;"
></iframe>
"""

display(HTML(iframe_html))
```

## [MD]
#### Angular Filter

The radial filter only checks whether the orbit passes near the segment. However, an orbiting obstacle is not present everywhere on its orbit during the fleet travel time.\
Let

$$
\beta_S = \operatorname{atan2}(S_y - 50, S_x - 50),
\quad
\beta_E = \operatorname{atan2}(E_y - 50, E_x - 50).
$$

The fleet segment is seen from the orbit center $C_{sun}$ through the angular interval $[\beta_S,\beta_E]$. Because the obstacle has a nonzero radius $r_i$, we enlarge this interval by a margin

$$
\eta = \arcsin\left(\frac{r_i}{r_{\min}}\right),
$$

> We know $r_i > r_{\min}$ because if it is not the case, the fleet would colide with the sun.

During the time interval $[0,t]$, the obstacle only visits the angular interval $[\theta_{i,0}, \theta_{i,0} + \omega_i t]$.

A necessary condition for collision is that these two intervals overlap, i.e

$$
[\theta_{i,0}, \theta_{i,0} + \omega_i t] \cap
[\beta_S - \eta,\ \beta_E + \eta]
\neq \emptyset.
$$

If this condition is not satisfied, the obstacle cannot be in the right angular region at the right time and can be safely discarded.

## [CODE]
```python
import html
from IPython.display import display, HTML

html_source = r"""
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>

    <style>
        html, body {
            margin: 0;
            padding: 0;
            background: transparent;
            font-family: Arial, sans-serif;
        }

        .interactive-container {
            position: relative;
            width: 760px;
            height: 800px;
            margin: 0 auto;
            background: white;
            border: 1px solid #ddd;
            box-sizing: border-box;
        }

        .title {
            text-align: center;
            padding-top: 12px;
            margin: 0;
            color: #222;
            font-size: 18px;
        }

        .plot-layer {
            position: absolute;
            top: 45px;
            left: 45px;
            width: 660px;
            height: 660px;
            background: white;
        }

        #sliderTheta {
            position: absolute;
            top: 720px;
            left: 130px;
            width: 500px;
            margin: 0;
            cursor: pointer;
        }

        #labelTheta {
            position: absolute;
            top: 745px;
            left: 130px;
            width: 500px;
            text-align: center;
            color: #222;
        }
    </style>
</head>

<body>
    <div class="interactive-container">
        <h3 class="title">Angular Filter for Orbiting Obstacles</h3>

        <div id="plotly-div" class="plot-layer"></div>

        <input type="range" id="sliderTheta" min="0" max="360" step="5" value="0">
        <div id="labelTheta"><b>theta_i,0 :</b> <span id="valTheta">0.0</span>°</div>
    </div>

    <script>
    const C_sun = [50.0, 50.0];
    const S = [60.0, 80.0];
    const E = [90.0, 70.0];

    const r_i = 5.0;
    const r_orb = 30.0;
    const omega_t = 60.0;

    function deg2rad(a) {
        return a * Math.PI / 180.0;
    }

    function norm2(v) {
        return Math.hypot(v[0], v[1]);
    }

    function dot(u, v) {
        return u[0] * v[0] + u[1] * v[1];
    }

    function add(u, v) {
        return [u[0] + v[0], u[1] + v[1]];
    }

    function sub(u, v) {
        return [u[0] - v[0], u[1] - v[1]];
    }

    function mul(a, v) {
        return [a * v[0], a * v[1]];
    }

    function normalizeAngle(a) {
        a = a % 360.0;
        if (a < 0) a += 360.0;
        return a;
    }

    function inRange(ang, s, e) {
        ang = normalizeAngle(ang);
        s = normalizeAngle(s);
        e = normalizeAngle(e);

        if (s <= e) {
            return s <= ang && ang <= e;
        }

        return ang >= s || ang <= e;
    }

    function polarPoint(center, radius, thetaDeg) {
        let theta = deg2rad(thetaDeg);

        return [
            center[0] + radius * Math.cos(theta),
            center[1] + radius * Math.sin(theta)
        ];
    }

    function getCircleCoords(center, radius, n=160) {
        let x = [];
        let y = [];

        for (let i = 0; i <= n; i++) {
            let theta = 2.0 * Math.PI * i / n;
            x.push(center[0] + radius * Math.cos(theta));
            y.push(center[1] + radius * Math.sin(theta));
        }

        return {x, y};
    }

    function angularSweep(startDeg, endDeg) {
        let s = normalizeAngle(startDeg);
        let e = normalizeAngle(endDeg);

        let sweep = e - s;
        if (sweep < 0) sweep += 360.0;

        return {
            start: s,
            sweep: sweep
        };
    }

    function getSectorCoords(center, radius, startDeg, endDeg, n=140) {
        let sweepInfo = angularSweep(startDeg, endDeg);
        let s = sweepInfo.start;
        let sweep = sweepInfo.sweep;

        let x = [center[0]];
        let y = [center[1]];

        for (let i = 0; i <= n; i++) {
            let a = s + sweep * i / n;
            let p = polarPoint(center, radius, a);
            x.push(p[0]);
            y.push(p[1]);
        }

        x.push(center[0]);
        y.push(center[1]);

        return {x, y};
    }

    function getArcCoords(center, radius, startDeg, endDeg, n=50) {
        let x = [];
        let y = [];

        for (let i = 0; i <= n; i++) {
            let a = startDeg + (endDeg - startDeg) * i / n;
            let p = polarPoint(center, radius, a);
            x.push(p[0]);
            y.push(p[1]);
        }

        return {x, y};
    }

    function getAnnularSectorCoords(center, rInner, rOuter, startDeg, endDeg, n=160) {
        let sweepInfo = angularSweep(startDeg, endDeg);
        let s = sweepInfo.start;
        let sweep = sweepInfo.sweep;

        let x = [];
        let y = [];

        for (let i = 0; i <= n; i++) {
            let a = s + sweep * i / n;
            let p = polarPoint(center, rOuter, a);
            x.push(p[0]);
            y.push(p[1]);
        }

        for (let i = n; i >= 0; i--) {
            let a = s + sweep * i / n;
            let p = polarPoint(center, rInner, a);
            x.push(p[0]);
            y.push(p[1]);
        }

        x.push(x[0]);
        y.push(y[0]);

        return {x, y};
    }

    function arrowHeadOnArc(center, radius, angleDeg, direction, sizeDeg=1.2, sizeRadial=0.8) {
        /*
        Petite pointe de flèche pour un arc angulaire.
        direction = +1 : pointe dans le sens croissant des angles
        direction = -1 : pointe dans le sens décroissant des angles
        */
        let tip = polarPoint(center, radius, angleDeg);

        let back1 = polarPoint(
            center,
            radius - sizeRadial,
            angleDeg - direction * sizeDeg
        );

        let back2 = polarPoint(
            center,
            radius + sizeRadial,
            angleDeg - direction * sizeDeg
        );

        return {
            x: [back1[0], tip[0], back2[0]],
            y: [back1[1], tip[1], back2[1]]
        };
    }

    function computeGeometry(theta_i_0) {
        let vec_SE = sub(E, S);
        let vec_SC = sub(C_sun, S);

        let lambda_star = dot(vec_SC, vec_SE) / dot(vec_SE, vec_SE);
        let lambda_bar = Math.max(0.0, Math.min(1.0, lambda_star));

        let P_min = add(S, mul(lambda_bar, vec_SE));
        let r_min = norm2(sub(P_min, C_sun));

        let eta = Math.asin(r_i / r_min) * 180.0 / Math.PI;

        let beta_S = Math.atan2(S[1] - C_sun[1], S[0] - C_sun[0]) * 180.0 / Math.PI;
        let beta_E = Math.atan2(E[1] - C_sun[1], E[0] - C_sun[0]) * 180.0 / Math.PI;

        let b_min = Math.min(beta_S, beta_E);
        let b_max = Math.max(beta_S, beta_E);

        let cone_start = b_min - eta;
        let cone_end = b_max + eta;

        let path_start = theta_i_0;
        let path_end = theta_i_0 - omega_t;

        let overlap =
            inRange(path_start, cone_start, cone_end) ||
            inRange(path_end, cone_start, cone_end) ||
            inRange(cone_start, path_end, path_start) ||
            inRange(cone_end, path_end, path_start);

        return {
            P_min,
            r_min,
            eta,
            beta_S,
            beta_E,
            b_min,
            b_max,
            cone_start,
            cone_end,
            path_start,
            path_end,
            overlap
        };
    }

    function drawPlot() {
        let theta_i_0 = parseFloat(document.getElementById("sliderTheta").value);
        document.getElementById("valTheta").innerText = theta_i_0.toFixed(1);

        let geom = computeGeometry(theta_i_0);

        let eta = geom.eta;
        let b_min = geom.b_min;
        let b_max = geom.b_max;
        let cone_start = geom.cone_start;
        let cone_end = geom.cone_end;
        let path_start = geom.path_start;
        let path_end = geom.path_end;
        let overlap = geom.overlap;

        let path_color = overlap
            ? "rgba(255, 0, 0, 0.40)"
            : "rgba(0, 128, 0, 0.40)";

        let cone = getSectorCoords(C_sun, 70.0, cone_start, cone_end);
        let orbit = getCircleCoords(C_sun, r_orb);
        let path = getAnnularSectorCoords(C_sun, r_orb - r_i, r_orb + r_i, path_end, path_start);

        let planet_now = polarPoint(C_sun, r_orb, path_start);
        let planet_future = polarPoint(C_sun, r_orb, path_end);

        let planet_now_circle = getCircleCoords(planet_now, r_i);
        let planet_future_circle = getCircleCoords(planet_future, r_i);

        let p_bmin = polarPoint(C_sun, 70.0, b_min);
        let p_bmax = polarPoint(C_sun, 70.0, b_max);
        let p_cstart = polarPoint(C_sun, 70.0, cone_start);
        let p_cend = polarPoint(C_sun, 70.0, cone_end);

        let R_eta = 40.0;

        /*
        Correction importante :
        - eta gauche : arc de cone_start vers b_min
        - eta droite : arc de b_max vers cone_end
        Ces arcs sont sur le même rayon R_eta que les extrémités, donc ils touchent les lignes grises/cyan.
        */
        let eta_arc_left = getArcCoords(C_sun, R_eta, cone_start, b_min, 40);
        let eta_arc_right = getArcCoords(C_sun, R_eta, b_max, cone_end, 40);

        let eta_left_head_1 = arrowHeadOnArc(C_sun, R_eta, cone_start, -1);
        let eta_left_head_2 = arrowHeadOnArc(C_sun, R_eta, b_min, +1);

        let eta_right_head_1 = arrowHeadOnArc(C_sun, R_eta, b_max, -1);
        let eta_right_head_2 = arrowHeadOnArc(C_sun, R_eta, cone_end, +1);

        let mid_eta1 = b_min - eta / 2.0;
        let mid_eta2 = b_max + eta / 2.0;
        let mid_cone_angle = (cone_start + cone_end) / 2.0;
        let mid_path_angle = (path_start + path_end) / 2.0;

        let eta_label_1 = polarPoint(C_sun, R_eta + 4.0, mid_eta1);
        let eta_label_2 = polarPoint(C_sun, R_eta + 4.0, mid_eta2);
        let cone_label = polarPoint(C_sun, 45.0, mid_cone_angle);
        let path_label = polarPoint(C_sun, 20.0, mid_path_angle);

        let arrow_arc = getArcCoords(C_sun, r_orb, path_start - 15.0, path_start, 25);
        let arrow_start = polarPoint(C_sun, r_orb, path_start - 15.0);
        let arrow_end = polarPoint(C_sun, r_orb, path_start - 10.0);

        let trace_cone = {
            x: cone.x,
            y: cone.y,
            mode: "lines",
            fill: "toself",
            line: {
                width: 0
            },
            fillcolor: "rgba(0, 255, 255, 0.15)",
            showlegend: false,
            hoverinfo: "skip"
        };

        let trace_orbit = {
            x: orbit.x,
            y: orbit.y,
            mode: "lines",
            line: {
                color: "blue",
                width: 2,
                dash: "dash"
            },
            showlegend: false,
            hoverinfo: "skip"
        };

        let trace_path = {
            x: path.x,
            y: path.y,
            mode: "lines",
            fill: "toself",
            line: {
                width: 0
            },
            fillcolor: path_color,
            showlegend: false,
            hoverinfo: "skip"
        };

        let trace_planet_now = {
            x: planet_now_circle.x,
            y: planet_now_circle.y,
            mode: "lines",
            fill: "toself",
            line: {
                width: 0
            },
            fillcolor: "rgba(128,128,128,0.80)",
            showlegend: false,
            hoverinfo: "skip"
        };

        let trace_planet_future = {
            x: planet_future_circle.x,
            y: planet_future_circle.y,
            mode: "lines",
            fill: "none",
            line: {
                color: "gray",
                width: 2,
                dash: "dash"
            },
            showlegend: false,
            hoverinfo: "skip"
        };

        let trace_arrow_arc = {
            x: arrow_arc.x,
            y: arrow_arc.y,
            mode: "lines",
            line: {
                color: "black",
                width: 2
            },
            showlegend: false,
            hoverinfo: "skip"
        };

        let trace_trajectory = {
            x: [S[0], E[0]],
            y: [S[1], E[1]],
            mode: "lines",
            line: {
                color: "blue",
                width: 3
            },
            showlegend: false,
            hoverinfo: "skip"
        };

        let trace_beta_lines = {
            x: [C_sun[0], p_bmin[0], null, C_sun[0], p_bmax[0]],
            y: [C_sun[1], p_bmin[1], null, C_sun[1], p_bmax[1]],
            mode: "lines",
            line: {
                color: "gray",
                width: 2,
                dash: "dash"
            },
            showlegend: false,
            hoverinfo: "skip"
        };

        let trace_cone_lines = {
            x: [C_sun[0], p_cstart[0], null, C_sun[0], p_cend[0]],
            y: [C_sun[1], p_cstart[1], null, C_sun[1], p_cend[1]],
            mode: "lines",
            line: {
                color: "cyan",
                width: 2,
                dash: "dash"
            },
            showlegend: false,
            hoverinfo: "skip"
        };

        let trace_eta_arcs = {
            x: [
                ...eta_arc_left.x,
                null,
                ...eta_arc_right.x
            ],
            y: [
                ...eta_arc_left.y,
                null,
                ...eta_arc_right.y
            ],
            mode: "lines",
            line: {
                color: "teal",
                width: 2
            },
            showlegend: false,
            hoverinfo: "skip"
        };

        let trace_eta_arrowheads = {
            x: [
                ...eta_left_head_1.x,
                null,
                ...eta_left_head_2.x,
                null,
                ...eta_right_head_1.x,
                null,
                ...eta_right_head_2.x
            ],
            y: [
                ...eta_left_head_1.y,
                null,
                ...eta_left_head_2.y,
                null,
                ...eta_right_head_1.y,
                null,
                ...eta_right_head_2.y
            ],
            mode: "lines",
            line: {
                color: "teal",
                width: 2
            },
            showlegend: false,
            hoverinfo: "skip"
        };

        let trace_points = {
            x: [S[0], E[0]],
            y: [S[1], E[1]],
            mode: "markers+text",
            marker: {
                color: "black",
                size: 10
            },
            text: ["S", "E"],
            textposition: ["middle left", "middle right"],
            textfont: {
                size: 15,
                color: "black"
            },
            showlegend: false,
            hoverinfo: "skip"
        };

        let trace_sun = {
            x: [C_sun[0]],
            y: [C_sun[1]],
            mode: "markers+text",
            marker: {
                color: "orange",
                size: 16
            },
            text: ["C_sun"],
            textposition: "bottom left",
            textfont: {
                size: 15,
                color: "black"
            },
            showlegend: false,
            hoverinfo: "skip"
        };

        let trace_text_labels = {
            x: [
                eta_label_1[0],
                eta_label_2[0],
                cone_label[0],
                path_label[0]
            ],
            y: [
                eta_label_1[1],
                eta_label_2[1],
                cone_label[1],
                path_label[1]
            ],
            mode: "text",
            text: [
                "η",
                "η",
                "[β_S - η, β_E + η]",
                "[θ_i,0, θ_i,0 - ω_i t]"
            ],
            textfont: {
                size: [14, 14, 13, 13],
                color: ["teal", "teal", "teal", "maroon"]
            },
            showlegend: false,
            hoverinfo: "skip"
        };

        let data = [
            trace_cone,
            trace_orbit,
            trace_path,
            trace_planet_now,
            trace_planet_future,
            trace_arrow_arc,
            trace_beta_lines,
            trace_cone_lines,
            trace_eta_arcs,
            trace_eta_arrowheads,
            trace_trajectory,
            trace_text_labels,
            trace_points,
            trace_sun
        ];

        let annotations = [
            {
                x: arrow_start[0],
                y: arrow_start[1],
                ax: arrow_end[0],
                ay: arrow_end[1],
                xref: "x",
                yref: "y",
                axref: "x",
                ayref: "y",
                showarrow: true,
                arrowhead: 2,
                arrowwidth: 1.5,
                arrowcolor: "black"
            }
        ];

        let layout = {
            width: 660,
            height: 660,

            title: {
                text:
                    "theta_i,0 = " + theta_i_0.toFixed(1) +
                    "° ; eta = " + eta.toFixed(2) +
                    "° ; overlap = " + overlap,
                font: {
                    size: 14
                },
                y: 0.96
            },

            xaxis: {
                range: [0, 100],
                scaleanchor: "y",
                scaleratio: 1,
                showgrid: true,
                gridcolor: "rgba(120,120,120,0.35)",
                griddash: "dot",
                zeroline: false
            },

            yaxis: {
                range: [0, 100],
                showgrid: true,
                gridcolor: "rgba(120,120,120,0.35)",
                griddash: "dot",
                zeroline: false
            },

            plot_bgcolor: "white",
            paper_bgcolor: "white",

            showlegend: false,

            annotations: annotations,

            margin: {
                l: 60,
                r: 45,
                t: 70,
                b: 55
            }
        };

        let config = {
            displayModeBar: false,
            responsive: true
        };

        Plotly.react("plotly-div", data, layout, config);
    }

    function init() {
        if (typeof Plotly !== "undefined") {
            document.getElementById("sliderTheta").addEventListener("input", drawPlot);
            drawPlot();
        } else {
            setTimeout(init, 100);
        }
    }

    init();
    </script>
</body>
</html>
"""

iframe_html = f"""
<iframe
    srcdoc="{html.escape(html_source)}"
    style="width: 100%; height: 820px; border: none; background: transparent;"
></iframe>
"""

display(HTML(iframe_html))
```

## [MD]
### Filter Pipeline

The collision check can therefore be organized as follows:

$$
\text{candidate trajectory}
\rightarrow
\text{static exact test / radial filter}
\rightarrow
\text{angular filter}
\rightarrow
\text{time-dependent collision test}.
$$

Only obstacles that pass the cheap filters are tested with the full condition

$$
\min_{0<s<t}
\|F_\alpha(s)-C_i(s)\|_2
\le r_i.
$$

This reduces the effective dimension of the collision problem: instead of testing every obstacle dynamically over time, we first reduce the set of relevant obstacles using constant-time geometric conditions.

## [MD]
# PathFinder Class

## [CODE]
```python
import numpy as np

SUN_CENTER = np.array([50.0, 50.0])
SUN_RADIUS = 10.0
BOARD_DIAGONAL = 100.0 * np.sqrt(2)
MAX_STEPS = 500
LAUNCH_OFFSET = 0.1 # Pas dans le README, mais le moteur ne lance pas les vaisseaux de la surface des planètes mais de juste à côté.

class PathFinder:
    def __init__(self, obs):
        self.static_obstacles = []
        self.orbiting_obstacles = []
        self.comets = []

        self.margin = 0.05

        self._parse_environment(obs)

    def _parse_environment(self, obs):
        """
        Analyse les observations pour catégoriser les obstacles (planètes statiques,
        planètes en orbite, comètes) et extraire leurs paramètres (centre, rayon, orbite).
        """
        planets = obs.get("planets", [])
        comets_data = obs.get("comets", [])
        self.angular_velocity = obs.get("angular_velocity", 0.0)

        comet_lookup = {}
        for group in comets_data:
            path_index = group["path_index"]
            for c_id, path in zip(group["planet_ids"], group["paths"]):
                comet_lookup[c_id] = {
                    "path": path,
                    "path_index": path_index
                }

        for p in planets:
            p_id, owner, x, y, radius, ships, production = p
            pos = np.array([x, y])

            obstacle = {
                "id": p_id,
                "pos": pos,
                "radius": radius
            }

            if p_id in comet_lookup:
                obstacle["path"] = comet_lookup[p_id]["path"]
                obstacle["path_index"] = comet_lookup[p_id]["path_index"]
                self.comets.append(obstacle)

            else:
                orbital_radius = np.linalg.norm(pos - SUN_CENTER)

                if orbital_radius + radius < 50.0:
                    obstacle["orbital_radius"] = orbital_radius
                    obstacle["current_angle"] = np.atan2(pos[1] - SUN_CENTER[1], pos[0] - SUN_CENTER[0])
                    self.orbiting_obstacles.append(obstacle)
                else:
                    self.static_obstacles.append(obstacle)

        self.static_obstacles.append({
            "id": "SUN",
            "pos": SUN_CENTER,
            "radius": SUN_RADIUS
        })

    def get_launch_angle(self, source_planet, target_planet, speed, delta_t=0.1):
        """
        Méthode publique principale. Cherche le premier angle de lancement valide
        pour atteindre la cible depuis la source à une vitesse donnée.
        """
        t_max = BOARD_DIAGONAL / speed

        current_t = delta_t
        while current_t <= t_max:
            if self._is_feasible_time(source_planet, target_planet, speed, current_t):
                angles = self._compute_admissible_angles(source_planet, target_planet, speed, current_t)

                if angles is not None:
                    phi, delta = angles
                    safe_delta = 0.9 * delta
                    offsets = np.linspace(-safe_delta, safe_delta, 5)
                    angles_to_test = [phi + offset for offset in sorted(offsets, key=abs)]

                    for alpha in angles_to_test:
                        if self._is_collision_free(source_planet, target_planet, alpha, speed, current_t):
                            return alpha

            current_t += delta_t

        return None

    def _get_position_at_time(self, obstacle, t):
        """
        Prédit la position du centre d'un obstacle au temps t.
        """
        if "orbital_radius" in obstacle:
            angle_t = obstacle["current_angle"] + (self.angular_velocity * t)
            x = SUN_CENTER[0] + obstacle["orbital_radius"] * np.cos(angle_t)
            y = SUN_CENTER[1] + obstacle["orbital_radius"] * np.sin(angle_t)
            return np.array([x, y])

        elif "path" in obstacle:
            future_index = obstacle["path_index"] + int(t)

            if future_index < len(obstacle["path"]):
                return np.array(obstacle["path"][future_index])
            else:
                # hors carte
                return np.array([-1000.0, -1000.0])

        return obstacle["pos"]

    def _is_feasible_time(self, source, target, speed, t):
        """
        Vérifie la condition scalaire : |d(t) - r_A - v*t| <= r_B
        """
        A = source["pos"]
        r_A = source["radius"]

        B_t = self._get_position_at_time(target, t)
        r_B = target["radius"]

        d_t = np.linalg.norm(B_t - A)
        r_t = r_A + LAUNCH_OFFSET + speed * t

        return abs(d_t - r_t) <= r_B

    def _compute_admissible_angles(self, source, target, speed, t):
        """
        Calcule la direction de base (phi) et la demi-largeur (delta).
        Retourne un tuple (phi, delta) ou None.
        """
        A = source["pos"]
        r_A = source["radius"]

        B_t = self._get_position_at_time(target, t)
        r_B = target["radius"]

        d_star = np.linalg.norm(B_t - A)
        r_star = r_A + LAUNCH_OFFSET + speed * t

        if d_star == 0 or r_star == 0:
            return None

        cos_val = (d_star**2 + r_star**2 - r_B**2) / (2 * d_star * r_star)

        # Clamping pour éviter les erreurs de précision flottante
        cos_val = max(-1.0, min(1.0, cos_val))
        delta = np.acos(cos_val)

        phi = np.atan2(B_t[1] - A[1], B_t[0] - A[0])

        return phi, delta

    def _is_collision_free(self, source, target, alpha, speed, t):
        """
        Exécute le pipeline de filtrage complet pour un angle et un temps donnés.
        """
        A = source["pos"]
        r_A = source["radius"]

        direction = np.array([np.cos(alpha), np.sin(alpha)])

        S = A + (r_A + LAUNCH_OFFSET) * direction
        E = S + speed * t * direction

        static_obstacles = [
            obs for obs in self.static_obstacles
            if obs["id"] not in {source["id"], target["id"]}
        ]

        orbiting_obstacles = [
            obs for obs in self.orbiting_obstacles
            if obs["id"] not in {source["id"], target["id"]}
        ]

        comets = [
            obs for obs in self.comets
            if obs["id"] not in {source["id"], target["id"]}
        ]

        candidates = self._filter_static_obstacles(S, E, static_obstacles)
        if candidates: return False

        candidates += self._filter_orbiting_obstacles(S, E, t, orbiting_obstacles) + \
                      comets

        if not candidates: return True

        return self._check_exact_collision(S, alpha, speed, t, candidates)

    def _filter_static_obstacles(self, S, E, obstacles):
        """
        Élimine les obstacles statiques trop éloignés du segment SE.
        """

        vec_SE = E - S
        norm_SE_squared = np.dot(vec_SE, vec_SE)

        for obs in obstacles:
            C_i = obs["pos"]
            r_i = obs["radius"]

            vec_SCi = C_i - S
            lambda_star = np.dot(vec_SCi, vec_SE) / norm_SE_squared
            lambda_bar = max(0.0, min(1.0, lambda_star))
            P_star = S + lambda_bar * vec_SE

            dist = np.linalg.norm(P_star - C_i)

            if dist <= r_i + self.margin:
                return [obs]

        return []

    def _filter_orbiting_obstacles(self, S, E, t, obstacles):
        """
        Élimine les obstacles orbitaux qui ne passe pas les filtres.
        """
        filtered = self._filter_orbiting_radial(S, E, obstacles)
        if not filtered: return []

        filtered = self._filter_orbiting_angular(S, E, t, filtered)
        return filtered

    def _filter_orbiting_radial(self, S, E, obstacles):
        """
        Élimine les obstacles orbitaux dont l'orbite ne croise pas le segment SE.
        """
        filtered = []

        vec_SE = E - S
        norm_SE_squared = np.dot(vec_SE, vec_SE)

        vec_SCsun = SUN_CENTER - S
        lambda_star = np.dot(vec_SCsun, vec_SE) / norm_SE_squared
        lambda_bar = max(0.0, min(1.0, lambda_star))
        P_star = S + lambda_bar * vec_SE

        r_min = np.linalg.norm(P_star - SUN_CENTER)
        r_max = max(np.linalg.norm(S - SUN_CENTER), np.linalg.norm(E - SUN_CENTER))

        for obs in obstacles:
            r_orb = obs["orbital_radius"]
            r_i = obs["radius"]

            if r_min <= r_orb + r_i + self.margin and r_max >= r_orb - r_i - self.margin:
                filtered.append(obs)

        return filtered

    def _filter_orbiting_angular(self, S, E, t, obstacles):
        """
        Élimine les obstacles orbitaux qui ne seront pas dans le bon secteur angulaire.
        """

        def angular_intervals_overlap(A, B, C, D):
            """
            Vérifie si l'intervalle [A, B] chevauche l'intervalle [C, D] modulo 2*pi.
            """
            if C > D:
                C, D = D, C

            hw1 = (B - A) / 2.0
            hw2 = (D - C) / 2.0

            if hw1 + hw2 >= np.pi:
                return True

            mid1 = (A + B) / 2.0
            mid2 = (C + D) / 2.0

            dist = abs((mid1 - mid2 + np.pi) % (2 * np.pi) - np.pi)

            return dist <= (hw1 + hw2)

        filtered = []

        beta_S = np.atan2(S[1] - SUN_CENTER[1], S[0] - SUN_CENTER[0])
        beta_E = np.atan2(E[1] - SUN_CENTER[1], E[0] - SUN_CENTER[0])

        diff = (beta_E - beta_S + np.pi) % (2 * np.pi) - np.pi
        beta_min, beta_max = min(beta_S, beta_S + diff), max(beta_S, beta_S + diff)

        vec_SE = E - S
        norm_SE_squared = np.dot(vec_SE, vec_SE)

        vec_SCsun = SUN_CENTER - S
        lambda_star = np.dot(vec_SCsun, vec_SE) / norm_SE_squared
        P_min = S + max(0.0, min(1.0, lambda_star)) * vec_SE
        r_min = np.linalg.norm(P_min - SUN_CENTER)

        for obs in obstacles:
            r_i = obs["radius"]

            safe_ratio = min(1.0, r_i / r_min) if r_min > 0 else 1.0
            eta = np.asin(safe_ratio)

            cone_start = beta_min - eta
            cone_end = beta_max + eta

            theta_start = obs["current_angle"]
            theta_end = theta_start + self.angular_velocity * t

            if angular_intervals_overlap(cone_start, cone_end, theta_start, theta_end):
                filtered.append(obs)

        return filtered

    def _check_exact_collision(self, S, alpha, speed, t, filtered_obstacles):
        """
        Test dynamique selon l'ordre réel du moteur Orbit Wars.
        fleet movement puis planet rotation...
        Retourne True s'il n'y a PAS de collision, False sinon.
        """
        direction = np.array([np.cos(alpha), np.sin(alpha)])

        s = 0.0
        while s < t:
            next_s = min(s + 1.0, t)

            F_start = S + speed * s * direction
            F_end = S + speed * next_s * direction

            fleet_segment = F_end - F_start
            fleet_segment_norm_sq = np.dot(fleet_segment, fleet_segment)

            for obs in filtered_obstacles:
                r_i = obs["radius"]

                O_start = self._get_position_at_time(obs, s)
                O_end = self._get_position_at_time(obs, next_s)

                # La flotte avance, l'obstacle est fixe à sa position du début du tour.
                if fleet_segment_norm_sq < 1e-9:
                    dist = np.linalg.norm(F_start - O_start)
                else:
                    lambda_star = np.dot(O_start - F_start, fleet_segment) / fleet_segment_norm_sq
                    lambda_bar = max(0.0, min(1.0, lambda_star))
                    P_star = F_start + lambda_bar * fleet_segment
                    dist = np.linalg.norm(P_star - O_start)

                if dist <= r_i + self.margin:
                    return False

                # L'obstacle bouge, la flotte est fixe à sa position de fin de tour.
                obstacle_segment = O_end - O_start
                obstacle_segment_norm_sq = np.dot(obstacle_segment, obstacle_segment)

                if obstacle_segment_norm_sq < 1e-9:
                    dist = np.linalg.norm(F_end - O_start)
                else:
                    lambda_star = np.dot(F_end - O_start, obstacle_segment) / obstacle_segment_norm_sq
                    lambda_bar = max(0.0, min(1.0, lambda_star))
                    P_star = O_start + lambda_bar * obstacle_segment
                    dist = np.linalg.norm(P_star - F_end)

                if dist <= r_i + self.margin:
                    return False

            s = next_s

        return True
```

## [MD]
# Tests
## Env setup

## [CODE]
```python
%%capture
!pip install --upgrade "kaggle-environments>=1.28.0"
```

## [CODE]
```python
from kaggle_environments import make

env = make("orbit_wars", debug=True)
print(f"Environment: {env.name} v{env.version}")
print(f"Players: {env.specification.agents}")
print(f"Max steps: {env.configuration.episodeSteps}")
```

## [CODE]
```python
def dummy_agent(obs):
    """Adversaire inactif pour ne pas polluer les tests visuels."""
    return []
```

## [MD]
## Test A: Static to Static

In this test, the agent must invade a static group of planets and cycle through them. The goal is to evaluate the algorithm's capacity to **send fleets from a static planet to another static planet** through a moving environment.
> We set the number of ships per fleet to one for simplicity.

## [CODE]
```python
STATIC_CHAIN_GROUP = None
STATIC_CHAIN_ENTRY = None
STATIC_ENTRY_DONE = False

STATIC_ENTRY_MIN_SHIPS = 40
STATIC_ENTRY_SEND_RATIO = 0.75
STATIC_CYCLE_MIN_SHIPS = 2

def ordered_group_ids(group_ids, all_objects_dict):
    return sorted(
        group_ids,
        key=lambda pid: np.atan2(
            all_objects_dict[pid]["pos"][1] - SUN_CENTER[1],
            all_objects_dict[pid]["pos"][0] - SUN_CENTER[0],
        )
    )

def is_static_obj(obj):
    return (
        obj["id"] != "SUN"
        and "orbital_radius" not in obj
        and "path" not in obj
    )

def is_orbiting_obj(obj):
    return "orbital_radius" in obj and "path" not in obj

def fleet_speed(ships, max_speed=6.0):
    ships = max(1, int(ships))
    return 1.0 + (max_speed - 1.0) * (np.log(ships) / np.log(1000)) ** 1.5




def choose_reachable_static_group_from_source(obs, pf, all_objects_dict, source_id):
    planets = obs["planets"]
    owners_by_id = {p[0]: p[1] for p in planets}

    if source_id not in all_objects_dict:
        return None

    source_obj = all_objects_dict[source_id]
    max_id = max(p[0] for p in planets)

    candidates = []

    for base in range(0, max_id + 1, 4):
        group_ids = [base, base + 1, base + 2, base + 3]

        if not all(pid in all_objects_dict for pid in group_ids):
            continue

        if not all(is_static_obj(all_objects_dict[pid]) for pid in group_ids):
            continue

        if all(owners_by_id.get(pid) == obs["player"] for pid in group_ids):
            continue

        ordered_group = ordered_group_ids(group_ids, all_objects_dict)

        reachable_count = 0
        min_dist = float("inf")

        for target_id in ordered_group:
            target_obj = all_objects_dict[target_id]

            angle = pf.get_launch_angle(
                source_obj,
                target_obj,
                speed=1.0,
                delta_t=1.0,
            )

            if angle is not None:
                reachable_count += 1
                min_dist = min(
                    min_dist,
                    np.linalg.norm(target_obj["pos"] - source_obj["pos"]),
                )

        if reachable_count > 0:
            candidates.append((reachable_count, min_dist, ordered_group))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (-x[0], x[1]))
    return candidates[0][2]

def choose_reachable_static_group(obs, pf, all_objects_dict):
    player = obs["player"]
    planets = obs["planets"]

    my_planets = [
        p for p in planets
        if p[1] == player and p[5] >= 2
    ]

    if not my_planets:
        return None, None

    candidates = []

    for source_planet in my_planets:
        source_id = source_planet[0]

        group = choose_reachable_static_group_from_source(
            obs,
            pf,
            all_objects_dict,
            source_id,
        )

        if group is None:
            continue

        source_obj = all_objects_dict[source_id]

        for target_id in group:
            target_obj = all_objects_dict[target_id]

            angle = pf.get_launch_angle(
                source_obj,
                target_obj,
                speed=1.0,
                delta_t=1.0,
            )

            if angle is not None:
                dist = np.linalg.norm(target_obj["pos"] - source_obj["pos"])

                candidates.append({
                    "dist": dist,
                    "group": group,
                    "source_id": source_id,
                    "target_id": target_id,
                    "angle": angle,
                })

    if not candidates:
        return None, None

    candidates.sort(key=lambda c: c["dist"])
    best = candidates[0]

    entry = {
        "source_id": best["source_id"],
        "target_id": best["target_id"],
        "angle": best["angle"],
    }

    return best["group"], entry

def static_to_static_agent(obs):
    global STATIC_CHAIN_GROUP, STATIC_CHAIN_ENTRY, STATIC_ENTRY_DONE

    moves = []
    player = obs["player"]
    planets = obs["planets"]

    pf = PathFinder(obs)

    all_objects_dict = {
        obj["id"]: obj
        for obj in pf.static_obstacles + pf.orbiting_obstacles + pf.comets
    }

    owners_by_id = {p[0]: p[1] for p in planets}
    ships_by_id = {p[0]: p[5] for p in planets}

    if STATIC_CHAIN_GROUP is None:
        group, entry = choose_reachable_static_group(obs, pf, all_objects_dict)

        if group is None:
            return []

        STATIC_CHAIN_GROUP = group
        STATIC_CHAIN_ENTRY = entry
        STATIC_ENTRY_DONE = False

    group = [
        pid for pid in STATIC_CHAIN_GROUP
        if pid in all_objects_dict
    ]

    if len(group) < 4:
        return []

    owned_in_group_any = [
        pid for pid in group
        if owners_by_id.get(pid) == player
    ]

    owned_in_group_ready = [
        pid for pid in group
        if owners_by_id.get(pid) == player
        and ships_by_id.get(pid, 0) >= STATIC_CYCLE_MIN_SHIPS
    ]

    if STATIC_CHAIN_ENTRY["target_id"] in owned_in_group_any:
        STATIC_ENTRY_DONE = True

    if not STATIC_ENTRY_DONE:
        source_id = STATIC_CHAIN_ENTRY["source_id"]
        target_id = STATIC_CHAIN_ENTRY["target_id"]

        if source_id not in all_objects_dict or target_id not in all_objects_dict:
            return []

        if owners_by_id.get(source_id) != player:
            return []

        source_ships = ships_by_id.get(source_id, 0)

        if source_ships < STATIC_ENTRY_MIN_SHIPS:
            return []

        ships_to_send = max(1, int(source_ships * STATIC_ENTRY_SEND_RATIO))
        speed = fleet_speed(ships_to_send)

        angle = pf.get_launch_angle(
            all_objects_dict[source_id],
            all_objects_dict[target_id],
            speed=speed,
            delta_t=1.0,
        )

        if angle is not None:
            moves.append([source_id, angle, ships_to_send])

        return moves

    for source_id in owned_in_group_ready:
        source_index = group.index(source_id)

        neighbor_ids = [
            group[(source_index + 1) % len(group)],
            group[(source_index - 1) % len(group)],
        ]

        source_obj = all_objects_dict[source_id]

        for target_id in neighbor_ids:
            if target_id not in all_objects_dict:
                continue

            target_obj = all_objects_dict[target_id]

            angle = pf.get_launch_angle(
                source_obj,
                target_obj,
                speed=1.0,
                delta_t=1.0,
            )

            if angle is not None:
                moves.append([source_id, angle, 1])

    return moves
```

## [CODE]
```python
from kaggle_environments import make
import os
import random
import numpy as np


STATIC_CHAIN_GROUP = None
STATIC_CHAIN_ENTRY = None
STATIC_ENTRY_DONE = False

SEED = 42

env = make("orbit_wars", configuration={"episodeSteps": 300} , debug=True)
print("Starting test : Static to Static...")

random.seed(SEED)
np.random.seed(SEED)

env.run([static_to_static_agent, dummy_agent])
env.render(mode="ipython", width=800, height=600)

# html_output = env.render(mode="html", width=800, height=600)
# with open("test_static_to_static.html", "w", encoding="utf-8") as f:
#     f.write(html_output)

# print("Fichier test_static_to_static.html généré dans /kaggle/working/ !")
```

## [MD]
## Test B: Static to Dynamic
In this test, the agent has to continuously send fleets to the planets of an orbiting group. The goal is to evaluate the algorithm's capacity to **send fleets from a static planet to a dynamic planet** through a moving environment.
> We set the number of ships per fleet to one for simplicity.

## [CODE]
```python
DYNAMIC_SOURCE_ID = None
DYNAMIC_TARGET_GROUP = None

def is_orbiting_obj(obj):
    return "orbital_radius" in obj and "path" not in obj

def fleet_speed(ships, max_speed=6.0):
    ships = max(1, int(ships))
    return 1.0 + (max_speed - 1.0) * (np.log(ships) / np.log(1000)) ** 1.5

def choose_one_reachable_orbiting_group(obs, pf, all_objects_dict, source_id):
    planets = obs["planets"]
    player = obs["player"]
    owners_by_id = {p[0]: p[1] for p in planets}

    source_obj = all_objects_dict[source_id]
    max_id = max(p[0] for p in planets)

    candidates = []

    for base in range(0, max_id + 1, 4):
        group_ids = [base, base + 1, base + 2, base + 3]

        if not all(pid in all_objects_dict for pid in group_ids):
            continue

        if not all(is_orbiting_obj(all_objects_dict[pid]) for pid in group_ids):
            continue

        # Ne pas choisir un groupe déjà possédé par moi.
        if any(owners_by_id.get(pid) == player for pid in group_ids):
            continue

        reachable_targets = []

        for target_id in group_ids:
            target_obj = all_objects_dict[target_id]

            angle = pf.get_launch_angle(
                source_obj,
                target_obj,
                speed=1.0,
                delta_t=1.0,
            )

            if angle is not None:
                dist = np.linalg.norm(target_obj["pos"] - source_obj["pos"])
                reachable_targets.append((dist, target_id))

        if reachable_targets:
            candidates.append((min(d for d, _ in reachable_targets), group_ids))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]

def static_to_dynamic_agent(obs):
    global DYNAMIC_SOURCE_ID, DYNAMIC_TARGET_GROUP

    moves = []
    player = obs["player"]
    planets = obs["planets"]

    pf = PathFinder(obs)

    all_objects_dict = {
        obj["id"]: obj
        for obj in pf.static_obstacles + pf.orbiting_obstacles + pf.comets
    }

    owners_by_id = {p[0]: p[1] for p in planets}
    ships_by_id = {p[0]: p[5] for p in planets}

    # Initialisation UNE SEULE FOIS.
    if DYNAMIC_SOURCE_ID is None:
        my_planets = [
            p for p in planets
            if p[1] == player and p[5] >= 2
        ]

        if not my_planets:
            return []

        # Source fixe : ta planète de départ.
        DYNAMIC_SOURCE_ID = my_planets[0][0]

    if DYNAMIC_TARGET_GROUP is None:
        group = choose_one_reachable_orbiting_group(
            obs,
            pf,
            all_objects_dict,
            DYNAMIC_SOURCE_ID,
        )

        if group is None:
            return []

        DYNAMIC_TARGET_GROUP = group

    # Si la source n'est plus disponible, on arrête le test.
    if DYNAMIC_SOURCE_ID not in all_objects_dict:
        return []

    if owners_by_id.get(DYNAMIC_SOURCE_ID) != player:
        return []

    if ships_by_id.get(DYNAMIC_SOURCE_ID, 0) < 2:
        return []

    source_obj = all_objects_dict[DYNAMIC_SOURCE_ID]

    # Tire uniquement vers CE groupe-là.
    for target_id in DYNAMIC_TARGET_GROUP:
        if target_id not in all_objects_dict:
            continue

        target_obj = all_objects_dict[target_id]

        angle = pf.get_launch_angle(
            source_obj,
            target_obj,
            speed=1.0,
            delta_t=1.0,
        )

        if angle is not None:
            moves.append([DYNAMIC_SOURCE_ID, angle, 1])

    return moves
```

## [CODE]
```python
from kaggle_environments import make
import os
import random
import numpy as np

SEED = 42
DYNAMIC_SOURCE_ID = None
DYNAMIC_TARGET_GROUP = None

env = make("orbit_wars", configuration={"episodeSteps": 300} , debug=True)
print("Starting test : Static to Dynamic...")

random.seed(SEED)
np.random.seed(SEED)

env.run([static_to_dynamic_agent, dummy_agent])
env.render(mode="ipython", width=800, height=600)

# html_output = env.render(mode="html", width=800, height=600)
# with open("test_static_to_dynamic.html", "w", encoding="utf-8") as f:
#     f.write(html_output)

# print("Fichier test_static_to_dynamic.html généré dans /kaggle/working/ !")
```

## [MD]
## Test C: Dynamic to Dynamic
In this test, the agent must invade a dynamic group of planets and cycle through them. The goal is to evaluate the algorithm's capacity to **send fleets from a dynamic planet to another dynamic planet** through a moving environment.
> We set the number of ships per fleet to one for simplicity.

## [CODE]
```python
DYNAMIC_SOURCE_ID = None
DYNAMIC_TARGET_GROUP = None
DYNAMIC_ENTRY_TARGET_ID = None
DYNAMIC_ENTRY_DONE = False

ENTRY_MIN_SHIPS = 40
ENTRY_SEND_RATIO = 0.75
CYCLE_MIN_SHIPS = 2

def choose_one_reachable_orbiting_group(obs, pf, all_objects_dict, source_id):
    planets = obs["planets"]
    player = obs["player"]
    owners_by_id = {p[0]: p[1] for p in planets}

    if source_id not in all_objects_dict:
        return None

    source_obj = all_objects_dict[source_id]
    max_id = max(p[0] for p in planets)

    candidates = []

    for base in range(0, max_id + 1, 4):
        group_ids = [base, base + 1, base + 2, base + 3]

        if not all(pid in all_objects_dict for pid in group_ids):
            continue

        if not all(is_orbiting_obj(all_objects_dict[pid]) for pid in group_ids):
            continue

        if any(owners_by_id.get(pid) == player for pid in group_ids):
            continue

        ordered_group = ordered_group_ids(group_ids, all_objects_dict)

        reachable_targets = []

        for target_id in ordered_group:
            target_obj = all_objects_dict[target_id]

            angle = pf.get_launch_angle(
                source_obj,
                target_obj,
                speed=1.0,
                delta_t=1.0,
            )

            if angle is not None:
                dist = np.linalg.norm(target_obj["pos"] - source_obj["pos"])
                reachable_targets.append((dist, target_id))

        if reachable_targets:
            candidates.append((min(d for d, _ in reachable_targets), ordered_group))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]

def dynamic_to_dynamic_agent(obs):
    global DYNAMIC_SOURCE_ID, DYNAMIC_TARGET_GROUP
    global DYNAMIC_ENTRY_TARGET_ID, DYNAMIC_ENTRY_DONE

    moves = []
    player = obs["player"]
    planets = obs["planets"]

    pf = PathFinder(obs)

    all_objects_dict = {
        obj["id"]: obj
        for obj in pf.static_obstacles + pf.orbiting_obstacles + pf.comets
    }

    owners_by_id = {p[0]: p[1] for p in planets}
    ships_by_id = {p[0]: p[5] for p in planets}

    if DYNAMIC_SOURCE_ID is None:
        my_planets = [p for p in planets if p[1] == player]
        if not my_planets:
            return []
        DYNAMIC_SOURCE_ID = my_planets[0][0]

    if DYNAMIC_TARGET_GROUP is None:
        group = choose_one_reachable_orbiting_group(
            obs,
            pf,
            all_objects_dict,
            DYNAMIC_SOURCE_ID,
        )

        if group is None:
            return []

        DYNAMIC_TARGET_GROUP = group

        source_obj = all_objects_dict[DYNAMIC_SOURCE_ID]
        reachable = []

        for target_id in DYNAMIC_TARGET_GROUP:
            target_obj = all_objects_dict[target_id]

            angle = pf.get_launch_angle(
                source_obj,
                target_obj,
                speed=1.0,
                delta_t=1.0,
            )

            if angle is not None:
                dist = np.linalg.norm(target_obj["pos"] - source_obj["pos"])
                reachable.append((dist, target_id))

        if not reachable:
            return []

        reachable.sort(key=lambda x: x[0])
        DYNAMIC_ENTRY_TARGET_ID = reachable[0][1]

    group = [
        pid for pid in DYNAMIC_TARGET_GROUP
        if pid in all_objects_dict
    ]

    if len(group) < 4:
        return []

    owned_in_group = [
        pid for pid in group
        if owners_by_id.get(pid) == player
    ]

    if DYNAMIC_ENTRY_TARGET_ID in owned_in_group:
        DYNAMIC_ENTRY_DONE = True

    if not DYNAMIC_ENTRY_DONE:
        source_id = DYNAMIC_SOURCE_ID
        target_id = DYNAMIC_ENTRY_TARGET_ID

        if source_id not in all_objects_dict or target_id not in all_objects_dict:
            return []

        if owners_by_id.get(source_id) != player:
            return []

        source_ships = ships_by_id.get(source_id, 0)

        if source_ships < ENTRY_MIN_SHIPS:
            return []

        ships_to_send = max(1, int(source_ships * ENTRY_SEND_RATIO))
        speed = fleet_speed(ships_to_send)

        source_obj = all_objects_dict[source_id]
        target_obj = all_objects_dict[target_id]

        angle = pf.get_launch_angle(
            source_obj,
            target_obj,
            speed=speed,
            delta_t=1.0,
        )

        if angle is not None:
            moves.append([source_id, angle, ships_to_send])

        return moves

    for source_id in group:
        if owners_by_id.get(source_id) != player:
            continue

        source_ships = ships_by_id.get(source_id, 0)

        if source_ships < CYCLE_MIN_SHIPS:
            continue

        source_index = group.index(source_id)

        neighbor_ids = [
            group[(source_index + 1) % len(group)],
            group[(source_index - 1) % len(group)],
        ]

        source_obj = all_objects_dict[source_id]

        for target_id in neighbor_ids:
            if target_id not in all_objects_dict:
                continue

            target_obj = all_objects_dict[target_id]

            angle = pf.get_launch_angle(
                source_obj,
                target_obj,
                speed=1.0,
                delta_t=1.0,
            )

            if angle is not None:
                moves.append([source_id, angle, 1])

    return moves
```

## [CODE]
```python
from kaggle_environments import make
import os
import random
import numpy as np

SEED = 42
DYNAMIC_SOURCE_ID = None
DYNAMIC_TARGET_GROUP = None

env = make("orbit_wars", configuration={"episodeSteps": 300} , debug=True)
print("Starting test : Dynamic to Dynamic...")

random.seed(SEED)
np.random.seed(SEED)

env.run([dynamic_to_dynamic_agent, dummy_agent])
env.render(mode="ipython", width=800, height=600)

# html_output = env.render(mode="html", width=800, height=600)
# with open("test_dynamic_to_dynamic.html", "w", encoding="utf-8") as f:
#     f.write(html_output)

# print("Fichier test_dynamic_to_dynamic.html généré dans /kaggle/working/ !")
```

## [MD]
## Test D: Dynamic to Static
In this test, the agent must invade a dynamic group of planets and continuously send fleets to the planets of a static group. The goal is to evaluate the algorithm's capacity to **send fleets from a dynamic planet to a static planet** through a moving environment.
> We set the number of ships per fleet to one for simplicity.

## [CODE]
```python
import numpy as np

ORBIT_SOURCE_ID = None
ORBIT_ENTRY_TARGET_ID = None
STATIC_TARGET_GROUP = None
ORBIT_ENTRY_DONE = False

ORBIT_ENTRY_MIN_SHIPS = 40
ORBIT_ENTRY_SEND_RATIO = 0.75

def is_static_obj(obj):
    return (
        obj["id"] != "SUN"
        and "orbital_radius" not in obj
        and "path" not in obj
    )

def ordered_group_ids(group_ids, all_objects_dict):
    return sorted(
        group_ids,
        key=lambda pid: np.atan2(
            all_objects_dict[pid]["pos"][1] - SUN_CENTER[1],
            all_objects_dict[pid]["pos"][0] - SUN_CENTER[0],
        )
    )

def fleet_speed(ships, max_speed=6.0):
    ships = max(1, int(ships))
    return 1.0 + (max_speed - 1.0) * (np.log(ships) / np.log(1000)) ** 1.5

def choose_reachable_orbiting_entry(obs, pf, all_objects_dict):
    player = obs["player"]
    planets = obs["planets"]

    my_planets = [
        p for p in planets
        if p[1] == player and p[5] >= 2
    ]

    orbit_targets = [
        obj for obj in pf.orbiting_obstacles
        if obj["id"] != "SUN"
    ]

    owners_by_id = {p[0]: p[1] for p in planets}

    candidates = []

    for source_planet in my_planets:
        source_id = source_planet[0]
        source_obj = all_objects_dict[source_id]

        for target_obj in orbit_targets:
            target_id = target_obj["id"]

            if owners_by_id.get(target_id) == player:
                continue

            angle = pf.get_launch_angle(
                source_obj,
                target_obj,
                speed=1.0,
                delta_t=1.0,
            )

            if angle is not None:
                dist = np.linalg.norm(target_obj["pos"] - source_obj["pos"])
                candidates.append({
                    "dist": dist,
                    "source_id": source_id,
                    "target_id": target_id,
                })

    if not candidates:
        return None

    candidates.sort(key=lambda c: c["dist"])
    return candidates[0]

def choose_reachable_static_group_from_source(obs, pf, all_objects_dict, source_id):
    planets = obs["planets"]
    owners_by_id = {p[0]: p[1] for p in planets}

    if source_id not in all_objects_dict:
        return None

    source_obj = all_objects_dict[source_id]
    max_id = max(p[0] for p in planets)

    candidates = []

    for base in range(0, max_id + 1, 4):
        group_ids = [base, base + 1, base + 2, base + 3]

        if not all(pid in all_objects_dict for pid in group_ids):
            continue

        if not all(is_static_obj(all_objects_dict[pid]) for pid in group_ids):
            continue

        if all(owners_by_id.get(pid) == obs["player"] for pid in group_ids):
            continue

        reachable_count = 0
        min_dist = float("inf")

        for target_id in group_ids:
            target_obj = all_objects_dict[target_id]

            angle = pf.get_launch_angle(
                source_obj,
                target_obj,
                speed=1.0,
                delta_t=1.0,
            )

            if angle is not None:
                reachable_count += 1
                min_dist = min(
                    min_dist,
                    np.linalg.norm(target_obj["pos"] - source_obj["pos"]),
                )

        if reachable_count > 0:
            candidates.append((reachable_count, min_dist, group_ids))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (-x[0], x[1]))
    return candidates[0][2]

def dynamic_to_static_agent(obs):
    global ORBIT_SOURCE_ID, ORBIT_ENTRY_TARGET_ID
    global STATIC_TARGET_GROUP, ORBIT_ENTRY_DONE

    moves = []
    player = obs["player"]
    planets = obs["planets"]

    pf = PathFinder(obs)

    all_objects_dict = {
        obj["id"]: obj
        for obj in pf.static_obstacles + pf.orbiting_obstacles + pf.comets
    }

    owners_by_id = {p[0]: p[1] for p in planets}
    ships_by_id = {p[0]: p[5] for p in planets}

    if ORBIT_ENTRY_TARGET_ID is None:
        entry = choose_reachable_orbiting_entry(obs, pf, all_objects_dict)

        if entry is None:
            return []

        ORBIT_SOURCE_ID = entry["source_id"]
        ORBIT_ENTRY_TARGET_ID = entry["target_id"]
        ORBIT_ENTRY_DONE = False

    if owners_by_id.get(ORBIT_ENTRY_TARGET_ID) == player:
        ORBIT_ENTRY_DONE = True

    if not ORBIT_ENTRY_DONE:
        source_id = ORBIT_SOURCE_ID
        target_id = ORBIT_ENTRY_TARGET_ID

        if source_id not in all_objects_dict or target_id not in all_objects_dict:
            return []

        if owners_by_id.get(source_id) != player:
            return []

        source_ships = ships_by_id.get(source_id, 0)

        if source_ships < ORBIT_ENTRY_MIN_SHIPS:
            return []

        ships_to_send = max(1, int(source_ships * ORBIT_ENTRY_SEND_RATIO))
        speed = fleet_speed(ships_to_send)

        angle = pf.get_launch_angle(
            all_objects_dict[source_id],
            all_objects_dict[target_id],
            speed=speed,
            delta_t=1.0,
        )

        if angle is not None:
            moves.append([source_id, angle, ships_to_send])

        return moves

    orbit_source_id = ORBIT_ENTRY_TARGET_ID

    if orbit_source_id not in all_objects_dict:
        return []

    if owners_by_id.get(orbit_source_id) != player:
        return []

    if ships_by_id.get(orbit_source_id, 0) < 2:
        return []

    if STATIC_TARGET_GROUP is None:
        group = choose_reachable_static_group_from_source(
            obs,
            pf,
            all_objects_dict,
            orbit_source_id,
        )

        if group is None:
            return []

        STATIC_TARGET_GROUP = ordered_group_ids(group, all_objects_dict)

    source_obj = all_objects_dict[orbit_source_id]

    for target_id in STATIC_TARGET_GROUP:
        if target_id not in all_objects_dict:
            continue

        target_obj = all_objects_dict[target_id]

        angle = pf.get_launch_angle(
            source_obj,
            target_obj,
            speed=1.0,
            delta_t=1.0,
        )

        if angle is not None:
            moves.append([orbit_source_id, angle, 1])

    return moves
```

## [CODE]
```python
from kaggle_environments import make
import os
import random
import numpy as np

SEED = 42
ORBIT_SOURCE_ID = None
ORBIT_ENTRY_TARGET_ID = None
STATIC_TARGET_GROUP = None
ORBIT_ENTRY_DONE = False

env = make("orbit_wars", configuration={"episodeSteps": 300} , debug=True)
print("Starting test : Dynamic to Static...")

random.seed(SEED)
np.random.seed(SEED)

env.run([dynamic_to_static_agent, dummy_agent])
env.render(mode="ipython", width=800, height=600)

# html_output = env.render(mode="html", width=800, height=600)
# with open("test_dynamic_to_static.html", "w", encoding="utf-8") as f:
#     f.write(html_output)

# print("Fichier test_dynamic_to_static.html généré dans /kaggle/working/ !")
```

## [MD]
## Test E: Comet Interception
In this test, the agent must send fleets of 10 ships to any reachable comet whenever possible. The goal is to evaluate the algorithm's capacity to **send fleets to comets**.

## [CODE]
```python
def fleet_speed(ships, max_speed=6.0):
    ships = max(1, int(ships))
    return 1.0 + (max_speed - 1.0) * (np.log(ships) / np.log(1000)) ** 1.5

def test_comet_continuous_agent(obs):
    moves = []
    player = obs["player"]
    planets = obs["planets"]
    comet_ids = obs.get("comet_planet_ids", [])

    # Pas de comètes visibles : on attend.
    if not comet_ids:
        return []

    pf = PathFinder(obs)

    all_objects_dict = {
        obj["id"]: obj
        for obj in pf.static_obstacles + pf.orbiting_obstacles + pf.comets
    }

    my_planets = [
        p for p in planets
        if p[1] == player and p[5] > 10
    ]

    if not my_planets:
        return []

    ships_to_send = 10
    speed = fleet_speed(ships_to_send)

    # Cibles comètes visibles uniquement.
    comet_targets = [
        cid for cid in comet_ids
        if cid in all_objects_dict
    ]

    for source_planet in my_planets:
        source_id = source_planet[0]
        source_obj = all_objects_dict[source_id]

        for comet_id in comet_targets:
            target_obj = all_objects_dict[comet_id]

            angle = pf.get_launch_angle(
                source_obj,
                target_obj,
                speed=speed,
                delta_t=1.0,
            )

            if angle is not None:
                moves.append([source_id, angle, ships_to_send])
                break  # une flotte par planète source par tour

    return moves
```

## [CODE]
```python
from kaggle_environments import make
import os
import random
import numpy as np

SEED = 42

env = make("orbit_wars", configuration={"episodeSteps": 300} , debug=True)
print("Starting test : Comet Interception...")

random.seed(SEED)
np.random.seed(SEED)

env.run([test_comet_continuous_agent, dummy_agent])
env.render(mode="ipython", width=800, height=600)

# html_output = env.render(mode="html", width=800, height=600)
# with open("test_comet.html", "w", encoding="utf-8") as f:
#     f.write(html_output)

# print("Fichier test_comet.html généré dans /kaggle/working/ !")
```
