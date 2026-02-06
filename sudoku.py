import pygame
import sys
import random
import time
import json
import os

# --- НАСТРОЙКИ ---
WIDTH, HEIGHT = 540, 950
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Sudoku: Infinite Edition")

pygame.init()

# --- ШРИФТЫ ---
FONT_XL = pygame.font.SysFont("Arial", 60, bold=True)
FONT_L = pygame.font.SysFont("Arial", 45, bold=True)
FONT_M = pygame.font.SysFont("Arial", 24, bold=True)
FONT = pygame.font.SysFont("Arial", 35)
SMALL_FONT = pygame.font.SysFont("Arial", 20)
CANDIDATE_FONT = pygame.font.SysFont("Arial", 12, bold=True) 
BTN_FONT = pygame.font.SysFont("Arial", 20, bold=True)
ICON_FONT = pygame.font.SysFont("Segoe UI Symbol", 28) 

# --- ЦВЕТОВЫЕ ТЕМЫ ---
THEMES = {
    "light": {
        "bg": (248, 243, 235),
        "grid_line": (160, 140, 130),
        "cell_bg": (255, 255, 255),
        "text_main": (60, 55, 50),
        "text_blue": (70, 130, 180),
        "text_candidate": (120, 120, 120),
        "highlight": (235, 225, 215),
        "selected": (200, 220, 230),
        "btn_bg": (220, 210, 200),
        "btn_hover": (200, 190, 180),
        "btn_checked": (100, 180, 100),
        "btn_active_tool": (255, 215, 0),
        "correct": (210, 245, 210),
        "wrong": (245, 210, 210),
        "heart_red": (220, 60, 60),
        "heart_black": (60, 60, 60),
        "bar_bg": (220, 220, 220),
        "box_outer": (230, 225, 220),
        "box_inner": (255, 255, 255),
        "box_inner_done": (200, 235, 200),
        "box_selected": (70, 130, 180),
        "lvl_col_bg": (245, 242, 240),
        "lvl_col_border": (180, 170, 160),
        "placeholder_img": (200, 200, 200),
        "placeholder_diff": (170, 170, 170)
    },
    "dark": {
        "bg": (35, 35, 40),
        "grid_line": (80, 80, 90),
        "cell_bg": (45, 45, 50),
        "text_main": (220, 220, 225),
        "text_blue": (100, 180, 255),
        "text_candidate": (150, 150, 160),
        "highlight": (60, 60, 70),
        "selected": (70, 80, 100),
        "btn_bg": (60, 60, 70),
        "btn_hover": (80, 80, 95),
        "btn_checked": (60, 120, 60),
        "btn_active_tool": (180, 160, 50),
        "correct": (40, 80, 40),
        "wrong": (80, 40, 40),
        "heart_red": (255, 80, 80),
        "heart_black": (100, 100, 100),
        "bar_bg": (60, 60, 65),
        "box_outer": (60, 60, 70),
        "box_inner": (80, 80, 90),
        "box_inner_done": (50, 90, 50),
        "box_selected": (100, 180, 255),
        "lvl_col_bg": (50, 50, 55),
        "lvl_col_border": (80, 80, 90),
        "placeholder_img": (80, 80, 80),
        "placeholder_diff": (100, 100, 100)
    }
}

current_theme_name = "light"
game_state = "SPLASH"

# --- ИГРОВЫЕ ПАРАМЕТРЫ ---
current_mode_type = "9x9"
grid_size = 9
box_w, box_h = 3, 3
max_digit = 9
difficulty_fill_percent = 0.45

lives = 3
score = 0
start_ticks = 0
elapsed_time = 0
cell_selection_time = 0
is_game_active = False
is_check_mode = False 
is_notes_mode = False 
is_super_hint_mode = False
is_fast_mode = False

error_history_cells = set()
hint_used_cells = set()

splash_start_time = 0
# Переменная для хранения загруженного интро-изображения
splash_image = None

# КЭШ КАРТИНОК РАНГОВ
loaded_rank_images = {}

def get_color(key): return THEMES[current_theme_name][key]

# --- СОХРАНЕНИЕ ---
DATA_FILE = "sudoku_data.json"
def load_data():
    if not os.path.exists(DATA_FILE): return {"best_time": None, "games_played": 0}
    try: 
        with open(DATA_FILE, "r") as f: return json.load(f)
    except: return {"best_time": None, "games_played": 0}

def save_game_result(time_ms):
    data = load_data()
    data["games_played"] += 1
    if data["best_time"] is None or time_ms < data["best_time"]:
        data["best_time"] = time_ms
    with open(DATA_FILE, "w") as f: json.dump(data, f)

# --- UI CLASS ---
class Button:
    def __init__(self, text, x, y, w, h, func=None, color_key="btn_bg", icon=False, font=None):
        self.text = text
        self.rect = pygame.Rect(x, y, w, h)
        self.func = func
        self.hovered = False
        self.pressed = False
        self.color_key = color_key
        self.icon = icon 
        self.custom_font = font
        self.active_override_color = None 

    def draw(self, screen):
        base_c = self.active_override_color if self.active_override_color else (get_color("btn_hover") if self.hovered else get_color(self.color_key))
        draw_rect = self.rect.inflate(-2, -2) if self.pressed else self.rect
        pygame.draw.rect(screen, base_c, draw_rect, border_radius=10)
        pygame.draw.rect(screen, get_color("grid_line"), draw_rect, 2, border_radius=10)
        f = self.custom_font if self.custom_font else (ICON_FONT if self.icon else BTN_FONT)
        txt_surf = f.render(self.text, True, get_color("text_main"))
        screen.blit(txt_surf, txt_surf.get_rect(center=draw_rect.center))

    def check_hover(self, pos): self.hovered = self.rect.collidepoint(pos)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered: self.pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.pressed and self.hovered and self.func: self.func()
            self.pressed = False

# --- LOGIC ---
def is_valid_logic(board, row, col, num, size, bw, bh):
    for x in range(size):
        if board[row][x] == num: return False
    for x in range(size):
        if board[x][col] == num: return False
    sr, sc = row - row % bh, col - col % bw
    for i in range(bh):
        for j in range(bw):
            if board[i + sr][j + sc] == num: return False
    return True

def get_candidates(board, r, c):
    return [num for num in range(1, max_digit + 1) if is_valid_logic(board, r, c, num, grid_size, box_w, box_h)]

def solve_algo(board):
    for i in range(grid_size):
        for j in range(grid_size):
            if board[i][j] == 0:
                nums = list(range(1, max_digit + 1)); random.shuffle(nums)
                for num in nums:
                    if is_valid_logic(board, i, j, num, grid_size, box_w, box_h):
                        board[i][j] = num
                        if solve_algo(board): return True
                        board[i][j] = 0
                return False
    return True

def generate_puzzle():
    board = [[0]*grid_size for _ in range(grid_size)]
    solve_algo(board)
    full_solution = [row[:] for row in board]
    total = grid_size * grid_size
    keep = int(total * difficulty_fill_percent)
    remove = total - keep
    attempts = remove
    while attempts > 0:
        r, c = random.randint(0, grid_size - 1), random.randint(0, grid_size - 1)
        if board[r][c] != 0: board[r][c] = 0
        attempts -= 1
    return board, full_solution

# --- GAME CONTROLLER ---
initial_grid, solved_grid, grid, validation_grid = None, None, None, None
selected_cell, selected_digit = None, None
message = ""

def set_mode_parameters(mode_name, diff_percent):
    global current_mode_type, grid_size, box_w, box_h, max_digit, difficulty_fill_percent
    current_mode_type = mode_name
    difficulty_fill_percent = diff_percent
    if mode_name == "6x6": grid_size = 6; box_w = 3; box_h = 2; max_digit = 6
    elif mode_name == "9x9": grid_size = 9; box_w = 3; box_h = 3; max_digit = 9
    elif mode_name == "16x16": grid_size = 16; box_w = 4; box_h = 4; max_digit = 16

def start_game_with_params(mode, diff_val):
    set_mode_parameters(mode, diff_val)
    start_new_game()

def start_new_game():
    global initial_grid, solved_grid, grid, validation_grid, selected_cell, selected_digit 
    global message, game_state, lives, score, start_ticks, elapsed_time, is_game_active, is_check_mode
    global is_notes_mode, is_super_hint_mode, is_fast_mode, error_history_cells, hint_used_cells
    
    initial_grid, solved_grid = generate_puzzle()
    grid = [row[:] for row in initial_grid]
    validation_grid = [[None]*grid_size for _ in range(grid_size)]
    selected_cell = None; selected_digit = 1
    message = ""; lives = 3; score = 0
    
    elapsed_time = 0
    start_ticks = pygame.time.get_ticks()
    
    is_game_active = True; is_check_mode = False; is_notes_mode = False; is_super_hint_mode = False; is_fast_mode = False
    error_history_cells = set(); hint_used_cells = set()
    game_state = "GAME"

def pause_game():
    global game_state, elapsed_time
    if game_state == "GAME":
        elapsed_time += pygame.time.get_ticks() - start_ticks
        game_state = "PAUSE"

def resume_game():
    global game_state, start_ticks
    if game_state == "PAUSE":
        start_ticks = pygame.time.get_ticks()
        game_state = "GAME"

def get_current_game_time():
    if game_state == "PAUSE":
        return elapsed_time
    elif is_game_active:
        return elapsed_time + (pygame.time.get_ticks() - start_ticks)
    return elapsed_time

def attempt_place_number(r, c, val):
    global grid, score, message, lives, is_game_active, game_state, validation_grid
    if not is_game_active or initial_grid[r][c] != 0: return
    grid[r][c] = val
    validation_grid[r][c] = None 
    if val == solved_grid[r][c]:
        points = 100
        if (r, c) in hint_used_cells: points = 0
        else:
            if time.time() - cell_selection_time < 5.0: points = int(points * 1.5)
            if (r, c) in error_history_cells: points = int(points * 0.5)
        score += points
        check_victory_condition()
    else: error_history_cells.add((r, c))

def check_victory_condition():
    global is_game_active, game_state, message, score
    correct = sum(1 for r in range(grid_size) for c in range(grid_size) if grid[r][c] == solved_grid[r][c])
    if correct == grid_size * grid_size:
        is_game_active = False
        final_time = get_current_game_time()
        mins = final_time // 60000
        mult = 0.5 if mins < 2 else (0.3 if mins < 5 else (0.1 if mins < 10 else 0.0))
        score += int(score * mult)
        message = f"Victory! +{int(score*mult)} Time Bonus"
        game_state = "VICTORY_SCREEN"
        save_game_result(final_time)

def toggle_check():
    global is_check_mode, lives, message, is_game_active, game_state
    if is_check_mode:
        is_check_mode = False
        for r in range(grid_size):
            for c in range(grid_size): validation_grid[r][c] = None
    else:
        errs = 0
        for r in range(grid_size):
            for c in range(grid_size):
                if grid[r][c] != 0:
                    if grid[r][c] != solved_grid[r][c]:
                        validation_grid[r][c] = "wrong"; errs += 1
                    else: validation_grid[r][c] = "correct"
        if errs > 0:
            lives -= errs
            message = f"Check: {errs} errors!"
            if lives <= 0: lives = 0; is_game_active = False; game_state = "GAME_OVER"; message = "GAME OVER"
        else: message = "Looks good!"
        is_check_mode = True

def toggle_notes(): global is_notes_mode; is_notes_mode = not is_notes_mode
def toggle_super_hint(): global is_super_hint_mode; is_super_hint_mode = not is_super_hint_mode
def toggle_fast_mode(): global is_fast_mode; is_fast_mode = not is_fast_mode
def use_random_hint():
    global grid
    if not is_game_active: return
    e = [(r, c) for r in range(grid_size) for c in range(grid_size) if grid[r][c] == 0]
    if e:
        r, c = random.choice(e)
        grid[r][c] = solved_grid[r][c]; hint_used_cells.add((r,c)); check_victory_condition()

# --- NAVIGATION ---
def go_to_main_menu(): global game_state; game_state = "MAIN_MENU" 
def go_to_mode_select(): global game_state; game_state = "MODE_SELECT"
def go_to_settings(): global game_state; game_state = "SETTINGS"
def quit_game(): pygame.quit(); sys.exit()
def toggle_theme(): global current_theme_name; current_theme_name = "dark" if current_theme_name == "light" else "light"

# --- RENDERERS ---

def format_cell_value(val):
    if val <= 9: return str(val)
    return chr(65 + val - 10)

# --- НОВАЯ ФУНКЦИЯ ЗАСТАВКИ (ИНТРО) ---
def draw_splash_screen():
    global splash_start_time, game_state, splash_image
    
    # 1. Инициализация таймера
    if splash_start_time == 0: splash_start_time = pygame.time.get_ticks()
    current_ms = pygame.time.get_ticks() - splash_start_time

    # 2. Загрузка изображения (один раз)
    if splash_image is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "assets", "images", "intro", "GDA.jpeg")
        if os.path.exists(path):
            try:
                loaded = pygame.image.load(path).convert()
                # Масштабируем до 80% ширины экрана, сохраняя пропорции
                target_width = WIDTH * 0.8
                scale_factor = target_width / loaded.get_width()
                target_height = loaded.get_height() * scale_factor
                splash_image = pygame.transform.smoothscale(loaded, (int(target_width), int(target_height)))
            except:
                splash_image = "ERROR" # Флаг ошибки, если не загрузилось
        else:
             splash_image = "ERROR"

    # 3. Логика тайминга и прозрачности (через черную накладку)
    # Тайминги: 1с появление, 1.5с удержание, 1с затухание
    FADE_IN_DUR = 1000
    HOLD_DUR = 1500
    FADE_OUT_START = FADE_IN_DUR + HOLD_DUR
    TOTAL_TIME = FADE_OUT_START + 1000 

    overlay_alpha = 0

    if current_ms < FADE_IN_DUR:
        # Появление: Черный слой становится прозрачным (255 -> 0)
        overlay_alpha = 255 - int((current_ms / FADE_IN_DUR) * 255)
    elif current_ms < FADE_OUT_START:
        # Удержание: Черный слой полностью прозрачен
        overlay_alpha = 0
    elif current_ms < TOTAL_TIME:
        # Затухание: Черный слой становится непрозрачным (0 -> 255)
        overlay_alpha = int(((current_ms - FADE_OUT_START) / (TOTAL_TIME - FADE_OUT_START)) * 255)
    else:
        # Время вышло, переход в меню
        game_state = "MAIN_MENU"
        return

    # 4. Отрисовка
    SCREEN.fill((0, 0, 0)) # Черный фон

    # Рисуем логотип по центру
    if splash_image and splash_image != "ERROR":
        img_rect = splash_image.get_rect(center=(WIDTH//2, HEIGHT//2))
        SCREEN.blit(splash_image, img_rect)
    else:
        # Запасной вариант (текст), если картинка не нашлась
        t = FONT_M.render("GDA STUDIO", True, (255,255,255))
        SCREEN.blit(t, t.get_rect(center=(WIDTH//2, HEIGHT//2)))

    # Рисуем черную накладку для эффекта фейда
    if overlay_alpha > 0:
        fade_surface = pygame.Surface((WIDTH, HEIGHT))
        fade_surface.fill((0,0,0))
        fade_surface.set_alpha(overlay_alpha)
        SCREEN.blit(fade_surface, (0,0))

def draw_main_menu():
    SCREEN.fill(get_color("bg"))
    t1 = FONT_XL.render("SUDOKU", True, get_color("text_main"))
    t2 = FONT.render("Infinite Edition", True, get_color("text_blue"))
    SCREEN.blit(t1, (WIDTH//2 - t1.get_width()//2, 160))
    SCREEN.blit(t2, (WIDTH//2 - t2.get_width()//2, 220))
    
    d = load_data()
    best = d["best_time"]
    bt_str = f"Best: {(best//1000)//60:02}:{(best//1000)%60:02}" if best else "Best: --:--"
    bs = BTN_FONT.render(bt_str, True, get_color("text_main"))
    SCREEN.blit(bs, (WIDTH//2 - bs.get_width()//2, 280))
    
    mp = pygame.mouse.get_pos()
    for b in [btn_start, btn_settings, btn_exit]:
        b.check_hover(mp); b.draw(SCREEN)

def draw_mode_select():
    SCREEN.fill(get_color("bg"))
    overlay = pygame.Surface((WIDTH, HEIGHT)); overlay.set_alpha(100); overlay.fill((0, 0, 0))
    SCREEN.blit(overlay, (0, 0))
    
    title = FONT_L.render("SELECT MODE", True, (255, 255, 255))
    SCREEN.blit(title, (WIDTH//2 - title.get_width()//2, 50))
    
    col_w = 160
    gap = 15
    start_x = (WIDTH - (col_w * 3 + gap * 2)) // 2
    col_h = 450
    start_y = (HEIGHT - col_h) // 2
    
    modes_config = [
        ("6x6", "Mini", [("Easy", 0.65), ("Norm", 0.55), ("Adv", 0.48), ("Hard", 0.40), ("Exp", 0.33)]),
        ("9x9", "Classic", [("Easy", 0.52), ("Norm", 0.42), ("Adv", 0.35), ("Hard", 0.28), ("Exp", 0.22)]),
        ("16x16", "Monster", [("Easy", 0.60), ("Norm", 0.50), ("Adv", 0.40), ("Hard", 0.32), ("Exp", 0.25)])
    ]
    
    mouse_pos = pygame.mouse.get_pos()
    
    for i, (m_id, m_name, diffs) in enumerate(modes_config):
        cx = start_x + i * (col_w + gap)
        cy = start_y
        col_rect = pygame.Rect(cx, cy, col_w, col_h)
        pygame.draw.rect(SCREEN, get_color("lvl_col_bg"), col_rect, border_radius=15)
        pygame.draw.rect(SCREEN, get_color("lvl_col_border"), col_rect, 2, border_radius=15)
        
        img_h = 80
        img_rect = pygame.Rect(cx + 20, cy + 20, col_w - 40, img_h)
        pygame.draw.rect(SCREEN, get_color("placeholder_img"), img_rect, border_radius=10)
        t_img = BTN_FONT.render(f"IMG {m_id}", True, (255,255,255))
        SCREEN.blit(t_img, t_img.get_rect(center=img_rect.center))
        
        name_s = FONT_M.render(m_name, True, get_color("text_main"))
        SCREEN.blit(name_s, (cx + col_w//2 - name_s.get_width()//2, cy + 110))
        
        btn_start_y = cy + 150
        btn_h = 45 
        btn_gap_y = 10
        
        rank_prefix = "bronze"
        if m_id == "9x9": rank_prefix = "silver"
        elif m_id == "16x16": rank_prefix = "gold"
        
        for d_idx, (d_name, d_val) in enumerate(diffs):
            by = btn_start_y + d_idx * (btn_h + btn_gap_y)
            btn_rect = pygame.Rect(cx + 10, by, col_w - 20, btn_h)
            is_hover = btn_rect.collidepoint(mouse_pos)
            if is_hover and pygame.mouse.get_pressed()[0]:
                start_game_with_params(m_id, d_val)
                return
            
            img_name = f"{rank_prefix}{d_idx + 1}.png"
            if img_name not in loaded_rank_images:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                path = os.path.join(base_dir, "assets", "images", "ranks", img_name)
                if os.path.exists(path):
                    try:
                        loaded = pygame.image.load(path).convert_alpha()
                        scaled = pygame.transform.smoothscale(loaded, (120, 35))
                        loaded_rank_images[img_name] = scaled
                    except:
                        loaded_rank_images[img_name] = None
                else:
                    loaded_rank_images[img_name] = None
            
            rank_surf = loaded_rank_images.get(img_name)
            
            if rank_surf:
                ix = btn_rect.centerx - rank_surf.get_width() // 2
                iy = btn_rect.centery - rank_surf.get_height() // 2
                SCREEN.blit(rank_surf, (ix, iy))
                if is_hover:
                    hover_rect = pygame.Rect(ix - 2, iy - 2, rank_surf.get_width() + 4, rank_surf.get_height() + 4)
                    pygame.draw.rect(SCREEN, (255, 215, 0), hover_rect, 2, border_radius=4)
            else:
                bg_c = get_color("btn_hover") if is_hover else get_color("btn_bg")
                pygame.draw.rect(SCREEN, bg_c, btn_rect, border_radius=8)
                txt_s = BTN_FONT.render(d_name, True, get_color("text_main"))
                SCREEN.blit(txt_s, txt_s.get_rect(center=btn_rect.center))
            
    btn_back_mode.rect.topleft = (WIDTH//2 - 60, start_y + col_h + 20)
    btn_back_mode.check_hover(mouse_pos)
    btn_back_mode.draw(SCREEN)

def draw_game_screen():
    SCREEN.fill(get_color("bg"))
    filled = sum(1 for r in range(grid_size) for c in range(grid_size) if grid[r][c] != 0)
    prog = filled / (grid_size * grid_size)
    pygame.draw.rect(SCREEN, get_color("bar_bg"), (20, 15, WIDTH-40, 12), border_radius=6)
    if prog > 0:
        sc, ec = (230, 80, 80), (80, 230, 80)
        c = (int(sc[0]+(ec[0]-sc[0])*prog), int(sc[1]+(ec[1]-sc[1])*prog), int(sc[2]+(ec[2]-sc[2])*prog))
        pygame.draw.rect(SCREEN, c, (20, 15, (WIDTH-40)*prog, 12), border_radius=6)
    
    ct = get_current_game_time()
    sec, mn = (ct//1000)%60, (ct//1000)//60
    t_str = f"{mn:02}:{sec:02}"
    col = get_color("text_main")
    SCREEN.blit(BTN_FONT.render(f"Time: {t_str}", True, col), (20, 40))
    SCREEN.blit(BTN_FONT.render(f"Score: {score}", True, col), (200, 40))

    avail_w = WIDTH - 20
    cell_s = avail_w // grid_size
    grid_y = 100
    grid_h = cell_s * grid_size
    
    lx = WIDTH - 20 - (3*30)
    ly = 40
    for i in range(3):
        c = get_color("heart_red") if i < lives else get_color("heart_black")
        SCREEN.blit(ICON_FONT.render("❤", True, c), (lx + i*30, ly - 10))
    
    for r in range(grid_size):
        for c in range(grid_size):
            rect = pygame.Rect(10 + c*cell_s, grid_y + r*cell_s, cell_s, cell_s)
            pygame.draw.rect(SCREEN, get_color("cell_bg"), rect)
            if is_check_mode:
                if validation_grid[r][c] == "correct": pygame.draw.rect(SCREEN, get_color("correct"), rect)
                elif validation_grid[r][c] == "wrong": pygame.draw.rect(SCREEN, get_color("wrong"), rect)
            elif selected_digit and grid[r][c] == selected_digit:
                pygame.draw.rect(SCREEN, get_color("highlight"), rect)
            if selected_cell == (r, c):
                pygame.draw.rect(SCREEN, get_color("selected"), rect)
                if is_super_hint_mode: pygame.draw.rect(SCREEN, get_color("btn_active_tool"), rect, 3)
            
            if is_notes_mode and grid[r][c] == 0:
                cands = get_candidates(grid, r, c)
                if cands:
                    note_font_size = max(8, int(cell_s / 3.5)) 
                    NOTE_FONT = pygame.font.SysFont("Arial", note_font_size)
                    cols_in_cell = box_w 
                    rows_in_cell = box_h 
                    cw = rect.width / cols_in_cell
                    ch = rect.height / rows_in_cell
                    for cand in cands:
                        idx = cand - 1
                        cx_idx = idx % cols_in_cell
                        cy_idx = idx // cols_in_cell
                        cx = rect.x + cx_idx * cw + cw/2
                        cy = rect.y + cy_idx * ch + ch/2
                        txt = NOTE_FONT.render(format_cell_value(cand), True, get_color("text_candidate"))
                        SCREEN.blit(txt, txt.get_rect(center=(cx, cy)))

    for i in range(grid_size + 1):
        th = 3 if i % box_w == 0 else 1
        lc = get_color("grid_line")
        pygame.draw.line(SCREEN, lc, (10 + i*cell_s, grid_y), (10 + i*cell_s, grid_y + grid_h), th)
        th_h = 3 if i % box_h == 0 else 1
        pygame.draw.line(SCREEN, lc, (10, grid_y + i*cell_s), (10 + grid_size*cell_s, grid_y + i*cell_s), th_h)

    val_font_size = int(cell_s * 0.6)
    VAL_FONT = pygame.font.SysFont("Arial", val_font_size)
    for r in range(grid_size):
        for c in range(grid_size):
            if grid[r][c] != 0:
                c_col = get_color("text_main") if not initial_grid[r][c] else get_color("text_blue")
                txt = VAL_FONT.render(format_cell_value(grid[r][c]), True, c_col)
                SCREEN.blit(txt, txt.get_rect(center=(10 + c*cell_s + cell_s//2, grid_y + r*cell_s + cell_s//2)))

    tool_y = grid_y + grid_h + 15
    cx = WIDTH // 2
    btn_tool_notes.rect.topleft = (cx - 130, tool_y)
    btn_tool_bulb.rect.topleft = (cx - 60, tool_y)
    btn_tool_super.rect.topleft = (cx + 10, tool_y)
    btn_tool_fast.rect.topleft = (cx + 80, tool_y)
    
    btn_tool_notes.active_override_color = get_color("btn_active_tool") if is_notes_mode else None
    btn_tool_super.active_override_color = get_color("btn_active_tool") if is_super_hint_mode else None
    btn_tool_fast.active_override_color = get_color("btn_active_tool") if is_fast_mode else None
    
    mp = pygame.mouse.get_pos()
    for b in [btn_tool_notes, btn_tool_bulb, btn_tool_super, btn_tool_fast]:
        b.check_hover(mp); b.draw(SCREEN)

    draw_numpad(SCREEN, tool_y + 60)

    btn_check.active_override_color = get_color("btn_checked") if is_check_mode else None
    btn_check.check_hover(mp); btn_menu_game.check_hover(mp)
    btn_check.draw(SCREEN); btn_menu_game.draw(SCREEN)

    if message:
        m_img = SMALL_FONT.render(message, True, get_color("text_main"))
        SCREEN.blit(m_img, (WIDTH//2 - m_img.get_width()//2, HEIGHT - 110))

    if game_state == "GAME_OVER": draw_overlay("GAME OVER", "No lives left!")
    if game_state == "VICTORY_SCREEN": draw_overlay("VICTORY!", f"Score: {score}")

def draw_numpad(screen, y):
    counts = {i: grid_size for i in range(1, max_digit+1)}
    for r in grid:
        for val in r:
            if val in counts: counts[val] -= 1
    rows = 1 if grid_size <= 9 else 2
    cols = grid_size if grid_size <= 9 else 8
    bw = (WIDTH - 20) // cols
    bh = 60
    for i in range(1, max_digit + 1):
        row_idx = (i - 1) // 8 if grid_size == 16 else 0
        col_idx = (i - 1) % 8 if grid_size == 16 else (i - 1)
        cx = 10 + col_idx * bw
        cy = y + row_idx * (bh + 5)
        outer = pygame.Rect(cx + 2, cy, bw - 4, bh)
        if selected_digit == i: pygame.draw.rect(screen, get_color("box_selected"), outer.inflate(4,4), border_radius=8)
        pygame.draw.rect(screen, get_color("box_outer"), outer, border_radius=6)
        t_val = format_cell_value(i)
        t_col = get_color("text_main")
        if counts[i] == 0: t_col = get_color("grid_line")
        f = BTN_FONT if grid_size <= 9 else SMALL_FONT
        ts = f.render(t_val, True, t_col)
        screen.blit(ts, ts.get_rect(center=(outer.centerx, outer.centery - 8)))
        if counts[i] > 0:
            rs = CANDIDATE_FONT.render(str(counts[i]), True, get_color("text_blue"))
            screen.blit(rs, rs.get_rect(center=(outer.centerx, outer.bottom - 10)))

def draw_overlay(t1_s, t2_s):
    ov = pygame.Surface((WIDTH, HEIGHT)); ov.set_alpha(180); ov.fill((0,0,0))
    SCREEN.blit(ov, (0,0))
    t1 = FONT_XL.render(t1_s, True, (255, 80, 80))
    t2 = FONT.render(t2_s, True, (255, 255, 255))
    SCREEN.blit(t1, (WIDTH//2 - t1.get_width()//2, HEIGHT//2 - 80))
    SCREEN.blit(t2, (WIDTH//2 - t2.get_width()//2, HEIGHT//2 - 20))
    mp = pygame.mouse.get_pos()
    for b in [btn_restart, btn_menu_over]: b.check_hover(mp); b.draw(SCREEN)

def draw_pause_menu():
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(180)
    overlay.fill((0, 0, 0))
    SCREEN.blit(overlay, (0, 0))
    t = FONT_XL.render("PAUSED", True, (255, 255, 255))
    SCREEN.blit(t, (WIDTH//2 - t.get_width()//2, 150))
    mp = pygame.mouse.get_pos()
    for b in [btn_pause_resume, btn_pause_restart, btn_pause_main, btn_pause_exit]:
        b.check_hover(mp)
        b.draw(SCREEN)

def draw_settings():
    SCREEN.fill(get_color("bg"))
    t = FONT_L.render("SETTINGS", True, get_color("text_main"))
    SCREEN.blit(t, (WIDTH//2 - t.get_width()//2, 180))
    btn_theme.text = f"Theme: {current_theme_name.capitalize()}"
    mp = pygame.mouse.get_pos()
    for b in [btn_theme, btn_back_set]: b.check_hover(mp); b.draw(SCREEN)

# --- BUTTONS ---
btn_start = Button("Start Game", WIDTH//2 - 100, 350, 200, 60, go_to_mode_select) 
btn_settings = Button("Settings", WIDTH//2 - 100, 430, 200, 60, go_to_settings)
btn_exit = Button("Exit", WIDTH//2 - 100, 510, 200, 60, quit_game)

btn_restart = Button("Try Again", WIDTH//2 - 110, HEIGHT//2 + 60, 220, 60, start_new_game)
btn_menu_over = Button("Modes", WIDTH//2 - 110, HEIGHT//2 + 140, 220, 60, go_to_mode_select)

btn_pause_resume = Button("Resume", WIDTH//2 - 100, 300, 200, 60, resume_game)
btn_pause_restart = Button("Restart", WIDTH//2 - 100, 380, 200, 60, start_new_game)
btn_pause_main = Button("Main Menu", WIDTH//2 - 100, 460, 200, 60, go_to_main_menu)
btn_pause_exit = Button("Exit", WIDTH//2 - 100, 540, 200, 60, quit_game)

btn_theme = Button("Theme: Light", WIDTH//2 - 120, 300, 240, 60, toggle_theme)
btn_back_set = Button("Back", WIDTH//2 - 100, 460, 200, 60, go_to_main_menu)
btn_back_mode = Button("Back", 0, 0, 120, 40, go_to_main_menu) 

btn_check = Button("Check", WIDTH - 130, HEIGHT - 70, 110, 50, toggle_check)
btn_menu_game = Button("Menu", 20, HEIGHT - 70, 110, 50, pause_game) 

btn_tool_notes = Button("★", 0, 0, 60, 50, toggle_notes, icon=True)
btn_tool_bulb = Button("💡", 0, 0, 60, 50, use_random_hint, icon=True)
btn_tool_super = Button("🎯", 0, 0, 60, 50, toggle_super_hint, icon=True)
btn_tool_fast  = Button("⚡", 0, 0, 60, 50, toggle_fast_mode, icon=True)

# --- MAIN ---
def main():
    global selected_cell, selected_digit, is_game_active, elapsed_time, cell_selection_time
    global is_super_hint_mode, is_fast_mode
    clock = pygame.time.Clock()
    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT: running = False
            active_btns = []
            
            if game_state == "MAIN_MENU": active_btns = [btn_start, btn_settings, btn_exit]
            elif game_state == "MODE_SELECT": active_btns = [btn_back_mode] 
            elif game_state == "SETTINGS": active_btns = [btn_theme, btn_back_set]
            elif game_state == "GAME": active_btns = [btn_check, btn_menu_game, btn_tool_notes, btn_tool_bulb, btn_tool_super, btn_tool_fast]
            elif game_state == "PAUSE": active_btns = [btn_pause_resume, btn_pause_restart, btn_pause_main, btn_pause_exit]
            elif game_state in ["GAME_OVER", "VICTORY_SCREEN"]: active_btns = [btn_restart, btn_menu_over]
            
            for b in active_btns: b.handle_event(event)
            
            if game_state == "GAME" and is_game_active and event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                avail_w = WIDTH - 20
                cell_s = avail_w // grid_size
                grid_y = 100
                grid_h = cell_s * grid_size
                if 10 <= x < 10 + grid_size*cell_s and grid_y <= y < grid_y + grid_h:
                    c = (x - 10) // cell_s
                    r = (y - grid_y) // cell_s
                    if is_super_hint_mode:
                        grid[r][c] = solved_grid[r][c]; hint_used_cells.add((r,c))
                        is_super_hint_mode = False; check_victory_condition()
                    elif is_fast_mode and selected_digit: attempt_place_number(r, c, selected_digit)
                    else:
                        selected_cell = (r, c); cell_selection_time = time.time()
                        if grid[r][c] != 0: selected_digit = grid[r][c]
                tool_y = grid_y + grid_h + 15; pad_y = tool_y + 60
                cols = grid_size if grid_size <= 9 else 8
                bw = (WIDTH - 20) // cols; bh = 60
                if pad_y <= y < HEIGHT - 80:
                    rel_y = y - pad_y
                    row_idx = rel_y // (bh + 5); col_idx = (x - 10) // bw
                    idx = -1
                    if grid_size <= 9:
                        if row_idx == 0 and 0 <= col_idx < grid_size: idx = col_idx + 1
                    else:
                        if 0 <= row_idx <= 1 and 0 <= col_idx < 8: idx = row_idx * 8 + col_idx + 1
                    if 1 <= idx <= max_digit:
                        if is_fast_mode: selected_digit = idx
                        else:
                            if selected_cell: r, c = selected_cell; attempt_place_number(r, c, idx)
                            else: selected_digit = idx

            if game_state == "GAME" and event.type == pygame.KEYDOWN and selected_cell:
                r, c = selected_cell
                if initial_grid[r][c] == 0:
                    val = -1
                    if event.key in range(pygame.K_1, pygame.K_9 + 1): val = int(event.unicode)
                    if val != -1: attempt_place_number(r, c, val)
                    if event.key == pygame.K_BACKSPACE: grid[r][c]=0; validation_grid[r][c]=None

        if game_state == "SPLASH": draw_splash_screen()
        elif game_state == "MAIN_MENU": draw_main_menu()
        elif game_state == "MODE_SELECT": draw_mode_select()
        elif game_state == "SETTINGS": draw_settings()
        elif game_state == "GAME": draw_game_screen()
        elif game_state == "PAUSE": 
            draw_game_screen() 
            draw_pause_menu()
        elif game_state in ["GAME_OVER", "VICTORY_SCREEN"]: draw_overlay("GAME OVER", "No lives left!") if game_state == "GAME_OVER" else draw_overlay("VICTORY!", f"Score: {score}")
        
        pygame.display.flip()
        clock.tick(30)
    pygame.quit(); sys.exit()

if __name__ == "__main__":
    main()