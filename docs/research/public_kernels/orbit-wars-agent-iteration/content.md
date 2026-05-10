## [MD]
# Orbit Wars v38 Testing Notebook

## [CODE]
```python
from kaggle_environments import make
import pandas as pd

env = make('orbit_wars', debug=True)
```

## [MD]
## Test 1: v38 vs 3x Random

## [CODE]
```python
results = []
for i in range(5):
    env.reset()
    env.run(['main_v38.py', 'random', 'random', 'random'])
    final = env.steps[-1]
    results.append({'test': i+1, 'v38_reward': final[0].reward, 'p1': final[1].reward, 'p2': final[2].reward, 'p3': final[3].reward})

df = pd.DataFrame(results)
print('v38 vs 3x Random (5 tests):')
print(df)
print(f'\nv38 win rate: {(df["v38_reward"] > df[["p1","p2","p3"]].max(axis=1)).mean()*100:.0f}%')
```

## [MD]
## Test 2: v38 vs v37 (head-to-head with 2 randoms)

## [CODE]
```python
results2 = []
for i in range(5):
    env.reset()
    env.run(['main_v38.py', 'main_v37.py', 'random', 'random'])
    final = env.steps[-1]
    results2.append({'test': i+1, 'v38': final[0].reward, 'v37': final[1].reward, 'r1': final[2].reward, 'r2': final[3].reward})

df2 = pd.DataFrame(results2)
print('v38 vs v37 (5 tests):')
print(df2)
v38_wins = (df2['v38'] > df2['v37']).sum()
print(f'\nv38 beats v37: {v38_wins}/5')
```

## [MD]
## Test 3: v38 vs v37 (direct 1v1)

## [CODE]
```python
results3 = []
for i in range(5):
    env.reset()
    env.run(['main_v38.py', 'main_v37.py'])
    final = env.steps[-1]
    results3.append({'test': i+1, 'v38': final[0].reward, 'v37': final[1].reward})

df3 = pd.DataFrame(results3)
print('v38 vs v37 direct (5 tests):')
print(df3)
v38_wins = (df3['v38'] > df3['v37']).sum()
print(f'\nv38 wins: {v38_wins}/5')
```

## [MD]
## Test 4: 4-way battle (v38, v37, v35, random)

## [CODE]
```python
results4 = []
for i in range(3):
    env.reset()
    env.run(['main_v38.py', 'main_v37.py', 'main.py', 'random'])
    final = env.steps[-1]
    results4.append({'test': i+1, 'v38': final[0].reward, 'v37': final[1].reward, 'v35': final[2].reward, 'rnd': final[3].reward})

df4 = pd.DataFrame(results4)
print('4-way battle (v38, v37, v35, random):')
print(df4)
print(f'\nAverage rewards: v38={df4["v38"].mean():.1f}, v37={df4["v37"].mean():.1f}, v35={df4["v35"].mean():.1f}')
```
