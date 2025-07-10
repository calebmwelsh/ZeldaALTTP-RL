import os
import sys
import pygame
import json
from datetime import datetime
import time
import math
import glob
import re
from pathlib import Path

# Add utils to path for animation handler
UTILS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'utils')
if UTILS_PATH not in sys.path:
    sys.path.append(UTILS_PATH)

from utils.settings import config

# Load ReplayVisualization config
replay_cfg = config["ReplayVisualization"]

# Load Paths config
paths_cfg = config["Paths"]

# Base path for assets and data
BASE_PATH = os.path.abspath(paths_cfg["base_path"])
ASSETS_PATH = os.path.join(BASE_PATH, paths_cfg["assets_path"])
SESSIONS_PATH = os.path.join(BASE_PATH, paths_cfg["sessions_path"])

# World map image
WORLD_MAP_IMAGE = replay_cfg["world_map_image"]

from animation_handler import AnimationManager

# Initialize Pygame
pygame.init()

# GLOBAL SCREEN SIZE OPTION: 'FULL', 'HALF', 'SMALL'
SCREEN_SIZE_OPTION = replay_cfg["screen_size_option"]
if SCREEN_SIZE_OPTION.upper() == 'FULL':
    SCREEN_WIDTH, SCREEN_HEIGHT = 1728, 1080
elif SCREEN_SIZE_OPTION.upper() == 'HALF':
    SCREEN_WIDTH, SCREEN_HEIGHT = 960, 600
elif SCREEN_SIZE_OPTION.upper() == 'SMALL':
    SCREEN_WIDTH, SCREEN_HEIGHT = 400, 300
SPRITE_SCALE = replay_cfg["sprite_scale"]
FPS = replay_cfg["fps"]

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Movement and position thresholds
TELEPORT_THRESHOLD = replay_cfg["teleport_threshold"]

# Show label above Links (env-ep)
SHOW_LABEL = replay_cfg["show_label"]

# Camera manual offset (for camera hold mode)
camera_offset_x = 0
camera_offset_y = 0
CAMERA_MOVE_SPEED = replay_cfg["camera_move_speed"]  # pixels per frame

# GLOBAL: NUMBER OF MOVEMENT FILES TO LOAD ('ALL' or an integer)
NUM_MOVEMENT_FILES = replay_cfg["num_movement_files"]  # e.g., 'ALL' or 20

# Global: episode number to filter movement files (-1 means all)
EPISODE_NUMBER = replay_cfg["episode_number"]

# Global: skip to position in replay (number of steps to skip at start)
SKIP_TO_POSITION = replay_cfg["skip_to_position"]

# Global: which envs to load (int for single, list for multiple, or 'all')
ENVS_TO_LOAD = replay_cfg["envs_to_load"]  # e.g., 2, [0, 2, 5], or 'all'

# Global Link position offset
LINK_POS_OFFSET_X = replay_cfg["link_pos_offset_x"]
LINK_POS_OFFSET_Y = replay_cfg["link_pos_offset_y"]

# Global zoom level
ZOOM_LEVEL = replay_cfg.get("zoom_level", 1.0)
ZOOM_MIN = 0.25
ZOOM_MAX = 4.0
ZOOM_STEP = 0.1

# Create the screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Movement Replay")
clock = pygame.time.Clock()

# model number
MODEL_NUMBER = replay_cfg["model_number"]
MODEL_BASE = MODEL_NUMBER.split('.')[0]  

# Base sessions directory (relative to this script)
SESSIONS_BASE = Path(__file__).parent.parent.parent / 'sessions'

# Find the session directory for the given model number
model_dir = SESSIONS_BASE / f"model {MODEL_BASE}"
session_pattern = str(model_dir / f"session_*_{MODEL_NUMBER}")
session_dirs = glob.glob(session_pattern)

if not session_dirs:
    raise FileNotFoundError(f"No session directory found for model {MODEL_NUMBER} in {model_dir}")

# If multiple, pick the latest (sorted by name, which includes timestamp)
session_dir = sorted(session_dirs)[-1]
movements_folder = os.path.join(session_dir, "movements")

def scale_image(image, scale_factor):
    """Scale an image up by the given factor while maintaining pixel sharpness"""
    return pygame.transform.scale(image, 
                                (int(image.get_width() * scale_factor), 
                                 int(image.get_height() * scale_factor)))

def load_map(path, scale=1):
    """Load the world map"""
    try:
        map_img = pygame.image.load(path)
        if scale != 1:
            map_img = pygame.transform.scale(map_img, 
                                          (int(map_img.get_width() * scale),
                                           int(map_img.get_height() * scale)))
        return map_img
    except pygame.error as e:
        print(f"Couldn't load map {path}: {e}")
        # Create a colored rectangle as fallback
        surf = pygame.Surface((800, 600))
        surf.fill((100, 100, 100))  # Gray for missing map
        return surf

class Camera:
    def __init__(self, width, height, map_width, map_height):
        self.width = width
        self.height = height
        self.map_width = map_width
        self.map_height = map_height
        self.x = 0
        self.y = 0
    
    def update(self, target_x, target_y):
        """Update camera position to follow target"""
        # Center the camera on the target
        self.x = target_x - self.width // 2 / ZOOM_LEVEL
        self.y = target_y - self.height // 2 / ZOOM_LEVEL
        
        # Keep camera within map bounds
        self.x = max(0, min(self.x, self.map_width - self.width / ZOOM_LEVEL))
        self.y = max(0, min(self.y, self.map_height - self.height / ZOOM_LEVEL))
    
    def set_position(self, x, y):
        self.x = max(0, min(x, self.map_width - self.width / ZOOM_LEVEL))
        self.y = max(0, min(y, self.map_height - self.height / ZOOM_LEVEL))
    
    def apply(self, x, y):
        """Convert world coordinates to screen coordinates, considering zoom"""
        return int((x - self.x) * ZOOM_LEVEL), int((y - self.y) * ZOOM_LEVEL)

class ReplayVisualizer:
    def __init__(self):
        global camera_offset_x, camera_offset_y, ZOOM_LEVEL
        # Font for episode numbers
        BASE_FONT_SIZE = 12
        def get_scaled_font():
            size = max(8, int(BASE_FONT_SIZE * ZOOM_LEVEL))
            return pygame.font.SysFont(None, size)
        self.get_scaled_font = get_scaled_font
        self.font = get_scaled_font()
        # Load world map
        self.world_map_orig = load_map(os.path.join(ASSETS_PATH, WORLD_MAP_IMAGE))
        self.map_width_orig = self.world_map_orig.get_width()
        self.map_height_orig = self.world_map_orig.get_height()
        # Initial zoomed map
        self.world_map = scale_image(self.world_map_orig, ZOOM_LEVEL)
        self.map_width = self.world_map.get_width()
        self.map_height = self.world_map.get_height()
        # Initialize camera
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT, self.map_width_orig, self.map_height_orig)
        # Initialize animation manager and load animations
        self.manager = AnimationManager()
        self.animations = {
            'down': self.manager.get_animation('run_down'),
            'up': self.manager.get_animation('run_up'),
            'right': self.manager.get_animation('run_horizontal')
        }
        self.animations['left'] = self.manager.get_animation('run_horizontal')
        # Load all movement files 
        def extract_episode(filename):
            match = re.search(r"episode_(\d+)", filename)
            return int(match.group(1)) if match else -1
        self.extract_episode = extract_episode
        # Determine which env folders to load
        all_env_dirs = sorted([d for d in os.listdir(movements_folder) if os.path.isdir(os.path.join(movements_folder, d)) and d.startswith('env_')], key=lambda x: int(x.split('_')[1]))
        if str(ENVS_TO_LOAD).upper() == 'ALL':
            env_dirs = all_env_dirs
        elif isinstance(ENVS_TO_LOAD, int):
            env_dirs = [f'env_{ENVS_TO_LOAD}'] if f'env_{ENVS_TO_LOAD}' in all_env_dirs else []
        elif isinstance(ENVS_TO_LOAD, list):
            env_dirs = [f'env_{i}' for i in ENVS_TO_LOAD if f'env_{i}' in all_env_dirs]
        else:
            env_dirs = []
        all_files = []
        for env_dir in env_dirs:
            env_path = os.path.join(movements_folder, env_dir)
            env_files = glob.glob(os.path.join(env_path, "*.json"))
            all_files.extend(env_files)
        # Filter by episode number if set
        if int(EPISODE_NUMBER) >= 0:
            all_files = [f for f in all_files if extract_episode(f) == int(EPISODE_NUMBER)]
        all_files_sorted = sorted(all_files, key=extract_episode, reverse=True)
        if str(NUM_MOVEMENT_FILES).upper() == "ALL":
            movement_files = all_files_sorted
        else:
            try:
                n = int(NUM_MOVEMENT_FILES)
                movement_files = all_files_sorted[:n]
            except Exception:
                movement_files = all_files_sorted[:20]  # fallback
        # Find the file with the highest episode number
        self.episode_numbers = [extract_episode(f) for f in movement_files]
        # Extract env numbers from file paths
        def extract_env(filename):
            match = re.search(r"env_(\d+)", filename)
            return int(match.group(1)) if match else -1
        self.env_numbers = [extract_env(f) for f in movement_files]
        if self.episode_numbers:
            self.highest_episode_index = self.episode_numbers.index(max(self.episode_numbers))
        else:
            self.highest_episode_index = 0
        # Camera follow index (default to highest episode)
        self.camera_follow_index = self.highest_episode_index
        self.all_movements = []
        for mf in movement_files:
            with open(mf, "r") as f:
                movement_data = json.load(f)
                self.all_movements.append(movement_data["movements"])
        self.num_links = len(self.all_movements)
        self.movement_indices = []
        self.positions = []
        self.directions = []
        self.facings = []
        self.idles = []
        self.finished_links = []  # Track if each Link has finished its movements
        for movements in self.all_movements:
            # Set initial index to SKIP_TO_POSITION, but clamp to last index if too large
            if movements:
                start_idx = min(SKIP_TO_POSITION, len(movements) - 1)
                self.movement_indices.append(start_idx)
                first = movements[start_idx]
                self.positions.append([first["world_x"], first["world_y"]])
                self.directions.append(first["direction"].lower() if first["direction"] != 'none' else 'down')
                self.facings.append(False)
                self.idles.append(first["direction"].lower() == 'none')
                self.finished_links.append(False)
            else:
                self.movement_indices.append(0)
                self.positions.append([self.map_width // 2, self.map_height // 2])
                self.directions.append('down')
                self.facings.append(False)
                self.idles.append(False)
                self.finished_links.append(True)
        # Movement speed (pixels per second)
        self.SPEED = 70 * SPRITE_SCALE  # Scale speed to match sprite scale
        # Mode control
        self.replay_mode = True
        # Global: camera hold toggle
        self.camera_hold = False
        self.running = True
        self.clock = clock
        self.screen = screen
        # Add dagger knights
        from utils.knight import Knight
        self.knights = [
            Knight(2785, 2917, self.manager, sprite_scale=SPRITE_SCALE, zoom_level=ZOOM_LEVEL, knight_type='dagger'),
            Knight(2815, 2917, self.manager, sprite_scale=SPRITE_SCALE, zoom_level=ZOOM_LEVEL, knight_type='dagger'),
            Knight(2005, 1900, self.manager, sprite_scale=SPRITE_SCALE, zoom_level=ZOOM_LEVEL, knight_type='dagger'),
            Knight(2085, 1900, self.manager, sprite_scale=SPRITE_SCALE, zoom_level=ZOOM_LEVEL, knight_type='dagger'),
            Knight(2045, 1936, self.manager, sprite_scale=SPRITE_SCALE, zoom_level=ZOOM_LEVEL, knight_type='sword')
        ]
        
    def run(self):
        global camera_offset_x, camera_offset_y, ZOOM_LEVEL
        while self.running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_r:  # Toggle replay mode
                        self.replay_mode = not self.replay_mode
                        print(f"{'Replay' if self.replay_mode else 'Manual'} mode activated")
                    elif event.key == pygame.K_c:  # Toggle camera hold
                        self.camera_hold = not self.camera_hold
                        if self.camera_hold:
                            camera_offset_x = self.camera.x
                            camera_offset_y = self.camera.y
                        print(f"Camera hold: {'ON' if self.camera_hold else 'OFF'}")
                    elif self.replay_mode and event.key == pygame.K_LEFT:
                        self.camera_follow_index = min(self.num_links - 1, self.camera_follow_index + 1)
                        print(f"Camera now following EP {self.episode_numbers[self.camera_follow_index]}")
                    elif self.replay_mode and event.key == pygame.K_RIGHT:
                        self.camera_follow_index = max(0, self.camera_follow_index - 1)
                        print(f"Camera now following EP {self.episode_numbers[self.camera_follow_index]}")
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        # Zoom out
                        prev_zoom = ZOOM_LEVEL
                        ZOOM_LEVEL = max(ZOOM_MIN, ZOOM_LEVEL - ZOOM_STEP)
                        if ZOOM_LEVEL != prev_zoom:
                            self.world_map = scale_image(self.world_map_orig, ZOOM_LEVEL)
                            self.map_width = self.world_map.get_width()
                            self.map_height = self.world_map.get_height()
                            self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT, self.map_width_orig, self.map_height_orig)
                            self.font = self.get_scaled_font()
                            print(f"Zoomed out: {ZOOM_LEVEL:.2f}x")
                    elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                        # Zoom in
                        prev_zoom = ZOOM_LEVEL
                        ZOOM_LEVEL = min(ZOOM_MAX, ZOOM_LEVEL + ZOOM_STEP)
                        if ZOOM_LEVEL != prev_zoom:
                            self.world_map = scale_image(self.world_map_orig, ZOOM_LEVEL)
                            self.map_width = self.world_map.get_width()
                            self.map_height = self.world_map.get_height()
                            self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT, self.map_width_orig, self.map_height_orig)
                            self.font = self.get_scaled_font()
                            print(f"Zoomed in: {ZOOM_LEVEL:.2f}x")
                    elif event.key == pygame.K_p:
                        # Only restart if all Links are finished
                        if all(self.finished_links):
                            for i in range(self.num_links):
                                self.movement_indices[i] = 0
                                if self.all_movements[i]:
                                    first = self.all_movements[i][0]
                                    self.positions[i] = [first["world_x"], first["world_y"]]
                                    self.directions[i] = first["direction"].lower() if first["direction"] != 'none' else 'down'
                                    self.idles[i] = first["direction"].lower() == 'none'
                                    self.finished_links[i] = False
                                else:
                                    self.positions[i] = [self.map_width // 2, self.map_height // 2]
                                    self.directions[i] = 'down'
                                    self.idles[i] = False
                                    self.finished_links[i] = True
            # Get time since last frame
            dt = self.clock.get_time() / 1000.0  # Convert to seconds
            # Always get key state for WASD
            keys = pygame.key.get_pressed()
            # Camera movement with WASD when camera_hold is ON
            if self.camera_hold:
                before_x, before_y = camera_offset_x, camera_offset_y
                if keys[pygame.K_a]:
                    camera_offset_x -= CAMERA_MOVE_SPEED / ZOOM_LEVEL
                if keys[pygame.K_d]:
                    camera_offset_x += CAMERA_MOVE_SPEED / ZOOM_LEVEL
                if keys[pygame.K_w]:
                    camera_offset_y -= CAMERA_MOVE_SPEED / ZOOM_LEVEL
                if keys[pygame.K_s]:
                    camera_offset_y += CAMERA_MOVE_SPEED / ZOOM_LEVEL
                # Clamp camera offset to map bounds
                camera_offset_x = max(0, min(camera_offset_x, self.map_width_orig - SCREEN_WIDTH / ZOOM_LEVEL))
                camera_offset_y = max(0, min(camera_offset_y, self.map_height_orig - SCREEN_HEIGHT / ZOOM_LEVEL))
                if (before_x, before_y) != (camera_offset_x, camera_offset_y):
                    print(f"Camera offset changed: ({camera_offset_x}, {camera_offset_y})")
                self.camera.set_position(camera_offset_x, camera_offset_y)
            if self.replay_mode:
                for i in range(self.num_links):
                    if self.finished_links[i]:
                        continue  # Do not update finished Links
                    movements = self.all_movements[i]
                    idx = self.movement_indices[i]
                    if len(movements) == 0:
                        self.finished_links[i] = True
                        continue
                    if idx >= len(movements) - 1:
                        # Determine true end position (before teleport/respawn)
                        last_movement = movements[-1]
                        if len(movements) > 1:
                            prev_movement = movements[-2]
                            area_changed = last_movement.get('area') != prev_movement.get('area')
                            dist = math.hypot(
                                last_movement["world_x"] - prev_movement["world_x"],
                                last_movement["world_y"] - prev_movement["world_y"]
                            )
                            is_teleport = area_changed or dist > 100  # 100 pixels as teleport threshold
                            if is_teleport:
                                end_x = prev_movement["world_x"]
                                end_y = prev_movement["world_y"]
                            else:
                                end_x = last_movement["world_x"]
                                end_y = last_movement["world_y"]
                        else:
                            end_x = last_movement["world_x"]
                            end_y = last_movement["world_y"]
                        # Instantly set position and freeze
                        self.positions[i] = [end_x, end_y]
                        self.directions[i] = 'down'
                        self.idles[i] = True
                        self.finished_links[i] = True
                        continue
                    current_movement = movements[idx]
                    target_x = current_movement["world_x"]
                    target_y = current_movement["world_y"]
                    new_direction = current_movement["direction"].lower()
                    pos_x, pos_y = self.positions[i]
                    dx = target_x - pos_x
                    dy = target_y - pos_y
                    dist = math.hypot(dx, dy)
                    # Axis-aligned movement: move along X first, then Y
                    step = self.SPEED * dt
                    idle = (new_direction == 'none')
                    if dist > TELEPORT_THRESHOLD:
                        pos_x = target_x
                        pos_y = target_y
                        if not idle:
                            if new_direction == 'left':
                                self.facings[i] = True
                            elif new_direction == 'right':
                                self.facings[i] = False
                            self.directions[i] = new_direction if new_direction != 'none' else self.directions[i]
                        self.idles[i] = idle
                        self.movement_indices[i] += 1
                    elif abs(dx) > 1:
                        # Move along X axis only
                        move_x = min(abs(dx), step) * (1 if dx > 0 else -1)
                        pos_x += move_x
                        # Snap if close
                        if abs(target_x - pos_x) < 1:
                            pos_x = target_x
                        # Set direction for animation
                        if not idle:
                            if dx < 0:
                                self.directions[i] = 'left'
                                self.facings[i] = True
                            elif dx > 0:
                                self.directions[i] = 'right'
                                self.facings[i] = False
                        self.idles[i] = idle
                    elif abs(dy) > 1:
                        # Move along Y axis only
                        move_y = min(abs(dy), step) * (1 if dy > 0 else -1)
                        pos_y += move_y
                        # Snap if close
                        if abs(target_y - pos_y) < 1:
                            pos_y = target_y
                        # Set direction for animation
                        if not idle:
                            if dy < 0:
                                self.directions[i] = 'up'
                            elif dy > 0:
                                self.directions[i] = 'down'
                        self.idles[i] = idle
                    else:
                        # At target, advance
                        self.movement_indices[i] += 1
                        self.idles[i] = idle
                    self.positions[i] = [pos_x, pos_y]
                # Camera follows the Link with the highest episode number
                if not self.camera_hold:
                    self.camera.update(int(self.positions[self.camera_follow_index][0]), int(self.positions[self.camera_follow_index][1]))
            else:
                # Manual mode only controls the first Link
                moving = False
                new_direction = self.directions[0]
                pos_x, pos_y = self.positions[0]
                if keys[pygame.K_LEFT]:
                    pos_x -= self.SPEED * dt
                    new_direction = 'left'
                    self.facings[0] = True
                    moving = True
                elif keys[pygame.K_RIGHT]:
                    pos_x += self.SPEED * dt
                    new_direction = 'right'
                    self.facings[0] = False
                    moving = True
                if keys[pygame.K_UP]:
                    pos_y -= self.SPEED * dt
                    new_direction = 'up'
                    moving = True
                elif keys[pygame.K_DOWN]:
                    pos_y += self.SPEED * dt
                    new_direction = 'down'
                    moving = True
                pos_x = max(0, min(pos_x, self.map_width))
                pos_y = max(0, min(pos_y, self.map_height))
                self.positions[0] = [pos_x, pos_y]
                self.directions[0] = new_direction
                self.idles[0] = not moving
                # Camera follows the Link with the highest episode number
                if not self.camera_hold:
                    self.camera.update(int(self.positions[self.camera_follow_index][0]), int(self.positions[self.camera_follow_index][1]))
            # Update animation
            for i in range(self.num_links):
                if self.finished_links[i]:
                    continue  # Do not update animation for finished Links
                current_direction = self.directions[i]
                facing_left = self.facings[i]
                idle = self.idles[i]
                if not self.replay_mode or (self.replay_mode and not idle):
                    self.animations[current_direction].play(dt)
                else:
                    self.animations[current_direction].rewind()
            # Update knights
            for knight in self.knights:
                knight.zoom_level = ZOOM_LEVEL
                knight.update(dt)
            # Clear screen with black background
            self.screen.fill(BLACK)
            # Draw map (bottom layer)
            map_x, map_y = self.camera.apply(0, 0)
            self.screen.blit(self.world_map, (map_x, map_y))
            # Draw dagger knights (above map, below Links)
            for knight in self.knights:
                knight.draw(self.screen, self.camera)
            # Draw all Links
            for i in range(self.num_links):
                pos_x, pos_y = self.positions[i]
                if self.finished_links[i]:
                    # Draw static first frame of 'down' animation at final position
                    static_img = self.animations['down'].animation_data.img_list[0][0]
                    sprite_scale = SPRITE_SCALE * ZOOM_LEVEL
                    static_img_scaled = scale_image(static_img, sprite_scale)
                    screen_x, screen_y = self.camera.apply(int(pos_x + LINK_POS_OFFSET_X), int(pos_y + LINK_POS_OFFSET_Y))
                    img_rect = static_img_scaled.get_rect()
                    img_rect.center = (screen_x, screen_y)
                    self.screen.blit(static_img_scaled, img_rect)
                    # Draw env and episode number above Link
                    if SHOW_LABEL:
                        env_label = self.env_numbers[i] if i < len(self.env_numbers) else '?'
                        ep_label = self.episode_numbers[i] if i < len(self.episode_numbers) else '?'
                        label = f"{env_label}-{ep_label}"
                        ep_text = self.font.render(label, True, WHITE)
                        text_rect = ep_text.get_rect(center=(screen_x, screen_y - img_rect.height//2 - 6))
                        self.screen.blit(ep_text, text_rect)
                else:
                    current_direction = self.directions[i]
                    facing_left = self.facings[i]
                    idle = self.idles[i]
                    current_img = self.animations[current_direction].img
                    if current_img is not None:
                        # Apply zoom to sprite
                        sprite_scale = SPRITE_SCALE * ZOOM_LEVEL
                        current_img_scaled = scale_image(current_img, sprite_scale)
                        if facing_left:
                            current_img_scaled = pygame.transform.flip(current_img_scaled, True, False)
                        # Apply global offset to Link position
                        screen_x, screen_y = self.camera.apply(int(pos_x + LINK_POS_OFFSET_X), int(pos_y + LINK_POS_OFFSET_Y))
                        img_rect = current_img_scaled.get_rect()
                        img_rect.center = (screen_x, screen_y)
                        self.screen.blit(current_img_scaled, img_rect)
                        # Draw env and episode number above Link
                        if SHOW_LABEL:
                            env_label = self.env_numbers[i] if i < len(self.env_numbers) else '?'
                            ep_label = self.episode_numbers[i] if i < len(self.episode_numbers) else '?'
                            label = f"{env_label}-{ep_label}"
                            ep_text = self.font.render(label, True, WHITE)
                            text_rect = ep_text.get_rect(center=(screen_x, screen_y - img_rect.height//2 - 6))
                            self.screen.blit(ep_text, text_rect)
            # Print debug info for the followed Link
            followed_pos = self.positions[self.camera_follow_index]
            # print(f"[{'REPLAY' if self.replay_mode else 'MANUAL'}] Following EP {self.episode_numbers[self.camera_follow_index]} - Pos: ({int(followed_pos[0])}, {int(followed_pos[1])}) - Dir: {self.directions[self.camera_follow_index]}")
            # Update display
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()

def main():
    visualizer = ReplayVisualizer()
    visualizer.run()

if __name__ == '__main__':
    main() 