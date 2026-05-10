## [MD]
## Imports

## [CODE]
```python
import os
import json
import math
import base64
import io
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from torch.utils.data import Dataset, DataLoader
```

## [MD]
## Hyperparameters

## [CODE]
```python
MAX_PLANETS = 150
MAX_FLEETS = 200
D_MODEL = 256
NHEAD = 8
LAYERS = 4
BATCH_SIZE = 128
EPOCHS = 40
DATA_PATH = "/kaggle/input/datasets/lakhindarpal/orbit-wars-rank1-gameplay/"
```

## [MD]
## Dataset

## [CODE]
```python
class OrbitWarsDataset(Dataset):
    def __init__(self, directory):
        self.samples = []
        files = [f for f in os.listdir(directory) if f.endswith(".json")]
        for f in files:
            with open(os.path.join(directory, f)) as j:
                replay = json.load(j)
                self._process(replay)
        print(f"✅ Total Training Samples: {len(self.samples)}")

    def _process(self, replay):
        steps = replay["steps"]
        # Identify the winner safely
        winner = next((i for i, s in enumerate(steps[-1]) if s.get("reward") == 1), 0)

        for step in steps[1:-1]:
            obs = step[0]["observation"]
            actions = step[winner].get("action", [])

            for act in actions:
                # Find source index
                s_idx = next((i for i, pl in enumerate(obs["planets"]) if pl[0] == act[0]), -1)
                if s_idx == -1:
                    continue

                tx, ty = obs["planets"][s_idx][2], obs["planets"][s_idx][3]
                t_idx = -1
                min_d = 9999

                # Robust reverse raycast using ~0.3 rad cone
                for i, pl in enumerate(obs["planets"]):
                    if i == s_idx:
                        continue
                    dist = math.hypot(pl[2] - tx, pl[3] - ty)
                    ang = math.atan2(pl[3] - ty, pl[2] - tx)
                    diff = math.atan2(math.sin(ang - act[1]), math.cos(ang - act[1]))

                    if abs(diff) < 0.3:
                        if dist < min_d:
                            min_d, t_idx = dist, i

                # Skip sample if no valid target was found (prevents label poisoning)
                if t_idx != -1:
                    frac = min(1.0, act[2] / max(1, obs["planets"][s_idx][5]))
                    self.samples.append((obs, winner, s_idx, t_idx, frac))

    def _featurize(self, obs, player):
        planets = obs["planets"]
        p_tensor = np.zeros((MAX_PLANETS, 10), dtype=np.float32)
        for i, p in enumerate(planets[:MAX_PLANETS]):
            x, y = p[2], p[3]
            orb_r = math.hypot(x - 50, y - 50) / 50.0
            orb_a = math.atan2(y - 50, x - 50) / math.pi
            p_tensor[i] = [
                1,
                x / 100,
                y / 100,
                p[4] / 10,
                p[1] == player,
                (p[1] != player and p[1] != -1),
                min(p[5] / 100, 10),
                p[6] / 10,
                orb_r,
                orb_a,
            ]

        f_tensor = np.zeros((MAX_FLEETS, 5), dtype=np.float32)
        for i, f in enumerate(obs["fleets"][:MAX_FLEETS]):
            f_tensor[i] = [
                1,
                f[2] / 100,
                f[3] / 100,
                1 if f[1] == player else -1,
                min(f[6] / 100, 10),
            ]
        return torch.tensor(p_tensor), torch.tensor(f_tensor)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        obs, p_id, s_idx, t_idx, frac = self.samples[idx]
        p, f = self._featurize(obs, p_id)
        return (
            p,
            f,
            torch.tensor(s_idx),
            torch.tensor(t_idx),
            torch.tensor(frac, dtype=torch.float32),
        )
```

## [MD]
## Transformer

## [CODE]
```python
class OrbitTransformer(nn.Module):
    def __init__(self):
        super().__init__()
        self.p_proj = nn.Linear(10, D_MODEL)
        self.f_proj = nn.Linear(5, D_MODEL)
        self.type_emb = nn.Embedding(2, D_MODEL)

        enc = nn.TransformerEncoderLayer(
            D_MODEL, NHEAD, D_MODEL * 4, batch_first=True, dropout=0.1
        )
        self.tf = nn.TransformerEncoder(enc, LAYERS)

        self.src_h = nn.Sequential(
            nn.Linear(D_MODEL, D_MODEL // 2), nn.ReLU(), nn.Linear(D_MODEL // 2, 1)
        )
        self.q_p = nn.Linear(D_MODEL, D_MODEL)
        self.k_p = nn.Linear(D_MODEL, D_MODEL)
        self.fr_h = nn.Sequential(
            nn.Linear(D_MODEL, 64), nn.ReLU(), nn.Linear(64, 1), nn.Sigmoid()
        )

    def forward(self, p, f, s_gt=None):
        B, nP = p.size(0), p.size(1)

        # Proper broadcastable zeros/ones for type embedding
        t0 = torch.zeros(1, dtype=torch.long, device=p.device)
        t1 = torch.ones(1, dtype=torch.long, device=f.device)

        pe = self.p_proj(p) + self.type_emb(t0)
        fe = self.f_proj(f) + self.type_emb(t1)

        # Global attention context
        out = self.tf(torch.cat([pe, fe], 1))[:, :nP, :]

        # Source Selection
        s_l = self.src_h(out).squeeze(-1)
        src_idx = s_gt if s_gt is not None else torch.argmax(s_l, 1)
        src_emb = out[torch.arange(B), src_idx, :]

        # Pointer Target Selection
        q = self.q_p(src_emb.unsqueeze(1))
        t_l = torch.bmm(q, self.k_p(out).transpose(1, 2)).squeeze(1)

        # Predict ship fraction using ONLY the source planet's context
        fr = self.fr_h(src_emb).squeeze(-1)

        return s_l, t_l, fr
```

## [MD]
## Training

## [CODE]
```python
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = nn.DataParallel(OrbitTransformer()).to(device)
dataset = OrbitWarsDataset(DATA_PATH)
loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

opt = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
sch = optim.lr_scheduler.CosineAnnealingLR(opt, EPOCHS)
crit_ce = nn.CrossEntropyLoss(label_smoothing=0.1)
crit_mse = nn.MSELoss()

print("🚀 Starting Stable Training...")
for ep in range(EPOCHS):
    model.train()
    total_loss = 0
    for p, f, s, t, fr in loader:
        p, f, s, t, fr = (
            p.to(device),
            f.to(device),
            s.to(device),
            t.to(device),
            fr.to(device),
        )

        opt.zero_grad()
        # Feed the ground-truth source (s) for teacher forcing
        sl, tl, pf = model(p, f, s_gt=s)

        loss = crit_ce(sl, s) + crit_ce(tl, t) + crit_mse(pf, fr) * 5
        loss.backward()

        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()

        total_loss += loss.item()

    sch.step()
    print(f"Epoch {ep+1}/{EPOCHS} | Loss: {total_loss/len(loader):.4f} | LR: {sch.get_last_lr()[0]:.6f}")
```

## [MD]
## Submission

## [CODE]
```python
# Extract weights from DataParallel
raw_model = model.module if hasattr(model, "module") else model
torch.save(raw_model.state_dict(), "rank1_clone.pth")

# Encode to string
with open("rank1_clone.pth", "rb") as f:
    b64_str = base64.b64encode(f.read()).decode("utf-8")

# Build self-contained script
sub_code = f"""
import base64, io, torch, math, numpy as np, torch.nn as nn

B64 = "{b64_str}"

class OrbitTransformer(nn.Module):
    def __init__(self):
        super().__init__()
        self.p_proj = nn.Linear(10, {D_MODEL}); self.f_proj = nn.Linear(5, {D_MODEL}); self.type_emb = nn.Embedding(2, {D_MODEL})
        enc = nn.TransformerEncoderLayer({D_MODEL}, {NHEAD}, {D_MODEL*4}, batch_first=True)
        self.tf = nn.TransformerEncoder(enc, {LAYERS})
        self.src_h = nn.Sequential(nn.Linear({D_MODEL}, {D_MODEL//2}), nn.ReLU(), nn.Linear({D_MODEL//2}, 1))
        self.q_p, self.k_p = nn.Linear({D_MODEL}, {D_MODEL}), nn.Linear({D_MODEL}, {D_MODEL})
        self.fr_h = nn.Sequential(nn.Linear({D_MODEL}, 64), nn.ReLU(), nn.Linear(64, 1), nn.Sigmoid())

    def forward(self, p, f, s_gt=None):
        B, nP = p.size(0), p.size(1)
        t0 = torch.zeros(1, dtype=torch.long, device=p.device)
        t1 = torch.ones(1, dtype=torch.long, device=f.device)
        pe = self.p_proj(p) + self.type_emb(t0)
        fe = self.f_proj(f) + self.type_emb(t1)
        out = self.tf(torch.cat([pe, fe], 1))[:, :nP, :]
        s_l = self.src_h(out).squeeze(-1)
        src_idx = s_gt if s_gt is not None else torch.argmax(s_l, 1)
        src_emb = out[torch.arange(B), src_idx, :]
        q = self.q_p(src_emb.unsqueeze(1))
        t_l = torch.bmm(q, self.k_p(out).transpose(1, 2)).squeeze(1)
        fr = self.fr_h(src_emb).squeeze(-1)
        return s_l, t_l, fr

M = None

# Kaggle Signature Fixed
def agent(obs):
    global M
    if M is None:
        M = OrbitTransformer()
        M.load_state_dict(torch.load(io.BytesIO(base64.b64decode(B64)), map_location='cpu'))
        M.eval()

    p_t = np.zeros((1, 150, 10), dtype=np.float32)
    for i, p in enumerate(obs.planets[:150]):
        x, y = p[2], p[3]
        p_t[0, i] = [1, x/100, y/100, p[4]/10, p[1]==obs.player, (p[1]!=obs.player and p[1]!=-1),
                     min(p[5]/100, 10), p[6]/10, math.hypot(x-50,y-50)/50, math.atan2(y-50,x-50)/math.pi]

    f_t = np.zeros((1, 200, 5), dtype=np.float32)
    for i, f in enumerate(obs.fleets[:200]):
        f_t[0, i] = [1, f[2]/100, f[3]/100, 1 if f[1]==obs.player else -1, min(f[6]/100, 10)]

    actions = []
    with torch.no_grad():
        p_ten = torch.tensor(p_t)
        f_ten = torch.tensor(f_t)

        # Multi-Move Evaluation Loop
        for i, p in enumerate(obs.planets):
            # Only command owned planets with available ships
            if p[1] == obs.player and p[5] > 1:
                # Supply the current planet index to fetch target specific to it
                s_gt = torch.tensor([i], dtype=torch.long)
                sl, tl, fr = M(p_ten, f_ten, s_gt)

                # Mask out targeting itself
                tl[0, i] = -1e9
                t_i = torch.argmax(tl, 1).item()

                sp, tp = obs.planets[i], obs.planets[t_i]
                actions.append([sp[0], float(math.atan2(tp[3]-sp[3], tp[2]-sp[2])), int(sp[5] * max(0.15, fr.item()))])

    return actions
"""

with open("submission.py", "w") as f:
    f.write(sub_code)
print("✅ submission.py generated.")
```
