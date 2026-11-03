# TetrisMind P4：实验调参

P4 负责遗传算法调权重、并行批量对局、指标统计和实验报告。模块既能调用真实的
P1 引擎与 P3 策略，也能在两者尚未合并时使用确定性内置后端独立运行。

## 独立运行

```powershell
.\.venv\Scripts\python.exe -m exp.demo
```

快速冒烟演示：

```powershell
.\.venv\Scripts\python.exe -m exp.demo --generations 3 --population 6 --games 1 --workers 1
```

默认运行 30 代、每代 16 个权重、每个候选打 2 局，输出到
`artifacts/p4_demo/`：

- `metrics.json`：默认权重和调参后权重聚合指标
- `history.csv`：每一代最佳/平均适应度和最佳权重
- `games.csv`：逐局消行与得分
- `fitness_curve.png`：进化曲线
- `metrics_comparison.png`：调参前后核心指标
- `game_distribution.png`：逐局分布
- `weights_heatmap.png`：最佳权重变化
- `report.html`：内嵌四张图的自包含报告
- `best_weights.json`：可复制给 P3 的最佳权重
- `checkpoint.json`：每代自动更新的断点与结果

结果由 `--seed` 完全确定。相同 seed、局数和权重会得到相同指标。

## 公共接口

```python
from exp import evaluate

metrics = evaluate(weights={"lines": 9, "holes": 7}, seed=42, n=10)
print(metrics.lines_mean, metrics.score_mean, metrics.game_lines)
```

`evaluate(weights, seed, n) -> Metrics`。第 `i` 局使用 `seed + i`；让默认权重
和调参权重传相同的 `seed/n`，就能做配对比较。非法局数会明确抛出
`ValueError`。

## 与 P1/P3 拼接

实验层的调用关系如下：

```text
exp.runner.evaluate
  -> contracts.Engine(seed=seed).reset()
  -> ai.policy.policy(state, weights)
  -> contracts.Engine.step(action)
  -> Metrics
```

只要 P1/P3 满足冻结契约，P4 默认会自动选择外部后端。也可显式指定模块：

```powershell
.\.venv\Scripts\python.exe -m exp.demo `
  --backend external `
  --engine contracts:Engine `
  --policy ai.policy:policy
```

融合时需要检查三点：

1. `Engine` 可接受 `seed=` 关键字，且 `reset()` 返回带 `board` 的 State。
2. `policy(state, weights)` 返回 `contracts.Action`。若策略仅接受
   `policy(state)`，适配器也会兼容。
3. 引擎结束状态使用 `game_over`、`done`、`is_over`、`terminal` 或
   `status="over"` 之一；累计消行使用 `total_lines`、`lines_cleared` 或
   `lines`；得分字段为 `score`；方块数为 `pieces` 或 `piece_count`。

P3 只要支持权重字典即可参与 GA。六个基因及推荐默认值为：

```json
{
  "lines": 9.0,
  "holes": 7.0,
  "height": 0.5,
  "bumpiness": 0.5,
  "wells": 0.3,
  "landing_height": 0.1
}
```

若 P3 使用不同键名，应在 `ai.policy` 内把该字典映射为搜索特征，避免在 P4
写分支；这是保持接口冻结的关键。

## 测试

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

测试覆盖确定性、进程并行、公开 Metrics、GA 冒烟运行、四张图和 HTML 报告，
还通过模拟 P1/P3 模块验证外部拼接路径。
