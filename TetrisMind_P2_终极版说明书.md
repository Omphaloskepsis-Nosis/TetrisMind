# TetrisMind P2 — 渲染与交互模块终极版说明书

> **版本**：3.0（终极版）  
> **适用**：TetrisMind 项目（Python 3.10+，pygame 2.6.1）  
> **生成日期**：2026-10-18  
> **模块路径**：`ui/` 包（`render.py` · `input.py` · `replay.py` · `__main__.py`）

---

## 1. 模块概述

P2 是 TetrisMind 的 **渲染与交互层**（Presentation Layer），位于 `ui/` 包下，职责清晰地划分为四个文件：

| 文件 | 职责 | 核心类/函数 |
|---|---|---|
| `ui/render.py` | 只读渲染：棋盘、方块、HUD、动画、霓虹主题 | `Renderer` · `LineClearAnimation` · `FloatTextAnimation` · `_sf()` |
| `ui/input.py` | 输入分发：键盘 → `Action` 枚举，模式切换 | `InputHandler` · `InputMode` · `_load_ai_policy()` |
| `ui/replay.py` | 确定性回放：JSON 加载、倍速、暂停/重启 | `ReplayPlayer` |
| `ui/__main__.py` | 统一入口：argparse 解析、主循环、响应式缩放 | `run_render/input/replay_mode` · `_setup_pygame` · `_scale_and_blit` |

**依赖链**：

```
contracts.py  ← 唯一契约来源（State / Action / Engine）
     ↑
ui/render.py   ui/input.py   ui/replay.py   ← P2 渲染与交互
     ↑
  __main__.py  ← 统一入口（python -m ui）
```

---

## 2. 只读红线架构

### 2.1 核心约束

> **`render.py` 和 `input.py` 不得对 `state` 任何属性赋值，不得调用 `engine.step()` 或任何引擎变更方法。**

| 模块 | 允许操作 | 禁止操作 |
|---|---|---|
| `render.py` | `getattr(state, ...)` 只读读取 | 任何赋值、`engine.step()` |
| `input.py` | 返回 `Action` 枚举 | 调用 `engine.step()`、修改 state |
| `replay.py` | 调用 `engine.step(action)` | 修改 `contracts.py` |
| `__main__.py` | 调用 `engine.step(action)`（input 模式） | 直接修改 state 属性 |

### 2.2 防御性读取

所有 `state.xxx` 访问统一使用 `getattr(state, 'xxx', 默认值)`，确保未来 P1 引擎字段变更时不崩溃：

```python
# render.py 中的防御性读取示例
score = int(getattr(state, 'score', 0) or 0)
level = int(getattr(state, 'level', 0) or 0)
lines = int(getattr(state, 'total_lines', 0) or 0)
hold_val = getattr(state, 'hold_piece', None)
queue = getattr(state, 'next_queue', []) or []

# 棋盘越界保护
cell_val = state.board[r][c] if r < len(state.board) and c < len(state.board[r]) else 0
```

### 2.3 响应式居中渲染架构

采用 **固定 game_surface + 等比缩放** 方案，彻底解决窗口拉伸变形问题：

```
┌─────────────────────────────────────────┐
│           实际窗口（可任意大小）            │
│                                         │
│    ┌───────────────────────────────┐    │
│    │   game_surface (600×800)      │    │
│    │   ← 所有渲染操作的目标          │    │
│    │   ← 逻辑分辨率固定不变          │    │
│    └───────────────────────────────┘    │
│                                         │
│   scale = min(win_w/600, win_h/800)    │
│   scaled = transform.scale(surface)    │
│   blit 居中                             │
└─────────────────────────────────────────┘
```

**实现细节**（`__main__.py`）：

1. `_setup_pygame()` 创建固定 `600×800` 的 `game_surface`
2. `Renderer` 所有绘制操作只针对 `game_surface`
3. 每帧 `_scale_and_blit()` 计算缩放比例，等比缩放后居中 blit
4. `VIDEORESIZE` 事件自动触发重新缩放，画面永远居中不变形
5. 支持 `F11` 全屏切换，全屏时同样保持等比居中

---

## 3. 运行方式

### 3.1 统一入口

```bash
python -m ui --mode <mode> [options]
```

| 命令 | 说明 |
|---|---|
| `python -m ui --mode render` | 纯渲染观察模式 |
| `python -m ui --mode input` | 人机交互模式（支持键盘输入） |
| `python -m ui --mode replay` | 回放模式（默认 20 步固定动作） |
| `python -m ui --mode replay --replay-file path.json` | 指定回放文件 |
| `python -m ui --mode replay --speed 8` | 8 倍速回放 |
| `python -m ui --mode all` | 依次运行全部模式 |

### 3.2 通用参数

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `--headless` | flag | 关闭 | 无头模式，不创建真实窗口 |
| `--frames N` | int | 60 | headless 模式下运行的帧数 |
| `--speed N` | int | 1 | 回放倍速（仅 replay 模式） |
| `--seed N` | int | 42 | 引擎随机种子 |
| `--replay-file PATH` | str | 无 | 回放 JSON 文件路径 |

---

## 4. 快捷键说明

### 4.1 全局快捷键

| 按键 | 功能 | 适用模式 |
|---|---|---|
| `ESC` | 关闭窗口 | 全部 |
| `F11` | 全屏 / 窗口切换 | 全部 |
| `TAB` | 切换 HUMAN ⇄ AI 模式 | input |

### 4.2 游戏操作（HUMAN 模式）

| 按键 | 动作 |
|---|---|
| `←` `→` | 左 / 右移动 |
| `↓` | 加速下落 |
| `↑` / `X` | 旋转 |
| `空格` | 硬降（Hard Drop） |
| `C` / `Shift` | 暂存（Hold） |

> **DAS/ARR 长按连发**：通过 `pygame.key.set_repeat(200, 50)` 实现。按住 ←/→ 200ms 后以 50ms 间隔连续触发，手感流畅。

### 4.3 回放控制（REPLAY 模式）

| 按键 | 功能 |
|---|---|
| `P` | 暂停 / 继续 |
| `R` | 重启回放（从头开始） |
| `1` | 1 倍速 |
| `2` | 2 倍速 |
| `4` | 4 倍速 |
| `8` | 8 倍速 |

> 暂停时屏幕中央显示 **PAUSED** 覆盖层；回放结束时显示 **REPLAY FINISHED**。

### 4.4 模式切换说明

- **TAB 键**：在 HUMAN 和 AI 之间循环切换（边沿触发防抖，按住不重复）
- 切换时 MODE 文字执行 0.2s Alpha 淡入动画（0→255）
- AI 模式自动加载 `ai.policy`，导入失败则降级为 `NOOP`
- AI/REPLAY 模式下按键提示置灰，显示 `(KEYS DISABLED)`

---

## 5. 无头测试验证（Headless）

### 5.1 原理

在 `import pygame` 之前注入环境变量：

```python
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
```

创建 `1×1` 最小 surface，主循环改为固定 N 帧后自动退出，返回码 0。

### 5.2 验证命令

```bash
python -m ui --mode render  --headless --frames 2    # 静态骨架
python -m ui --mode render  --headless --frames 30   # 消行动画
python -m ui --mode input   --headless --frames 2    # 三模式分发
python -m ui --mode replay  --speed 8 --headless --frames 5  # 倍速回放
python -m ui --mode all     --headless --frames 2    # 全量检查
```

> 所有命令返回码必须为 **0**，作为后续 P1 引擎迭代的回归基准。

### 5.3 字体系统容错

Dummy driver 下 `pygame.font.SysFont()` 可能因 Windows 注册表枚举干扰抛出 `TypeError`。`_sf()` 和 `_make_font()` 使用 `try/except` 兜底 fallback 到 `Font(None, size)`，确保自动化测试不崩溃。

---

## 6. 视觉设计

### 6.1 赛博朋克霓虹主题

| 元素 | 配色 |
|---|---|
| 背景 | 极深蓝灰黑 `(20, 24, 34)` |
| 棋盘 | 纯黑 `(10, 10, 15)` |
| 网格线 | 暗灰蓝 `(40, 45, 60)` |
| 面板 | 深灰 `(30, 35, 48)` + 偏移阴影 |
| 棋盘外框 | 亮青 `(0, 255, 255)` 3px |
| MODE 文字 | 荧光黄 `(255, 230, 0)` 52pt bold |
| 回放信息 | 亮青 `(0, 255, 255)` |
| 方块颜色 | 高饱和霓虹色（青/蓝/黄/红/绿/紫/橙） |

### 6.2 方块立体渲染（4 层绘制）

每个方块单元格包含 **5 层绘制**：

1. **纯色填充**：高饱和霓虹色（`PIECE_COLORS`），`inflate(-2, -2)` 留出 1px 黑缝
2. **霓虹内发光**：白色半透明内边框（α=55），`inflate(-2, -2)` 再缩进，模拟灯管效果
3. **白色描边**：1px 白色外轮廓
4. **左上高光**：白色 SRCALPHA（α=165，约 1/5 宽 × 1/7 高）
5. **右下阴影**：黑色 SRCALPHA（α=130，约 1/5 宽 × 1/7 高）

```
rect(30×30)
├── inflate(-2,-2) 纯色填充   ← 饱和霓虹色
│   ├── inflate(-2,-2) SRCALPHA 白色内发光 α=55  ← 霓虹灯管层
│   └── 1px 白色描边                           ← 外轮廓
├── 左上白色高光   α=165 (~1/5 宽, ~1/7 高)
└── 右下黑色阴影   α=130
```

### 6.3 面板悬浮感（磨砂玻璃）

所有大面板（HUD、HOLD/NEXT）使用 `_draw_panel_with_shadow()`：

1. 偏移 +4px / +6px 绘制半透明黑阴影（α=90）
2. 主面板填充 `COLOR_PANEL` + 外描边 `COLOR_PANEL_BORDER`（`border_radius=12`）
3. 内侧 1px 描边（`inflate(-3, -3)`），颜色 `(50, 56, 74)`，模拟"磨砂玻璃"质感

### 6.4 消行动画三阶段

| 阶段 | 时间 | 效果 |
|---|---|---|
| 闪白 | 0–0.12s | 20Hz 快速闪烁白色（α=210），`flash_visible` 基于 `int(elapsed*20)%2` |
| 横向收缩 | 0.12–0.22s | 从两侧向中间收缩，白色覆盖（α=180），`shrink = int(BOARD_W * fade_t)` |
| 淡出 | 0.22–0.30s | 完全收缩 + alpha 线性衰减到 0 |

### 6.5 消行飘字

消行时屏幕中央生成 `FloatTextAnimation`，1 秒内向上飘 80px，alpha 从 255 衰减到 0。分数根据消行数查 `CLEAR_SCORE_TABLE = [0, 100, 300, 500, 800]`。

### 6.6 字体系统

全局使用 `pygame.font.SysFont(['Microsoft YaHei', 'Segoe UI', 'Arial'], size, bold=...)`，fallback 到 `Font(None, size)`。

| 用途 | 字号 | 粗体 |
|---|---|---|
| 正文/按键提示 | 18pt | 否 |
| HUD 标签 | 18pt | 否 |
| HUD 数值 | 48pt | **是** |
| MODE 文字 | 52pt | **是** |
| PAUSED 覆盖层 | 72pt | **是** |
| REPLAY FINISHED | 54pt | **是** |

---

## 7. 回放系统

### 7.1 JSON 格式

```json
{
  "seed": 42,
  "actions": ["LEFT", "ROTATE", "HARD_DROP", ...],
  "version": 1
}
```

### 7.2 确定性保证

- `ReplayPlayer` 内部无 `random` / `time.time()` 调用
- 推进完全依赖 `seed + action 序列`
- 动作解码同时支持字符串名（`"LEFT"`）和整数编码（`1`）
- `_decode_action()` 容错：未知动作默认 `NOOP`

### 7.3 倍速语义

> "每渲染帧执行 N 次 `engine.step(action)`，只绘制最后一次结果。"

```python
def step_frame(self) -> State:
    if self._state is None:
        self._state = self.engine.reset()
    if self.paused:
        return self._state
    for _ in range(self.speed):
        if self._action_index >= len(self.actions):
            break
        action = self.actions[self._action_index]
        self._state = self.engine.step(action)
        self._action_index += 1
    return self._state
```

### 7.4 回放专属 UI

- 顶栏右侧显示 `SPEED Nx` 和 `PROGRESS: xx/xxx`
- 回放结束时屏幕中央显示 `REPLAY FINISHED` + `Press R to restart`
- 暂停时屏幕中央显示 `PAUSED` + `Press P to resume`

---

## 8. 人机协作说明

### 8.1 人工设计的核心架构决策

- **只读红线约束**：render/input 层绝不修改引擎状态
- **contracts.py 契约驱动**：State / Action / Engine 的唯一来源
- **消行动画独立队列**：引擎不感知动画时间，渲染层独立管理
- **渲染层倍速语义**：倍速在 P2 层实现，不污染引擎
- **JSON 回放格式**：确定性回放的标准数据格式
- **Headless 验证正确时序**：dummy driver 注入在 pygame import 之前
- **响应式 game_surface 架构**：固定逻辑分辨率 + 等比缩放居中
- **赛博朋克霓虹主题配色方案**：极深蓝灰黑 + 亮青 + 荧光黄
- **面板悬浮阴影 + 磨砂玻璃双层描边**
- **方块霓虹内发光 + 高光阴影 5 层绘制**
- **DAS/ARR 长按连发手感调优**
- **消行动画三阶段时序精确控制**
- **AI 策略降级机制**：导入失败自动降级为 NOOP

### 8.2 Trae AI 加速的环节

- 类骨架生成与契约探查脚本
- 防御性读取注入（`getattr` 安全访问）
- `SysFont` / dummy driver 兼容性修复（`_sf` / `_make_font` fallback）
- `_setup_pygame()` 公共辅助函数抽取
- `UnboundLocalError` 状态管理 bug 修复
- 响应式 `_scale_and_blit()` 居中缩放实现
- 全部 headless 验证命令自动化执行与修复

---

## 附录：项目结构

```
TetrisMind/
├── contracts.py                 ← 唯一契约来源（State / Action / Engine）
├── TetrisMind_P2_终极版说明书.md  ← 本文件
└── ui/
    ├── __init__.py              ← 包标记
    ├── __main__.py              ← 统一入口（~290 行）
    ├── render.py                ← Renderer + 动画类（~387 行）
    ├── input.py                 ← InputHandler + InputMode（~93 行）
    └── replay.py                ← ReplayPlayer（~86 行）
```

**总计**：4 个代码文件，约 856 行。

---

*本文档基于 TetrisMind 项目 ui/ 目录最新代码生成，与 contracts.py 契约保持同步。*