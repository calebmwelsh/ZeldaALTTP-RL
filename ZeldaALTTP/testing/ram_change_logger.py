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
from ZeldaALTTP.utils.path_utils import get_rom_path, get_saves_dir, get_states_dir
from pygba import PyGBA, PyGBAEnv
from pygba.game_wrappers.utils.zelda_utils import *

mgba.log.silence()


# --- Ensure directories exist ---
get_states_dir().mkdir(exist_ok=True)

# --- Paths ---
ROM_PATH = get_rom_path()
SAVE_STATE_PATH = get_states_dir() / "Zelda_1.state"
USER_PRINT_FILE = LOGS_DIR / "user_prints.log"


# --- Logging directory ---
LOGS_DIR = Path(__file__).resolve().parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)
RAM_LOG_FILE = LOGS_DIR / "ram_changes.log"


# GBA memory regions
MEMORY_REGIONS = {
    'BIOS':   (0x00000000, 0x00003FFF),
    'EWRAM':  (0x02000000, 0x0203FFFF),
    'IWRAM':  (0x03000000, 0x03007FFF),
    'VRAM':   (0x06000000, 0x06017FFF),
    'OAM':    (0x07000000, 0x070003FF),
    'ROM':    (0x08000000, 0x09FFFFFF),
}

# Global variable to select which region to monitor
MEMORY_REGION = 'EWRAM'

# Get the address range for the selected region
REGION_START, REGION_END = MEMORY_REGIONS[MEMORY_REGION]

# Number of frames to scan for volatile addresses at start
VOLATILITY_SCAN_FRAMES = 10

# Set to store volatile addresses
volatile_addresses = set()

# List of address ranges to ignore (inclusive)
IGNORE_ADDR_RANGES = [
    # (0x02005480, 0x020057F0),  # User-specified ignore range - text
    # (0x02003080, 0x02010509),  # User-specified ignore range - text
    # (0x02000402, 0x020005A3),  # User-specified ignore range - text 
    # (0x0201050A, 0x0201058D),  # User-specified ignore range - text
    # (0x02000400, 0x02018BDB),  # User-specified ignore range - Zelda Door
]

def is_ignored_address(addr):
    for start, end in IGNORE_ADDR_RANGES:
        if start <= addr <= end:
            return True
    return False

def log_wram_change(frame, addr, old, new):
    with open(RAM_LOG_FILE, "a") as f:
        f.write(f"frame {frame} | addr 0x{addr:08X} | {int(old)} -> {int(new)}\n")


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

    # Erase WRAM log at program start
    RAM_LOG_FILE.write_text("")

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
    frame = 0
    prev_wram = None
    # For volatility scan
    volatility_scan_counts = None
    try:
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

            wram = gba.read_memory(REGION_START, REGION_END - REGION_START + 1)
            if prev_wram is not None:
                if frame < VOLATILITY_SCAN_FRAMES:
                    # Volatility scan phase
                    if volatility_scan_counts is None:
                        volatility_scan_counts = [0] * (REGION_END - REGION_START + 1)
                    for i in range(REGION_END - REGION_START + 1):
                        if wram[i] != prev_wram[i]:
                            volatility_scan_counts[i] += 1
                    if frame == VOLATILITY_SCAN_FRAMES - 1:
                        # After scan, mark addresses that changed every frame as volatile
                        for i, count in enumerate(volatility_scan_counts):
                            if count == VOLATILITY_SCAN_FRAMES:
                                volatile_addresses.add(REGION_START + i)
                        user_print(f"Volatile addresses detected: {len(volatile_addresses)} (not monitored)")
                else:
                    # Normal monitoring, skip volatile addresses and ignored addresses
                    for i in range(REGION_END - REGION_START + 1):
                        addr = REGION_START + i
                        if addr in volatile_addresses:
                            continue
                        if is_ignored_address(addr):
                            continue
                        if wram[i] != prev_wram[i]:
                            log_wram_change(frame, addr, prev_wram[i], wram[i])
            prev_wram = wram
            frame += 1

            action = env.get_action_id(direction, button)
            observation, reward, done, truncated, info = env.step(action)
            env.render()
            
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




