from contracts import State, Action
from ai.policy import policy, DEFAULT_WEIGHTS
from ai.search import find_best_move


def run_demo():
    print("=" * 40)
    print("P3 (C AI决策) 独立模块演示")
    print("=" * 40)

    fake_board = [[0] * 10 for _ in range(20)]
    for r in range(18, 20):
        for c in range(10):
            fake_board[r][c] = 1
    fake_board[17][0] = 1
    fake_board[16][0] = 1

    test_state = State(
        board=fake_board,
        current_piece=(3, 0),
        hold_piece=None,
        next_queue=[1, 2],
        cleared_lines=[]
    )

    print("当前 AI 权重参数:", DEFAULT_WEIGHTS)
    print("正在执行 2 层搜索寻找最优落点...")

    import time
    t0 = time.perf_counter()
    best_score, target_rot, target_col = find_best_move(test_state, DEFAULT_WEIGHTS)
    t1 = time.perf_counter()

    print(f"[OK] 搜索完成！")
    print(f" - 最优目标列: {target_col}")
    print(f" - 目标旋转次数: {target_rot}")
    print(f" - 预估评分: {best_score:.2f}")
    print(f" - 计算耗时: {(t1 - t0) * 1000:.2f} ms (要求 < 80ms)")

    action = policy(test_state)
    print(f"[OK] policy() 返回给 P2 的执行动作: {action}")

    print("\n测试降级机制 (传入无效 State)...")
    bad_action = policy(None)
    print(f"[OK] 异常兜底返回动作: {bad_action} (期望为 Action.NOOP)")


if __name__ == "__main__":
    run_demo()
