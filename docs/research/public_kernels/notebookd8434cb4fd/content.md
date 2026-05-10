## [MD]
# 嵌套agent写法

- 内置agent实现 random starter
- 嵌套agent玩法演示，计时
- main.py写法

可实现：计时器，记录器，过滤器等高级玩法

## [CODE]
```python
%%capture
!pip install --upgrade "kaggle-environments"
```

## [CODE]
```python
"""Agent 基类。"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Callable

class KaggleAgent(ABC):
    """Agent 基类，定义推理接口。

    返回值可以是:
        - list[dict]: moves 列表
        - Agent: 嵌套的内部 agent（会递归调用）
    """

    def _obs_get(self, obs: dict, key: str, default=None):
        if isinstance(obs, dict):
            return obs.get(key, default)
        return getattr(obs, key, default)

    def _player_id(self, obs: dict) -> int:
        return int(self._obs_get(obs, "player", 0) or 0)

    @abstractmethod
    def __init__(self, config : dict | None = None, iner: KaggleAgent | None = None, callback: Callable[[float, int], None] | None = None) -> None:
        """初始化 agent。

        参数:
            config: 配置信息
            iner: 内部 agent
        """


    @abstractmethod
    def __call__(self, obs: dict, config: dict | None = None , outer: KaggleAgent | None = None) -> list[dict]:
        """执行推理。

        参数:
            obs: 游戏观察
            config: 配置信息
            outer: 外部 agent

        返回:
            moves 列表
        """
        raise NotImplementedError
```

## [MD]
# 随机

## [CODE]
```python
"""随机 Agent。"""
from typing import Callable

import math
import random

from kaggle_environments.envs.orbit_wars.orbit_wars import Planet

class RandomAgent(KaggleAgent):
    """随机动作的 Agent。"""

    def __init__(self, config : dict | None = None, iner: KaggleAgent | None = None, callback: Callable[[float, int], None] | None = None) -> None:
        return

    def __call__(self, obs: dict, config: dict | None = None, outer: KaggleAgent | None = None) -> list[dict]:
        moves = []
        player = obs.get("player", 0)
        planets = [Planet(*p) for p in obs.get("planets", [])]
        for p in planets:
            if p.owner == player and p.ships > 0:
                angle = random.uniform(0, 2 * math.pi)
                ships = p.ships // 2
                if ships >= 20:
                    moves.append([p.id, angle, ships])
        return moves
```

## [MD]
# 初学者示例

## [CODE]
```python
from kaggle_environments.envs.orbit_wars.orbit_wars import Planet , CENTER, ROTATION_RADIUS_LIMIT
import math
from typing import Callable

class StarterAgent(KaggleAgent):
    """Starter Agent，优先攻击静态行星。"""

    def __init__(self, config: dict | None = None, iner: KaggleAgent | None = None, callback: Callable[[float, int], None] | None = None) -> None:
        return

    def __call__(self, obs: dict, config: dict | None = None, outer: KaggleAgent | None = None) -> list[dict]:
        moves = []
        player = obs.get("player", 0)
        planets = [Planet(*p) for p in obs.get("planets", [])]

        # Find static planets (orbital_radius + planet_radius >= ROTATION_RADIUS_LIMIT)
        static_targets = []
        for p in planets:
            orbital_r = math.sqrt((p.x - CENTER) ** 2 + (p.y - CENTER) ** 2)
            if orbital_r + p.radius >= ROTATION_RADIUS_LIMIT and p.owner != player:
                static_targets.append(p)

        my_planets = [p for p in planets if p.owner == player]
        for mp in my_planets:
            if mp.ships <= 0:
                continue
            # Find closest static planet not owned by us
            closest = None
            min_dist = float("inf")
            for t in static_targets:
                dist = math.sqrt((mp.x - t.x) ** 2 + (mp.y - t.y) ** 2)
                if dist < min_dist:
                    min_dist = dist
                    closest = t

            if closest:
                angle = math.atan2(closest.y - mp.y, closest.x - mp.x)
                ships = mp.ships // 2
                if ships >= 20:
                    moves.append([mp.id, angle, ships])

        return moves
```

## [MD]
# 计时器

## [CODE]
```python
from typing import Callable
import time
import logging

class TimedAgent(KaggleAgent):
    """包装 agent 函数，记录耗时和错误。"""

    def __init__(self, config : dict | None = None, iner: KaggleAgent | None = None, callback: Callable[[dict, float, int], None] | None = None) -> None:
        self.iner = iner
        self.ms = -1
        self.errors = 0
        self.callback = callback

    def __call__(self, obs: dict, config: dict | None = None , outer: KaggleAgent | None = None) -> list[dict]:
        start = time.perf_counter()
        try:
            if self.iner is None:
                raise ValueError("TimedAgent requires an inner agent to function.")
            # 调用实际的执行函数
            self.ms = 0
            moves = self.iner(obs, config, outer = self)
            return moves
        except Exception as e:
            self.errors += 1
            logging.error(f"Agent error: {e}")
            return []
        finally:
            self.ms = (time.perf_counter() - start) * 1000
            self.callback(obs, self.ms, self.errors) if self.callback else None
```

## [MD]
main.py

## [CODE]
```python
def print_act_log(obs: dict, ms: float, errors: int) -> None:
    print(f"Player: {obs.get('player', 'Unknown')}, Agent took {ms:.2f} ms, errors: {errors}")

agent = TimedAgent(config=None, iner=StarterAgent(), callback=print_act_log)

__all__ = ["agent"]
```

## [MD]
Notebook

## [MD]
# kaggle-environments run --environment orbit_wars --agents main.py random --debug True
