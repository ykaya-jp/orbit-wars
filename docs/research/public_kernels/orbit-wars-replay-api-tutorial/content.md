## [MD]
# Orbit Wars: Replay Data API Tutorial

> **Fetch, parse, and analyze any match replay from the Orbit Wars leaderboard**
>
> The leaderboard URL has two IDs: `submissionId`
> and `episodeId` (one specific match). This notebook covers both.

## [MD]
## 1. Setup - Credentials

The API uses Kaggle Basic Auth (username + API key).

**On Kaggle:** Add your API key as a Secret named `KAGGLE_KEY` in notebook settings
(Add-ons -> Secrets -> KAGGLE_KEY). Your username is auto-injected as
`os.environ['KAGGLE_USERNAME']`.

**Locally:** Place your `kaggle.json` in the working directory.

## [CODE]
```python
import os
import json
import requests

BASE = 'https://www.kaggle.com/api/i/competitions.EpisodeService/'

# -- Try Kaggle Secrets (Kaggle platform)
AUTH = None
try:
    from kaggle_secrets import UserSecretsClient
    _s = UserSecretsClient()
    _user = os.environ.get('KAGGLE_USERNAME', '')
    _key  = _s.get_secret('KAGGLE_KEY')
    AUTH = (_user, _key)
    print(f'Kaggle Secrets loaded for: {_user}')
except Exception:
    pass

# -- Try local kaggle.json (local use)
if AUTH is None:
    try:
        with open('kaggle.json') as _f:
            _c = json.load(_f)
        AUTH = (_c['username'], _c['key'])
        print(f'Local credentials loaded for: {AUTH[0]}')
    except FileNotFoundError:
        print('WARNING: No credentials found.')
        print('  On Kaggle: add KAGGLE_KEY as a Secret (Add-ons -> Secrets).')
        print('  Locally:   place kaggle.json in the working directory.')
        print('  API calls below will be skipped.')

if AUTH is not None:
    print('Ready.')
```

## [MD]
## 2. List Episodes for a Submission

Given a `submissionId`, fetch all recent matches that agent played.

## [CODE]
```python
def list_episodes(submission_id, auth):
    # Returns (episodes_list, sub_to_name_dict)
    resp = requests.post(
        BASE + 'ListEpisodes',
        json={'submissionId': submission_id},
        auth=auth
    )
    resp.raise_for_status()
    raw = resp.json()

    episodes   = raw.get('episodes', [])
    subs_list  = raw.get('submissions', [])
    teams_list = raw.get('teams', [])

    team_by_id  = {t['id']: t['teamName'] for t in teams_list}
    sub_to_name = {
        s['id']: team_by_id.get(s.get('teamId', 0), f"sub_{s['id']}")
        for s in subs_list
    }
    return episodes, sub_to_name


SUBMISSION_ID = 51896673   # Change to any submissionId from the leaderboard

if AUTH is not None:
    episodes, sub_to_name = list_episodes(SUBMISSION_ID, AUTH)
    print(f'Episodes found: {len(episodes)}')
else:
    print('Skipped: no credentials. Set AUTH above.')
    episodes, sub_to_name = [], {}
```

## [MD]
### Episode Table

Show the 20 most recent episodes as a readable table.

## [CODE]
```python
if episodes:
    rows = []
    for ep in sorted(episodes, key=lambda e: e['createTime'], reverse=True)[:20]:
        agents = ep['agents']
        my_agent = next((a for a in agents if a['submissionId'] == SUBMISSION_ID), None)
        opps = [a for a in agents if a['submissionId'] != SUBMISSION_ID]
        opp_names = [sub_to_name.get(a['submissionId'], '?') for a in opps]
        my_reward = my_agent['reward'] if my_agent else '?'
        ep_id     = ep['id']
        create_t  = ep['createTime'][:19]
        rows.append((ep_id, create_t, my_reward, ', '.join(opp_names)))

    print(f'{"Episode ID":>12}  {"Time":>19}  {"My Reward":>10}  Opponents')
    print('-' * 80)
    for r in rows:
        print(f'{r[0]:>12}  {r[1]:>19}  {r[2]:>10}  {r[3]}')
else:
    print('No episodes (credentials not set or no data).')
```

## [MD]
## 3. Fetch a Full Replay

With an `episodeId`, fetch the complete step-by-step replay.

## [CODE]
```python
def fetch_replay(episode_id, auth):
    # Returns replay dict with keys: steps, configuration, info, rewards, statuses
    resp = requests.post(
        BASE + 'GetEpisodeReplay',
        json={'episodeId': episode_id},
        auth=auth
    )
    resp.raise_for_status()
    return resp.json()


EPISODE_ID = 75239557   # Change to any episodeId from the table above

if AUTH is not None:
    replay = fetch_replay(EPISODE_ID, AUTH)
    agents = replay.get('agents', [])
    config = replay.get('configuration', {})
    print(f'Steps in replay : {len(replay["steps"])}')
    print(f'Players          : {len(agents)}')
    print(f'Total turns      : {config.get("episodeSteps", "?")} configured')
else:
    print('Skipped: no credentials.')
    replay = None
    agents = []
```

## [MD]
## 4. Data Format Reference

The replay `steps` field is a list of per-step observations:

```python
replay['steps'][step_index][player_index]['observation']
```

### Planet format
```
planets[i] = [id, owner, x, y, radius, ships, production]
  owner: -1=neutral, 0=Player0, 1=Player1, ...
```

### Fleet format
```
fleets[i] = [id, owner, x, y, size, source_planet, dest_planet]
```

### Top-level keys in each step entry
```
action, reward, info, observation
observation: planets, fleets, step, angular_velocity
```

## [CODE]
```python
if replay is not None:
    step1    = replay['steps'][1][0]['observation']
    planets  = step1['planets']
    fleets   = step1['fleets']
    ang_vel  = step1['angular_velocity']

    print(f'Angular velocity : {ang_vel:.4f} rad/turn')
    print(f'Total planets    : {len(planets)}')
    print(f'Active fleets    : {len(fleets)}')
    print()
    print(f'{"ID":>3}  {"Owner":>6}  {"x":>5}  {"y":>5}  {"R":>4}  {"Ships":>5}  {"Prod":>4}')
    print('-' * 45)
    for p in planets[:10]:
        pid, owner, x, y, r, ships, prod = p[:7]
        print(f'{pid:>3}  {owner:>6}  {x:>5}  {y:>5}  {r:>4}  {ships:>5}  {prod:>4}')
    if len(planets) > 10:
        print(f'  ... and {len(planets)-10} more')
else:
    print('Skipped: no replay data.')
```

## [MD]
## 5. Basic Analysis: Ship Count Timeline

Plot each player's total ship count (fleet + planet garrison) over time.

## [CODE]
```python
import matplotlib.pyplot as plt
import numpy as np

if replay is not None:
    num_players = len(agents)
    timeline_steps   = []
    timeline_ships   = [[] for _ in range(num_players)]
    timeline_planets = [[] for _ in range(num_players)]

    for step_idx in range(0, len(replay['steps']), 5):
        obs = replay['steps'][step_idx][0]['observation']
        if isinstance(obs, dict):
            planets_s = obs.get('planets', [])
            fleets_s  = obs.get('fleets', [])
            step_num  = obs.get('step', step_idx)
        else:
            planets_s = obs.planets
            fleets_s  = obs.fleets
            step_num  = step_idx

        timeline_steps.append(step_num)
        ship_count   = [0] * num_players
        planet_count = [0] * num_players

        for p in planets_s:
            owner, ships = p[1], p[5]
            if 0 <= owner < num_players:
                ship_count[owner]   += ships
                planet_count[owner] += 1
        for fl in fleets_s:
            owner, size = fl[1], fl[4]
            if 0 <= owner < num_players:
                ship_count[owner] += size

        for p in range(num_players):
            timeline_ships[p].append(ship_count[p])
            timeline_planets[p].append(planet_count[p])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor('#0d1117')
    colors = ['#58a6ff', '#f78166', '#3fb950', '#ffa657']

    agent_names = [a.get('teamName', f'Player {i}') for i, a in enumerate(agents)]

    for ax in (ax1, ax2):
        ax.set_facecolor('#161b22')
        ax.tick_params(colors='#8b949e')
        ax.spines[:].set_color('#30363d')

    for p in range(num_players):
        c = colors[p % len(colors)]
        ax1.plot(timeline_steps, timeline_ships[p],   color=c, lw=2, label=agent_names[p])
        ax2.plot(timeline_steps, timeline_planets[p], color=c, lw=2, label=agent_names[p])

    ax1.set_title('Total Ships (garrison + fleets)', color='white')
    ax2.set_title('Planets Owned', color='white')
    for ax in (ax1, ax2):
        ax.set_xlabel('Turn', color='#8b949e')
        ax.legend(facecolor='#21262d', labelcolor='white', edgecolor='#30363d')

    plt.tight_layout()
    plt.show()
else:
    print('Skipped: no replay data.')
```

## [MD]
## 6. Planet Capture Events

Track every ownership change: who captured what planet and when.

## [CODE]
```python
if replay is not None:
    prev_owners = {}
    capture_events = []

    for step_idx, step_data in enumerate(replay['steps']):
        obs = step_data[0]['observation']
        if isinstance(obs, dict):
            planets_s = obs.get('planets', [])
            step_num  = obs.get('step', step_idx)
        else:
            planets_s = obs.planets
            step_num  = step_idx

        for p in planets_s:
            pid, owner = p[0], p[1]
            if pid in prev_owners and prev_owners[pid] != owner:
                capture_events.append({
                    'step'     : step_num,
                    'planet_id': pid,
                    'from'     : prev_owners[pid],
                    'to'       : owner,
                })
            prev_owners[pid] = owner

    print(f'Total capture events: {len(capture_events)}')
    print()
    print(f'{"Step":>5}  {"Planet":>7}  {"From":>5}  {"To":>5}')
    print('-' * 32)
    for ev in capture_events[:20]:
        print(f'{ev["step"]:>5}  {ev["planet_id"]:>7}  {ev["from"]:>5}  {ev["to"]:>5}')
    if len(capture_events) > 20:
        print(f'  ... and {len(capture_events)-20} more')
else:
    print('Skipped: no replay data.')
```

## [MD]
## 7. Save Replay to Disk

Save the raw replay JSON for offline analysis or bulk processing.

## [CODE]
```python
if replay is not None:
    output_path = f'replay_{EPISODE_ID}.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(replay, f, ensure_ascii=False, indent=2)
    size_kb = len(json.dumps(replay).encode()) / 1024
    print(f'Saved: {output_path}  (~{size_kb:.0f} KB)')
    print()
    print('Top-level keys:')
    for k, v in replay.items():
        if isinstance(v, list):
            print(f'  {k}: list of {len(v)}')
        elif isinstance(v, dict):
            print(f'  {k}: dict with {len(v)} keys')
        else:
            print(f'  {k}: {v}')
else:
    print('Skipped: no replay data.')
```

## [MD]
## 8. Where to Go From Here

Now that you can fetch and parse any replay, some ideas:

### Analysis ideas
- **Heatmap of fleet launch angles** - do top agents use the full 360 degrees?
- **First-capture timing** - how fast do strong agents grab neutral planets?
- **Fleet size distribution** - large consolidated fleets vs. many small ones
- **Win-condition correlation** - ship count, planet count, territory shape

### Batch analysis
```python
episodes, _ = list_episodes(SUBMISSION_ID, AUTH)
for ep in episodes:
    r = fetch_replay(ep['id'], AUTH)
    # ... your analysis
```

### Useful resources
- [Orbit Wars Complete Mechanics Deep Dive](https://www.kaggle.com/code/dylanxue04/orbit-wars-complete-game-mechanics-deep-dive)
- [Orbit Wars Competition Page](https://www.kaggle.com/competitions/orbit-wars)
