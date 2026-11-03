import sys
from pathlib import Path

from contracts import Action, State

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame

BASE_W = 600
BASE_H = 800


def _sf(families: list[str], size: int, bold: bool = False) -> pygame.font.Font:
    try:
        return pygame.font.SysFont(families, size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)

def _draw_sharp_text(surface: pygame.Surface, text: str, pos: tuple[int, int],
                     color: tuple, font: pygame.font.Font) -> None:
    surf = font.render(text, True, color)
    surface.blit(surf, (int(pos[0]), int(pos[1])))

# ============================================================
# 动态布局计算：标准 10列 × 20行 俄罗斯方块规格（1.5x 放大）
# ============================================================
COLS = 10
ROWS = 20
CELL = 45  # 每格45px（30 * 1.5），确保正方形且清晰可见

# 面板宽度（确保文字有舒适的padding，1.5x 放大）
HUD_LEFT_W = 210
SIDEBAR_W = 210
PANEL_GAP = 15
MARGIN = 24
TOP_BAR_H = 105

# 游戏区尺寸（严格 10×20 正方形网格）
BOARD_W = COLS * CELL   # 450px
BOARD_H = ROWS * CELL   # 900px

# 窗口总宽度 = 左面板 + 间隙 + 游戏区 + 间隙 + 右面板 + 两侧边距
BASE_W = MARGIN + HUD_LEFT_W + PANEL_GAP + BOARD_W + PANEL_GAP + SIDEBAR_W + MARGIN  # 1053px
# 窗口总高度 = 顶部栏 + 上边距 + 游戏区 + 下边距
BASE_H = TOP_BAR_H + MARGIN + BOARD_H + MARGIN  # 1053px

# 各区域坐标（动态计算，非硬编码）
HUD_LEFT_X = MARGIN
HUD_LEFT_Y = TOP_BAR_H + MARGIN
HUD_LEFT_H = BOARD_H

BOARD_X = HUD_LEFT_X + HUD_LEFT_W + PANEL_GAP
BOARD_Y = TOP_BAR_H + MARGIN

SIDEBAR_X = BOARD_X + BOARD_W + PANEL_GAP
SIDEBAR_Y = TOP_BAR_H + MARGIN
SIDEBAR_H = BOARD_H

CLEAR_SCORE_TABLE = [0, 100, 300, 500, 800]

# 赛博朋克/现代深色色彩系统
COLOR_BG = (30, 34, 45)
COLOR_BG_GRADIENT = (22, 26, 36)
COLOR_BOARD_BG = (18, 20, 28)
COLOR_GRID = (58, 64, 80, 120)
COLOR_GRID_FAINT = (58, 64, 80, 100)
COLOR_PANEL = (35, 40, 55, 140)
COLOR_PANEL_BORDER = (80, 180, 255, 160)
COLOR_PANEL_INNER_GLOW = (255, 255, 255, 30)
COLOR_BOARD_BORDER = (0, 220, 220)
COLOR_BOARD_BORDER_GLOW = (0, 255, 255, 50)
COLOR_TEXT = (220, 225, 240)
COLOR_TEXT_DIM = (130, 135, 150)
COLOR_TEXT_BRIGHT = (230, 235, 250)
COLOR_ACCENT = (0, 230, 230)
COLOR_ACCENT_GLOW = (0, 255, 255, 60)
COLOR_ACCENT2 = (255, 230, 60)
COLOR_VALUE = (255, 240, 80)
COLOR_SHADOW = (0, 0, 0, 80)

PIECE_COLORS = {
    0: (18, 20, 28),
    1: (0, 220, 240),
    2: (70, 110, 240),
    3: (255, 210, 30),
    4: (255, 50, 70),
    5: (50, 230, 110),
    6: (190, 90, 240),
    7: (255, 150, 30),
}


class LineClearAnimation:
    def __init__(self, row_indices: list[int], duration: float = 0.3):
        self.rows = list(row_indices)
        self.duration = duration
        self.elapsed = 0.0

    def update(self, dt: float) -> bool:
        self.elapsed += dt
        return self.elapsed < self.duration

    @property
    def phase(self) -> int:
        if self.elapsed < 0.12:
            return 0
        if self.elapsed < 0.22:
            return 1
        return 2

    @property
    def progress(self) -> float:
        if self.duration <= 0:
            return 1.0
        return min(1.0, self.elapsed / self.duration)

    @property
    def flash_visible(self) -> bool:
        if self.phase != 0:
            return False
        cycle = int(self.elapsed * 20) % 2
        return cycle == 0


class FloatTextAnimation:
    def __init__(self, text: str, center: tuple[int, int], duration: float = 1.0):
        self.text = text
        self.center_x = float(center[0])
        self.center_y = float(center[1])
        self.duration = duration
        self.elapsed = 0.0

    def update(self, dt: float) -> bool:
        self.elapsed += dt
        return self.elapsed < self.duration

    @property
    def progress(self) -> float:
        if self.duration <= 0:
            return 1.0
        return min(1.0, self.elapsed / self.duration)

    @property
    def alpha(self) -> int:
        return int(255 * (1.0 - self.progress))

    @property
    def current_y(self) -> float:
        return self.center_y - 80.0 * self.progress


class Renderer:
    def __init__(self, surface: pygame.Surface,
                 font: pygame.font.Font | None = None,
                 big_font: pygame.font.Font | None = None,
                 value_font: pygame.font.Font | None = None,
                 clock: pygame.time.Clock | None = None):
        self.surface = surface
        _sys = ['Microsoft YaHei', 'Segoe UI', 'Arial']
        self.font = font or _sf(_sys, 18)
        self.big_font = big_font or _sf(_sys, 42, bold=True)
        self.value_font = value_font or _sf(_sys, 52, bold=True)
        self.mode_font = _sf(_sys, 52, bold=True)
        self.clock = clock
        self.mode_label: str = "HUMAN"
        self.mode_name_full: str = "human"
        self.replay_speed: int = 1
        self.replay_progress: tuple[int, int] = (0, 0)
        self.is_replay: bool = False
        self.is_paused: bool = False
        self.replay_finished: bool = False
        self._prev_mode: str | None = None
        self._mode_transition: float = 0.0
        self.line_animations: list[LineClearAnimation] = []
        self.float_texts: list[FloatTextAnimation] = []
        self._breath_phase: float = 0.0

        # 性能优化：缓存
        self._bg_cache: pygame.Surface | None = None
        self._static_text_cache: dict[str, pygame.Surface] = {}
        self._value_cache: dict[str, tuple[int, pygame.Surface]] = {}
        self._label_surfaces: dict[str, pygame.Surface] = {}
        self._controls_surfaces: list[pygame.Surface] = []
        self._sidebar_labels: dict[str, pygame.Surface] = {}
        self._fps_font = _sf(_sys, 22)
        self._label_font = _sf(_sys, 25)
        self._value_font = _sf(_sys, 72, bold=True)
        try:
            self._controls_font = pygame.font.SysFont("consolas", 21)
        except Exception:
            self._controls_font = _sf(["arial", "Microsoft YaHei"], 21)

        self._build_bg_cache()
        self._build_static_text_cache()

    def _build_bg_cache(self) -> None:
        self._bg_cache = pygame.Surface((BASE_W, BASE_H))
        self._bg_cache.fill(COLOR_BG)
        for y in range(0, BASE_H, 4):
            ratio = y / BASE_H
            r = int(COLOR_BG[0] * (1 - ratio) + COLOR_BG_GRADIENT[0] * ratio)
            g = int(COLOR_BG[1] * (1 - ratio) + COLOR_BG_GRADIENT[1] * ratio)
            b = int(COLOR_BG[2] * (1 - ratio) + COLOR_BG_GRADIENT[2] * ratio)
            pygame.draw.line(self._bg_cache, (r, g, b), (0, y), (BASE_W, y))

        for c in range(0, COLS + 1):
            x = BOARD_X + c * CELL
            pygame.draw.line(self._bg_cache, COLOR_GRID_FAINT, (x, BOARD_Y), (x, BOARD_Y + BOARD_H), 2)
        for r in range(0, ROWS + 1):
            y = BOARD_Y + r * CELL
            pygame.draw.line(self._bg_cache, COLOR_GRID_FAINT, (BOARD_X, y), (BOARD_X + BOARD_W, y), 2)

        board_bg = pygame.Rect(BOARD_X, BOARD_Y, BOARD_W, BOARD_H)
        pygame.draw.rect(self._bg_cache, COLOR_BOARD_BG, board_bg)

    def _build_static_text_cache(self) -> None:
        self._sidebar_labels = {
            "HOLD": self.font.render("HOLD", True, COLOR_TEXT_DIM),
            "NEXT": self.font.render("NEXT", True, COLOR_TEXT_DIM),
            "empty": self.font.render("empty", True, (70, 70, 85)),
        }
        header = self._controls_font.render("CONTROLS", True, COLOR_ACCENT)
        self._label_surfaces["CONTROLS"] = header

    def _get_controls_surfaces(self, legend_alpha: int) -> list[pygame.Surface]:
        if self.is_replay:
            hints = ["P       pause", "R       restart", "1/2/4/8 speed"]
        else:
            hints = ["LEFT/RIGHT move", "UP/X      rotate", "SPACE     hard",
                     "C/SHIFT   hold", "TAB       AI/HU", "ESC       quit"]
        result = []
        for line in hints:
            surf = self._controls_font.render(line, True, (180, 185, 200))
            surf.set_alpha(legend_alpha)
            result.append(surf)
        return result

    def _get_value_surface(self, key: str, val: int) -> pygame.Surface:
        cached = self._value_cache.get(key)
        if cached and cached[0] == val:
            return cached[1]
        surf = self._value_font.render(f"{val:,}", True, COLOR_VALUE)
        self._value_cache[key] = (val, surf)
        return surf

    def set_mode(self, label: str, name_full: str, is_replay: bool = False) -> None:
        if self.mode_label != label:
            self._prev_mode = self.mode_label
            self.mode_label = label
            self.mode_name_full = name_full
            self._mode_transition = 0.0
        self.is_replay = is_replay

    def record_clears(self, cleared_rows: list[int]) -> None:
        if cleared_rows:
            n = len(cleared_rows)
            score = CLEAR_SCORE_TABLE[min(n, 4)]
            self.line_animations.append(LineClearAnimation(cleared_rows))
            cx = BOARD_X + BOARD_W // 2
            cy = BOARD_Y + BOARD_H // 2
            self.float_texts.append(FloatTextAnimation(f"+{score}", (cx, cy)))

    def update_animations(self, dt: float) -> None:
        self.line_animations = [a for a in self.line_animations if a.update(dt)]
        self.float_texts = [t for t in self.float_texts if t.update(dt)]
        if self._mode_transition < 0.2:
            self._mode_transition = min(0.2, self._mode_transition + dt)
        self._breath_phase = (self._breath_phase + dt * 2.0) % (2.0 * 3.14159)

    def _get_breath_scale(self) -> float:
        import math
        return 1.0 + math.sin(self._breath_phase) * 0.03

    def draw(self, state: State) -> None:
        if self._bg_cache:
            self.surface.blit(self._bg_cache, (0, 0))
        self._draw_top_bar()
        self._draw_hud_left(state)
        self._draw_board(state)
        self._draw_sidebar(state)
        self._draw_line_animations()
        self._draw_float_texts()
        self._draw_overlay_texts(state)

    def _draw_background_gradient(self) -> None:
        for y in range(0, BASE_H, 4):
            ratio = y / BASE_H
            r = int(COLOR_BG[0] * (1 - ratio) + COLOR_BG_GRADIENT[0] * ratio)
            g = int(COLOR_BG[1] * (1 - ratio) + COLOR_BG_GRADIENT[1] * ratio)
            b = int(COLOR_BG[2] * (1 - ratio) + COLOR_BG_GRADIENT[2] * ratio)
            pygame.draw.line(self.surface, (r, g, b), (0, y), (BASE_W, y))
        for c in range(0, COLS + 1):
            x = BOARD_X + c * CELL
            pygame.draw.line(self.surface, COLOR_GRID_FAINT, (x, BOARD_Y), (x, BOARD_Y + BOARD_H), 2)
        for r in range(0, ROWS + 1):
            y = BOARD_Y + r * CELL
            pygame.draw.line(self.surface, COLOR_GRID_FAINT, (BOARD_X, y), (BOARD_X + BOARD_W, y), 2)

    def _draw_glow_text(self, text: str, pos: tuple[int, int], color: tuple, glow_color: tuple,
                        font: pygame.font.Font | None = None) -> None:
        f = font or self.font
        main_surf = f.render(text, True, color)
        self.surface.blit(main_surf, (int(pos[0]), int(pos[1])))

    def _draw_glass_panel(self, rect: pygame.Rect, radius: int = 12) -> None:
        shadow = rect.copy()
        shadow.x += 5
        shadow.y += 7
        shadow_surf = pygame.Surface((shadow.w, shadow.h), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, COLOR_SHADOW, shadow_surf.get_rect(), border_radius=radius)
        self.surface.blit(shadow_surf, shadow.topleft)
        panel_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, COLOR_PANEL, panel_surf.get_rect(), border_radius=radius)
        pygame.draw.rect(panel_surf, COLOR_PANEL_BORDER, panel_surf.get_rect(), 2, border_radius=radius)
        inner = panel_surf.get_rect().inflate(-4, -4)
        pygame.draw.rect(panel_surf, COLOR_PANEL_INNER_GLOW, inner, 1, border_radius=radius - 2)
        self.surface.blit(panel_surf, rect.topleft)

    def _draw_top_bar(self) -> None:
        fps = int(self.clock.get_fps()) if self.clock else 0
        fps_surf = self._fps_font.render(f"FPS {fps}", True, (140, 180, 140))
        self.surface.blit(fps_surf, (int(MARGIN), int(MARGIN + 2)))

        mode_alpha = 255
        if self._mode_transition < 0.2 and self._prev_mode is not None:
            mode_alpha = int(255 * (self._mode_transition / 0.2))
        mode_text = f"MODE: {self.mode_label}"
        self._draw_glow_text(mode_text, (int(MARGIN), int(MARGIN + 20)), COLOR_ACCENT, COLOR_ACCENT_GLOW, self.mode_font)

        if self.is_replay:
            prog = self.replay_progress
            info = self.font.render(
                f"SPEED {self.replay_speed}x   {prog[0]}/{prog[1]}", True, COLOR_ACCENT2)
            self.surface.blit(info, (int(BASE_W - info.get_width() - MARGIN), int(MARGIN + 28)))

    def _draw_hud_left(self, state: State) -> None:
        panel = pygame.Rect(HUD_LEFT_X, HUD_LEFT_Y, HUD_LEFT_W, HUD_LEFT_H)
        self._draw_glass_panel(panel, radius=12)

        score = int(getattr(state, 'score', 0) or 0)
        level = int(getattr(state, 'level', 0) or 0)
        lines = int(getattr(state, 'total_lines', 0) or 0)

        y = HUD_LEFT_Y + 14
        for label, val in [("SCORE", score), ("LEVEL", level), ("LINES", lines)]:
            _draw_sharp_text(self.surface, label, (HUD_LEFT_X + 14, y), COLOR_TEXT_DIM, self._label_font)
            val_surf = self._get_value_surface(label, val)
            self.surface.blit(val_surf, (int(HUD_LEFT_X + 14), int(y + 20)))
            y += 112

        human_mode = self.mode_label == "HUMAN"
        interactive = human_mode
        legend_alpha = 255 if interactive else 90

        header = self._label_surfaces.get("CONTROLS")
        if header:
            header.set_alpha(legend_alpha)
            self.surface.blit(header, (int(HUD_LEFT_X + 14), int(HUD_LEFT_H - 140)))

        controls = self._get_controls_surfaces(legend_alpha)
        yy = HUD_LEFT_H - 120
        for surf in controls:
            self.surface.blit(surf, (int(HUD_LEFT_X + 14), int(yy)))
            yy += 19

        if not interactive and not self.is_replay:
            note = self.font.render("(KEYS DISABLED)", True, (80, 80, 95))
            note.set_alpha(130)
            self.surface.blit(note, (int(HUD_LEFT_X + 14), int(HUD_LEFT_H - 18)))

    def _draw_board(self, state: State) -> None:
        board_bg = pygame.Rect(BOARD_X, BOARD_Y, BOARD_W, BOARD_H)
        pygame.draw.rect(self.surface, COLOR_BOARD_BG, board_bg)

        for c in range(COLS + 1):
            x = BOARD_X + c * CELL
            pygame.draw.line(self.surface, COLOR_GRID_FAINT, (x, BOARD_Y), (x, BOARD_Y + BOARD_H), 1)
        for r in range(ROWS + 1):
            y = BOARD_Y + r * CELL
            pygame.draw.line(self.surface, COLOR_GRID_FAINT, (BOARD_X, y), (BOARD_X + BOARD_W, y), 1)

        for r in range(ROWS):
            for c in range(COLS):
                rect = pygame.Rect(BOARD_X + c * CELL + 1, BOARD_Y + r * CELL + 1, CELL - 2, CELL - 2)
                cell_val = state.board[r][c] if r < len(state.board) and c < len(state.board[r]) else 0
                if cell_val:
                    self._draw_3d_block(rect, PIECE_COLORS.get(cell_val, (200, 200, 200)))

        current_kind = int(getattr(state, "current_kind", 0) or 0)
        current_color = PIECE_COLORS.get(current_kind, (220, 220, 220))
        for x, y in getattr(state, "current_cells", []):
            if 0 <= x < COLS and 0 <= y < ROWS:
                rect = pygame.Rect(
                    BOARD_X + x * CELL + 1,
                    BOARD_Y + y * CELL + 1,
                    CELL - 2,
                    CELL - 2,
                )
                self._draw_3d_block(rect, current_color)

        border_surf = pygame.Surface((BOARD_W + 6, BOARD_H + 6), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, COLOR_BOARD_BORDER_GLOW, border_surf.get_rect(), 4, border_radius=4)
        self.surface.blit(border_surf, (BOARD_X - 3, BOARD_Y - 3))
        pygame.draw.rect(self.surface, COLOR_BOARD_BORDER, board_bg, 2)

    def _draw_3d_block(self, rect: pygame.Rect, base_color: tuple[int, int, int]) -> None:
        inset = 2
        fill = rect.inflate(-inset * 2, -inset * 2)
        pygame.draw.rect(self.surface, base_color, fill, border_radius=3)
        hl_top = pygame.Rect(fill.x + 2, fill.y + 2, fill.w - 4, max(2, fill.h // 4))
        hl_surf = pygame.Surface((hl_top.w, hl_top.h), pygame.SRCALPHA)
        hl_color = (min(255, base_color[0] + 80), min(255, base_color[1] + 80), min(255, base_color[2] + 80), 140)
        hl_surf.fill(hl_color)
        self.surface.blit(hl_surf, hl_top.topleft)
        sh_bottom = pygame.Rect(fill.x + 2, fill.bottom - max(2, fill.h // 4) - 2, fill.w - 4, max(2, fill.h // 4))
        sh_surf = pygame.Surface((sh_bottom.w, sh_bottom.h), pygame.SRCALPHA)
        sh_color = (max(0, base_color[0] - 60), max(0, base_color[1] - 60), max(0, base_color[2] - 60), 120)
        sh_surf.fill(sh_color)
        self.surface.blit(sh_surf, sh_bottom.topleft)
        sh_bottom_edge = pygame.Rect(fill.x + 2, fill.bottom - 4, fill.w - 4, 3)
        sh_edge_surf = pygame.Surface((sh_bottom_edge.w, sh_bottom_edge.h), pygame.SRCALPHA)
        sh_edge_surf.fill((0, 0, 0, 80))
        self.surface.blit(sh_edge_surf, sh_bottom_edge.topleft)
        pygame.draw.rect(self.surface, (255, 255, 255, 60), fill, 1, border_radius=3)

    def _draw_sidebar(self, state: State) -> None:
        panel = pygame.Rect(SIDEBAR_X, SIDEBAR_Y, SIDEBAR_W, SIDEBAR_H)
        self._draw_glass_panel(panel, radius=12)

        hold_label = self._sidebar_labels.get("HOLD")
        if hold_label:
            self.surface.blit(hold_label, (int(SIDEBAR_X + 14), int(SIDEBAR_Y + 12)))
        hold_rect = pygame.Rect(SIDEBAR_X + 14, SIDEBAR_Y + 38, 84, 74)
        pygame.draw.rect(self.surface, COLOR_BOARD_BG, hold_rect, border_radius=10)
        pygame.draw.rect(self.surface, COLOR_PANEL_BORDER, hold_rect, 1, border_radius=10)
        hold_val = getattr(state, 'hold_piece', None)
        if hold_val is not None and hold_val != 0:
            scale = self._get_breath_scale()
            center_x = hold_rect.centerx
            center_y = hold_rect.centery
            scaled_w = int(hold_rect.w * scale)
            scaled_h = int(hold_rect.h * scale)
            scaled_rect = pygame.Rect(center_x - scaled_w // 2, center_y - scaled_h // 2, scaled_w, scaled_h)
            self._draw_3d_block(scaled_rect, PIECE_COLORS.get(hold_val, (200, 200, 200)))
        elif hold_val is None or hold_val == 0:
            hint = self._sidebar_labels.get("empty")
            if hint:
                hint.set_alpha(120)
                self.surface.blit(hint, hint.get_rect(center=(int(hold_rect.centerx), int(hold_rect.centery))))

        next_label = self._sidebar_labels.get("NEXT")
        if next_label:
            self.surface.blit(next_label, (int(SIDEBAR_X + 14), int(SIDEBAR_Y + 132)))
        queue = getattr(state, 'next_queue', []) or []
        for i in range(5):
            slot_rect = pygame.Rect(SIDEBAR_X + 14, SIDEBAR_Y + 158 + i * 38, 64, 32)
            pygame.draw.rect(self.surface, (20, 22, 32), slot_rect, border_radius=6)
            pygame.draw.rect(self.surface, (60, 68, 85), slot_rect, 1, border_radius=6)
            piece = queue[i] if i < len(queue) else 0
            if piece:
                scale = self._get_breath_scale()
                center_x = slot_rect.centerx
                center_y = slot_rect.centery
                scaled_w = int(slot_rect.w * scale)
                scaled_h = int(slot_rect.h * scale)
                scaled_rect = pygame.Rect(center_x - scaled_w // 2, center_y - scaled_h // 2, scaled_w, scaled_h)
                self._draw_3d_block(scaled_rect, PIECE_COLORS.get(piece, (200, 200, 200)))
            else:
                inner_slot = slot_rect.inflate(-6, -6)
                dash_len = 4
                gap_len = 4
                for dx in range(inner_slot.x, inner_slot.x + inner_slot.w, dash_len + gap_len):
                    pygame.draw.line(self.surface, (50, 55, 70, 80), (int(dx), int(inner_slot.centery)), (int(dx + dash_len), int(inner_slot.centery)), 1)

    def _draw_line_animations(self) -> None:
        for anim in self.line_animations:
            t = anim.progress
            for row in anim.rows:
                base_rect = pygame.Rect(BOARD_X + 1, BOARD_Y + row * CELL + 1, BOARD_W - 2, CELL - 2)
                if anim.phase == 0:
                    if anim.flash_visible:
                        flash = pygame.Surface((base_rect.w, base_rect.h), pygame.SRCALPHA)
                        flash.fill((255, 255, 255, 210))
                        self.surface.blit(flash, base_rect.topleft)
                elif anim.phase == 1:
                    fade_t = (t - 0.12) / 0.10 if t > 0.12 else 0
                    shrink = int(BOARD_W * fade_t)
                    new_w = max(1, BOARD_W - 2 - shrink)
                    new_x = BOARD_X + 1 + shrink // 2
                    rect = pygame.Rect(new_x, BOARD_Y + row * CELL + 1, new_w, CELL - 2)
                    flash = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                    flash.fill((255, 255, 255, 180))
                    self.surface.blit(flash, rect.topleft)
                else:
                    fade_t = (t - 0.22) / 0.08 if t > 0.22 else 0
                    shrink = int(BOARD_W)
                    new_w = max(1, BOARD_W - 2 - shrink)
                    new_x = BOARD_X + 1 + shrink // 2
                    rect = pygame.Rect(new_x, BOARD_Y + row * CELL + 1, new_w, CELL - 2)
                    alpha = int(180 * (1 - fade_t))
                    flash = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                    flash.fill((255, 255, 255, alpha))
                    self.surface.blit(flash, rect.topleft)

    def _draw_float_texts(self) -> None:
        for ft in self.float_texts:
            alpha = ft.alpha
            surf = self.big_font.render(ft.text, True, COLOR_ACCENT2)
            surf.set_alpha(alpha)
            rect = surf.get_rect(center=(int(ft.center_x), int(ft.current_y)))
            self.surface.blit(surf, (int(rect.x), int(rect.y)))

    def _draw_overlay_texts(self, state: State | None = None) -> None:
        center = pygame.Rect(0, 0, BASE_W, BASE_H).center
        _sys = ['Microsoft YaHei', 'Segoe UI', 'Arial']
        big_font = _sf(_sys, 72, bold=True)

        if self.is_paused:
            self._draw_glow_text("PAUSED", (int(center[0] - 140), int(center[1] - 40)), COLOR_ACCENT, COLOR_ACCENT_GLOW, big_font)
            sub = self.font.render("Press P to resume", True, COLOR_TEXT_DIM)
            self.surface.blit(sub, (int(center[0] - sub.get_width() // 2), int(center[1] + 30)))

        if self.replay_finished and self.is_replay:
            self._draw_glow_text("REPLAY FINISHED", (int(center[0] - 180), int(center[1] + 60)), COLOR_ACCENT2, (255, 230, 60, 80), _sf(_sys, 54, bold=True))
            sub = self.font.render("Press R to restart", True, COLOR_TEXT_DIM)
            self.surface.blit(sub, (int(center[0] - sub.get_width() // 2), int(center[1] + 120)))

        if state is not None and bool(getattr(state, "game_over", False)):
            self._draw_glow_text(
                "GAME OVER",
                (int(center[0] - 190), int(center[1] - 45)),
                (255, 80, 95),
                (255, 80, 95, 70),
                big_font,
            )
            sub = self.font.render("Press R to restart", True, COLOR_TEXT_DIM)
            self.surface.blit(
                sub,
                (int(center[0] - sub.get_width() // 2), int(center[1] + 45)),
            )
