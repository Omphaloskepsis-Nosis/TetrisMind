# TetrisMind P4

本仓库当前只包含 P4“实验调参”模块：遗传算法调权重、并行批量对局、指标统计、
可视化报告和实验产物。

## 快速运行

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

- `exp/`：P4 批量对局、GA、统计和报告
- `tests/`：P4 单元测试及外部引擎/策略拼接模拟
- `exp/results/p4_seed42/`：固定种子实验报告和原始指标
- `TetrisMind-feature-p4-experiment.zip`：可直接提交的 P4 源码包

与真实 P1/P3 拼接时的可选字段、后端切换和权重键名见
[`exp/README.md`](exp/README.md)。
