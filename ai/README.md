# TetrisMind P3：AI 决策

- `features.py`：列高、空洞、起伏、总高度及行列转换六维特征
- `search.py`：当前方块落点枚举与下一方块双层搜索，默认限时 75 ms
- `policy.py`：缓存目标落点，依次返回旋转、左右移动和硬降动作

独立验证：

```powershell
.\.venv\Scripts\python.exe -m ai.demo
```

完整界面：

```powershell
.\.venv\Scripts\python.exe main.py --mode ai
```

`policy(state, weights, time_limit_ms)` 必须返回 `contracts.Action`。
`contracts.Engine.auto_step()` 用该策略完成一个方块，P4 批量实验也走这条路径。
