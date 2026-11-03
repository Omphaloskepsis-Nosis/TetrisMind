# TetrisMind

俄罗斯方块 AI 与遗传算法调参项目。当前仓库包含 P2 渲染交互和 P4 实验调参；
P1 规则引擎与 P3 AI 决策仍以冻结的 `contracts.py` 接口并行开发。

## P4 快速运行

```powershell
.\.venv\Scripts\python.exe -m exp.demo
```

默认运行 30 代 GA，并在 `artifacts/p4_demo/` 生成指标、四张图和 HTML 报告。

本次 30 代固定种子结果已经提交在
[`exp/results/p4_seed42/report.html`](exp/results/p4_seed42/report.html)，可直接用
浏览器打开。复现命令：

```powershell
.\.venv\Scripts\python.exe -m exp.demo `
  --generations 30 --population 16 --games 2 --seed 42 `
  --workers 4 --max-pieces 80 --output exp/results/p4_seed42
```

结果：默认权重平均消行 30.50、平均得分 3300；GA 调参后平均消行 31.00、
平均得分 3600。相同 seed 重复运行的权重、逐局结果和每代历史完全一致。

## 环境

PyCharm 项目解释器：`.venv/Scripts/python.exe`。依赖安装：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

完整测试：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 目录

- `contracts.py`：P1-P4 共享契约
- `ui/`：P2 渲染、输入和回放
- `exp/`：P4 批量对局、GA、统计和报告
- `tests/`：P4 单元测试及 P1/P3 拼接模拟
- `TetrisMind_P2_终极版说明书.md`：P2 使用说明

P4 与真实 P1/P3 的拼接字段、自动后端切换和权重键名见
[`exp/README.md`](exp/README.md)。
