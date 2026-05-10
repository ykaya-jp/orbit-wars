## [CODE]
```python
!pip install -U kaggle
```

## [CODE]
```python
import os

os.environ['KAGGLE_USERNAME'] = "sangrampatil5150"

# This ONly To Safe my KAGGLE KEY is not mandatory you can directly replace value from api_key variable!
from kaggle_secrets import UserSecretsClient
user_secrets = UserSecretsClient()

!mkdir -p replay
```

## [MD]
# Single Player Download

Currently, I used the ID of a top player, **bowwowforeach**, as an example to demonstrate the process.
In single-player replays, we use the submission ID of a specific player.

## 1

In step one, we first extract the list of all episodes for that player.
I scraped this link from the Developer tab:

``
url = "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes"
``

## 2

Using the JSON file of IDs we created, we make API calls to download all available replay files.

## [CODE]
```python
import json
import requests


SUB_ID = 52318886 # current top player bowwowforeach
username = os.environ.get('KAGGLE_USERNAME')
api_key = user_secrets.get_secret("KAGGLE_KEY")

url = "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes"

response = requests.post(
    url,
    auth=(username, api_key),
    json={
        "submissionId": SUB_ID
    }, # Send payload as JSON
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
)

if response.status_code == 200:
    data = response.json()
    output_filename = f"episodes_{SUB_ID}.json"

    with open(output_filename, 'w') as f:
        json.dump(data, f, indent=4)

    episodes = data.get('episodes',[])
    if len(episodes) == 0:
       print("empty")
    else:
        print(f"Found {len(episodes)} episodes.")

else:
    print(f"Failed to download.Status Code: {response.status_code}")
    print("Response details:")
    print(response.text)
```

## [MD]
# Download Part

## [CODE]
```python
import os
import json
import requests
import time

INPUT_FILE = f"episodes_{SUB_ID}.json"
OUTPUT_DIR = f"replay"

try:
    with open(INPUT_FILE, 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"Error: Could not find {INPUT_FILE}.")
    exit()

episodes = data.get('episodes', [])
print(f"Loaded {len(episodes)} episodes. Downloading all...")

downloaded = 0
for index, episode in enumerate(episodes):
    episode_id = episode.get('id')

    if not episode_id:
        continue

    print(f"[{index + 1}/{len(episodes)}] Downloading Episode {episode_id}...")

    url = f"https://www.kaggle.com/api/v1/competitions/episodes/{episode_id}/replay"
    r = requests.get(url, auth=(username, api_key))

    if r.status_code == 200:
        out_filepath = os.path.join(OUTPUT_DIR, f"{episode_id}.json")
        with open(out_filepath, "wb") as f:
            f.write(r.content)

        downloaded += 1
    else:
        print(f"Failed {episode_id} | Status: {r.status_code}")

    time.sleep(1)
```

## [MD]
# Multiple IDs Download Replays

## 3

Here, I collect multiple player IDs. In this case, I selected the top 20 IDs.
First, we had already scraped the ID of the 1st player. Then, I manually copied and pasted the IDs of players ranked 2 to 20.

Using a simple `for` loop, I fetched and downloaded the list of all episodes for each player and saved each result as a JSON file.

## 4

Next, we merge all these files to create a single file:

``
episodes_merged.json
``

Using the same code, we can then easily download all episodes.

It is important to add `time.sleep()`; otherwise, you may get the following error:

``
{"error":{"code":429,"message":"Too many requests","status":"RESOURCE_EXHAUSTED"}}
``

## [CODE]
```python
# this are range(1, 20) top player on LB
SUB_IDS = [
    52292204, # Shun_PI
    51987365, # Vadasz
    52300620, # Kovi,
    52266125, # Ousagi
    52335742, # sash
    52334987, # Andrew Tratz
    52358342, # ymg_aq,
    52266849, # ush
    52276006, # Wenchong Huang
    52346769, # Orbit Team
    52317967, # flg
    52312579, # HY2017
    52103846, # Orbital Occle
    52214689, # lookaside
    52357823, # Claws
    52334402, # Ezra
    52176489, # fgwiebfaoish
    52279326, # SalvadorDali
]


url = "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes"

for SUB_ID in SUB_IDS:
    print(f"\nFetching: {SUB_ID}")

    response = requests.post(
        url,
        auth=(username, api_key),
        json={"submissionId": SUB_ID},
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    )

    if response.status_code == 200:
        data = response.json()
        output_filename = f"episodes_{SUB_ID}.json"

        with open(output_filename, 'w') as f:
            json.dump(data, f, indent=4)

        print(f"Found {len(episodes)} episodes.")

    else:
        print(f"Failed for {SUB_ID} | Status: {response.status_code}")
        print(response.text)
    time.sleep(1)
```

## [CODE]
```python
import glob

files = glob.glob("episodes_*.json")
all_episodes = []
print(f"Found {len(files)} files.")

for file in files:
    with open(file, "r") as f:
        data = json.load(f)
        episodes = data.get("episodes", [])
        all_episodes.extend(episodes)

unique_episodes = {ep["id"]: ep for ep in all_episodes}
merged_list = list(unique_episodes.values())

output_file = "episodes_merged.json"

with open(output_file, "w") as f:
    json.dump({"episodes": merged_list}, f, indent=4)
```

## [CODE]
```python
import os
import json
import requests
import time

INPUT_FILE = f"episodes_merged.json"
OUTPUT_DIR = f"replay"

try:
    with open(INPUT_FILE, 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"Error: Could not find {INPUT_FILE}.")
    exit()

episodes = data.get('episodes', [])
print(f"Loaded {len(episodes)} episodes. Downloading all...")

downloaded = 0
for index, episode in enumerate(episodes):
    episode_id = episode.get('id')

    if not episode_id:
        continue

    if index % 50 == 0:
        print(f"[{index + 1}/{len(episodes)}] Downloading Episode {episode_id}...")

    url = f"https://www.kaggle.com/api/v1/competitions/episodes/{episode_id}/replay"
    r = requests.get(url, auth=(username, api_key))

    if r.status_code == 200:
        out_filepath = os.path.join(OUTPUT_DIR, f"{episode_id}.json")
        with open(out_filepath, "wb") as f:
            f.write(r.content)

        downloaded += 1
    else:
        print(f"Failed {episode_id} | Status: {r.status_code}")

    time.sleep(1)
```
