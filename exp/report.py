"""CSV/JSON output and the four-chart HTML experiment report."""

from __future__ import annotations

import base64
import csv
from html import escape
import json
import os
from pathlib import Path
from typing import Any

PROJECT_CACHE = Path(__file__).resolve().parent.parent / ".cache" / "matplotlib"
PROJECT_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_CACHE))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

from exp.metrics import Metrics, WEIGHT_NAMES  # noqa: E402


CHINESE_FONTS = ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS")


def configure_chinese_font() -> str:
    available = {font.name for font in font_manager.fontManager.ttflist}
    selected = next((name for name in CHINESE_FONTS if name in available), "DejaVu Sans")
    plt.rcParams["font.sans-serif"] = [selected, "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    return selected


def _save_fitness_chart(history: list[dict[str, Any]], destination: Path) -> None:
    generations = [record["generation"] for record in history]
    best = [record["best_fitness"] for record in history]
    average = [record["mean_fitness"] for record in history]
    figure, axis = plt.subplots(figsize=(9, 4.8))
    axis.plot(generations, best, color="#0c8f8f", linewidth=2.5, marker="o", label="最佳适应度")
    axis.plot(generations, average, color="#ef8354", linewidth=2.0, label="种群平均")
    axis.set_title("遗传算法进化曲线")
    axis.set_xlabel("代数")
    axis.set_ylabel("适应度（消行数 + 分数奖励）")
    axis.grid(alpha=0.22)
    axis.legend()
    figure.tight_layout()
    figure.savefig(destination, dpi=160)
    plt.close(figure)


def _save_comparison_chart(baseline: Metrics, tuned: Metrics, destination: Path) -> None:
    labels = ("平均消行", "平均得分 / 100")
    baseline_values = (baseline.lines_mean, baseline.score_mean / 100.0)
    tuned_values = (tuned.lines_mean, tuned.score_mean / 100.0)
    positions = range(len(labels))
    width = 0.34
    figure, axis = plt.subplots(figsize=(8, 4.6))
    axis.bar([x - width / 2 for x in positions], baseline_values, width, label="默认权重", color="#8497b0")
    axis.bar([x + width / 2 for x in positions], tuned_values, width, label="GA 调参", color="#0c8f8f")
    axis.set_xticks(list(positions), labels)
    axis.set_title("调参前后核心指标")
    axis.grid(axis="y", alpha=0.2)
    axis.legend()
    figure.tight_layout()
    figure.savefig(destination, dpi=160)
    plt.close(figure)


def _save_distribution_chart(baseline: Metrics, tuned: Metrics, destination: Path) -> None:
    figure, axis = plt.subplots(figsize=(7, 4.6))
    axis.boxplot(
        [baseline.game_lines, tuned.game_lines],
        tick_labels=["默认权重", "GA 调参"],
        patch_artist=True,
        boxprops={"facecolor": "#d7e4ee"},
        medianprops={"color": "#ef8354", "linewidth": 2},
    )
    for index, values in enumerate((baseline.game_lines, tuned.game_lines), start=1):
        axis.scatter(
            [index] * len(values),
            values,
            alpha=0.6,
            color="#0c8f8f" if index == 2 else "#6b7790",
            zorder=3,
        )
    axis.set_title("逐局消行分布")
    axis.set_ylabel("消行数")
    axis.grid(axis="y", alpha=0.2)
    figure.tight_layout()
    figure.savefig(destination, dpi=160)
    plt.close(figure)


def _save_weights_chart(history: list[dict[str, Any]], destination: Path) -> None:
    matrix = [
        [record["best_weights"][name] for record in history]
        for name in WEIGHT_NAMES
    ]
    figure, axis = plt.subplots(figsize=(10, 4.8))
    image = axis.imshow(matrix, aspect="auto", cmap="YlGnBu")
    axis.set_yticks(range(len(WEIGHT_NAMES)), labels=WEIGHT_NAMES)
    axis.set_xlabel("代数")
    axis.set_title("各代最佳权重变化")
    figure.colorbar(image, ax=axis, label="权重")
    figure.tight_layout()
    figure.savefig(destination, dpi=160)
    plt.close(figure)


def write_metrics_files(
    output_dir: str | Path,
    baseline: Metrics,
    tuned: Metrics,
    history: list[dict[str, Any]],
) -> None:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "metrics.json").write_text(
        json.dumps(
            {"baseline": baseline.as_dict(), "tuned": tuned.as_dict()},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    with (destination / "history.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            ["generation", "best_fitness", "mean_fitness", "best_lines", *WEIGHT_NAMES]
        )
        for record in history:
            writer.writerow(
                [
                    record["generation"],
                    record["best_fitness"],
                    record["mean_fitness"],
                    record["best_lines"],
                    *(record["best_weights"][name] for name in WEIGHT_NAMES),
                ]
            )
    with (destination / "games.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["policy", "game", "lines", "score"])
        for policy, metric in (("baseline", baseline), ("tuned", tuned)):
            for index, (lines, score) in enumerate(
                zip(metric.game_lines, metric.game_scores),
                start=1,
            ):
                writer.writerow([policy, index, lines, score])


def _embedded_image(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _weight_table(weights: dict[str, float]) -> str:
    rows = "".join(
        f"<tr><td>{escape(name)}</td><td>{weights[name]:.4f}</td></tr>"
        for name in WEIGHT_NAMES
    )
    return f"<table><thead><tr><th>权重</th><th>数值</th></tr></thead><tbody>{rows}</tbody></table>"


def render_report(
    *,
    output_dir: str | Path,
    baseline: Metrics,
    tuned: Metrics,
    history: list[dict[str, Any]],
    seed: int,
) -> Path:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    font = configure_chinese_font()
    chart_paths = {
        "fitness": destination / "fitness_curve.png",
        "comparison": destination / "metrics_comparison.png",
        "distribution": destination / "game_distribution.png",
        "weights": destination / "weights_heatmap.png",
    }
    _save_fitness_chart(history, chart_paths["fitness"])
    _save_comparison_chart(baseline, tuned, chart_paths["comparison"])
    _save_distribution_chart(baseline, tuned, chart_paths["distribution"])
    _save_weights_chart(history, chart_paths["weights"])
    write_metrics_files(destination, baseline, tuned, history)

    improvement = tuned.lines_mean - baseline.lines_mean
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TetrisMind P4 实验报告</title>
  <style>
    body {{ margin: 0; background: #edf3f7; color: #17212b;
            font-family: "Microsoft YaHei", sans-serif; line-height: 1.65; }}
    main {{ max-width: 1120px; margin: 32px auto; padding: 32px;
            background: white; box-shadow: 0 12px 36px rgba(38, 58, 78, .13); }}
    h1 {{ color: #087f7f; margin-bottom: 4px; }}
    h2 {{ margin-top: 36px; border-left: 5px solid #ef8354; padding-left: 12px; }}
    .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }}
    .card {{ background: #f4f8fa; border: 1px solid #d7e2e9; padding: 16px; border-radius: 8px; }}
    .value {{ font-size: 28px; font-weight: 700; color: #087f7f; }}
    img {{ width: 100%; border: 1px solid #d7e2e9; margin-top: 12px; }}
    .two {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid #d7e2e9; padding: 9px; text-align: left; }}
    code {{ background: #eef3f6; padding: 2px 5px; }}
  </style>
</head>
<body><main>
  <h1>TetrisMind · P4 实验调参报告</h1>
  <p>固定可复现随机种子 <code>{seed}</code>；默认权重与 GA 调参结果使用相同对局种子。</p>
  <div class="stats">
    <div class="card"><div>默认权重平均消行</div><div class="value">{baseline.lines_mean:.2f}</div></div>
    <div class="card"><div>GA 调参平均消行</div><div class="value">{tuned.lines_mean:.2f}</div></div>
    <div class="card"><div>平均消行变化</div><div class="value">{improvement:+.2f}</div></div>
  </div>
  <h2>1. 进化曲线</h2>
  <img src="{_embedded_image(chart_paths['fitness'])}" alt="进化曲线">
  <h2>2. 指标对比</h2>
  <img src="{_embedded_image(chart_paths['comparison'])}" alt="指标对比">
  <h2>3. 逐局分布</h2>
  <img src="{_embedded_image(chart_paths['distribution'])}" alt="逐局分布">
  <h2>4. 最佳权重变化</h2>
  <img src="{_embedded_image(chart_paths['weights'])}" alt="权重热图">
  <div class="two">
    <section><h2>默认权重</h2>{_weight_table(baseline.weights)}</section>
    <section><h2>GA 最佳权重</h2>{_weight_table(tuned.weights)}</section>
  </div>
  <h2>复现信息</h2>
  <p>后端：<code>{escape(tuned.backend)}</code>；GA 最佳适应度：
  <code>{tuned.fitness:.4f}</code>；绘图字体：<code>{escape(font)}</code>。</p>
  <p>运行命令：<code>python -m exp.demo --seed {seed}</code></p>
</main></body></html>"""
    report_path = destination / "report.html"
    report_path.write_text(html, encoding="utf-8")
    return report_path
