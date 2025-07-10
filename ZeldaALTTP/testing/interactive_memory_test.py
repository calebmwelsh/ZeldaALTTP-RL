import os
import sys
from pathlib import Path

# --- Logging directory in ZeldaALTTP/logs ---
LOGS_DIR = Path(__file__).resolve().parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

import time

import pygame
from mgba._pylib import ffi
import mgba.log
from ZeldaALTTP.utils.path_utils import get_rom_path, get_states_dir
from pygba import PyGBA, PyGBAEnv
from pygba.game_wrappers.utils.zelda_utils import *

mgba.log.silence()



# --- Ensure directories exist ---
get_states_dir().mkdir(exist_ok=True)

# --- Paths ---
ROM_PATH = get_rom_path()
SAVE_STATE_PATH = get_states_dir() / "StartPos.state"
USER_PRINT_FILE = LOGS_DIR / "user_prints.log"


# Erase user_prints.log at program start
USER_PRINT_FILE.write_text("")

def user_print(*args, **kwargs):
    with open(USER_PRINT_FILE, "a") as f:
        print(*args, **kwargs, file=f)

def load_save_state(env, save_file_path):
    try:
        save_data = Path(save_file_path).read_bytes()
        state = ffi.new("uint8_t[]", save_data)
        success = env.gba.core.load_raw_state(state)
        return success
    except Exception as e:
        user_print(f"Error loading save state: {e}")
        return False

def create_save_state(env, rom_name):
    try:
        state = env.gba.core.save_raw_state()
        state_bytes = bytes(ffi.buffer(state))
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        rom_name = Path(rom_name).stem
        save_dir = get_states_dir()
        save_file = save_dir / f"{rom_name}_savestate_{timestamp}.state"
        save_file.write_bytes(state_bytes)
        return save_file
    except Exception as e:
        user_print(f"Error creating save state: {e}")
        return None

def print_player_xy_periodically(gba, last_print_time, interval=5.0):
    """Prints the player's X and Y coordinates every `interval` seconds."""
    now = time.time()
    if now - last_print_time >= interval:
        x = read_player_x(gba)
        y = read_player_y(gba)
        area_info = get_area_description(gba)
        user_print(f"Player position: x={x}, y={y} | {area_info}")
        return now
    return last_print_time

def main():
    print(f"ROM_PATH: {ROM_PATH}")
    if not Path(ROM_PATH).exists():
        user_print(f"ROM file not found: {ROM_PATH}")
        return
    
    if not Path(SAVE_STATE_PATH).exists():
        user_print(f"Save state file not found: {SAVE_STATE_PATH}")
        return
    
    user_print("Loading ROM...")
    user_print("Controls:")
    user_print("Arrow keys: Movement")
    user_print("Z: A button")
    user_print("X: B button")
    user_print("Enter: Start")
    user_print("Right Shift: Select")
    user_print("A: L button")
    user_print("S: R button")
    user_print("ESC: Exit")
    user_print("F: Toggle fast-forward")
    user_print("P: Save state")
    user_print("I: Print player position and area info")

    gba = PyGBA.load(ROM_PATH)
    env = PyGBAEnv(
        gba=gba,
        render_mode="human",
        obs_type="rgb",
        frameskip=0,
        repeat_action_probability=0.0,
    )
    observation, info = env.reset()



    user_print(f"Loading save state: {SAVE_STATE_PATH}")
    if load_save_state(env, SAVE_STATE_PATH):
        user_print("Save state loaded successfully!")
    else:
        user_print("Failed to load save state!")
        env.close()
        pygame.quit()
        return

    running = True
    fast_forward = False
    try:
        # with open(RUPEES_FILE, "w") as rupee_log, open(HEALTH_FILE, "w") as health_log:
        frame = 0
        prev_health = None  # Track previous health value
        prev_rupees = None  # Track previous rupee value
        prev_small_keys = None  # Track previous small keys value
        prev_bombs = None  # Track previous bombs value
        prev_maps = None  # Track previous maps value
        prev_master_key = None  # Track previous master key value
        prev_boomerang = None  # Track previous boomerang value
        prev_lamp = None  # Track previous lamp value
        prev_sword = None  # Track previous sword value
        prev_enemies_killed = None  # Track previous enemies killed value
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_f:
                        fast_forward = not fast_forward
                        env.frameskip = 64 if fast_forward else 0
                        user_print("Fast-forward:", "ON" if fast_forward else "OFF")
                    elif event.key == pygame.K_p:
                        save_file = create_save_state(env, ROM_PATH)
                        if save_file:
                            user_print(f"Save state created: {save_file}")
                        else:
                            user_print("Failed to create save state")
                    elif event.key == pygame.K_i:
                        x = read_player_x(gba)
                        y = read_player_y(gba)
                        area_info = get_area_description(gba)
                        user_print(f"Player position: x={x}, y={y} | {area_info}")
            keys = pygame.key.get_pressed()
            direction = None
            if keys[pygame.K_UP]:
                direction = "up"
            elif keys[pygame.K_DOWN]:
                direction = "down"
            elif keys[pygame.K_LEFT]:
                direction = "left"
            elif keys[pygame.K_RIGHT]:
                direction = "right"
            button = None
            if keys[pygame.K_z]:
                button = "B"
            elif keys[pygame.K_x]:
                button = "A"
            elif keys[pygame.K_RETURN]:
                button = "start"
            elif keys[pygame.K_RSHIFT]:
                button = "select"
            elif keys[pygame.K_a]:
                button = "L"
            elif keys[pygame.K_s]:
                button = "R"
            action = env.get_action_id(direction, button)
            observation, reward, done, truncated, info = env.step(action)
            env.render()
            # --- Log rupee and health count ---
            rupees = read_rupees(gba)
            health = read_player_health(gba)
            small_keys = read_small_keys(gba)
            bombs = read_bombs(gba)
            maps = read_maps(gba)
            master_key = read_master_key(gba)
            boomerang = read_boomerang(gba)
            lamp = read_lamp(gba)
            sword = read_sword(gba)
            enemies_killed = read_enemies_killed(gba)
            # Print to user_prints.log if health changes
            if prev_health is None or health != prev_health:
                user_print(f"Health changed: {prev_health} -> {health} (frame {frame})")
            prev_health = health
            # Print to user_prints.log if rupees change
            if prev_rupees is None or rupees != prev_rupees:
                user_print(f"Rupees changed: {prev_rupees} -> {rupees} (frame {frame})")
            prev_rupees = rupees
            # Print to user_prints.log if small keys change
            if prev_small_keys is None or small_keys != prev_small_keys:
                user_print(f"Small keys changed: {prev_small_keys} -> {small_keys} (frame {frame})")
            prev_small_keys = small_keys
            # Print to user_prints.log if bombs change
            if prev_bombs is None or bombs != prev_bombs:
                user_print(f"Bombs changed: {prev_bombs} -> {bombs} (frame {frame})")
            prev_bombs = bombs
            # Print to user_prints.log if maps change
            if prev_maps is None or maps != prev_maps:
                user_print(f"Maps changed: {prev_maps} -> {maps} (frame {frame})")
            prev_maps = maps
            # Print to user_prints.log if master key changes
            if prev_master_key is None or master_key != prev_master_key:
                user_print(f"Master key changed: {prev_master_key} -> {master_key} (frame {frame})")
            prev_master_key = master_key
            # Print to user_prints.log if boomerang changes
            if prev_boomerang is None or boomerang != prev_boomerang:
                user_print(f"Boomerang changed: {prev_boomerang} -> {boomerang} (frame {frame})")
            prev_boomerang = boomerang
            # Print to user_prints.log if lamp changes
            if prev_lamp is None or lamp != prev_lamp:
                user_print(f"Lamp changed: {prev_lamp} -> {lamp} (frame {frame})")
            prev_lamp = lamp
            # Print to user_prints.log if sword changes
            if prev_sword is None or sword != prev_sword:
                user_print(f"Sword changed: {prev_sword} -> {sword} (frame {frame})")
            prev_sword = sword
            # Print to user_prints.log if enemies killed changes
            if prev_enemies_killed is None or enemies_killed != prev_enemies_killed:
                user_print(f"Enemies killed changed: {prev_enemies_killed} -> {enemies_killed} (frame {frame})")
            prev_enemies_killed = enemies_killed
            frame += 1
            if done or not running:
                user_print("Game session ended")
                break
    except KeyboardInterrupt:
        user_print("\nStopping emulation...")
    finally:
        env.close()
        pygame.quit()

if __name__ == "__main__":
    pygame.init()
    main() 