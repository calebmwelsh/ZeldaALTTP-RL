import os
import sys
from pathlib import Path
import json
import time
from datetime import datetime

import pygame
from mgba._pylib import ffi
import mgba.log
from ZeldaALTTP.utils.path_utils import get_rom_path, get_states_dir
from pygba import PyGBA, PyGBAEnv
from pygba.game_wrappers.utils.zelda_utils import read_player_xy, get_area_description

mgba.log.silence()

# --- Ensure directories exist ---
get_states_dir().mkdir(exist_ok=True)

# --- Paths ---
ROM_PATH = get_rom_path()
SAVE_STATE_PATH = get_states_dir() / "Zelda_1.state"

def load_save_state(env, save_file_path):
    """Load a save state file"""
    try:
        save_data = Path(save_file_path).read_bytes()
        state = ffi.new("uint8_t[]", save_data)
        success = env.gba.core.load_raw_state(state)
        return success
    except Exception as e:
        print(f"Error loading save state: {e}")
        return False

def create_save_state(env, rom_name):
    """Create a new save state"""
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
        print(f"Error creating save state: {e}")
        return None

class AreaMapper:
    def __init__(self):
        self.current_area = None
        self.areas = {}
        self.current_bounds = {"min_x": None, "min_y": None, "max_x": None, "max_y": None}
        self.latest_map_path = "area_map.json"  
        
        # Initialize GBA
        print("Loading ROM...")
        self.gba = PyGBA.load(ROM_PATH)
        self.env = PyGBAEnv(
            gba=self.gba,
            render_mode="human",
            obs_type="rgb",
            frameskip=0,
            repeat_action_probability=0.0,
        )
        observation, info = self.env.reset()

        # Try to load save state if it exists
        if Path(SAVE_STATE_PATH).exists():
            print(f"Loading save state: {SAVE_STATE_PATH}")
            if load_save_state(self.env, SAVE_STATE_PATH):
                print("Save state loaded successfully!")
            else:
                print("Failed to load save state!")
        
        # Try to load existing areas
        self.load_areas()
        
    def load_areas(self):
        """Load previously mapped areas"""
        latest_map = Path(__file__).resolve().parent / "area_maps" / "area_map.json"
        if Path(latest_map).exists():
            try:
                with open(latest_map) as f:
                    self.areas = json.load(f)
                self.latest_map_path = latest_map  # Track the file
                print(f"Loaded existing {len(self.areas)} area(s) from {latest_map}")
            except Exception as e:
                print(f"Error loading areas: {e}")
                self.areas = {}
                self.latest_map_path = latest_map
        else:
            self.areas = {}
            self.latest_map_path = latest_map
    
    def save_areas(self):
        """Append new/updated areas to area_map.json, preserving existing areas."""
        filepath = self.latest_map_path
        # Load existing areas from file
        if Path(filepath).exists():
            with open(filepath, "r") as f:
                file_areas = json.load(f)
        else:
            file_areas = {}
        # Update with new/changed areas
        file_areas.update(self.areas)
        with open(filepath, "w") as f:
            json.dump(file_areas, f, indent=2)
        print(f"Saved areas to {filepath}")
    
    def start_new_area(self, name):
        """Start mapping a new area"""
        self.current_area = name
        self.current_bounds = {"min_x": None, "min_y": None, "max_x": None, "max_y": None}
        print(f"\nStarting to map area: {name}")
        print("Press:")
        print("  1: Mark top-left corner")
        print("  2: Mark bottom-right corner")
        print("  S: Save current area")
        print("  Q: Quit and save all areas")
        print("  I: Display current bounds")
        print("\nGame Controls:")
        print("Arrow keys: Movement")
        print("Z: A button")
        print("X: B button")
        print("Enter: Start")
        print("Right Shift: Select")
        print("A: L button")
        print("S: R button")
        print("F: Toggle fast-forward")
        print("P: Save state")
        print("L: Load last save state")
    
    def mark_corner(self, corner_type):
        """Mark a corner of the current area"""
        if not self.current_area:
            print("Please start a new area first!")
            return
            
        x, y = read_player_xy(self.gba)
        
        if corner_type == "top_left":
            self.current_bounds["min_x"] = x
            self.current_bounds["min_y"] = y
            print(f"Marked top-left corner at ({x}, {y})")
        else:  # bottom_right
            self.current_bounds["max_x"] = x
            self.current_bounds["max_y"] = y
            print(f"Marked bottom-right corner at ({x}, {y})")
    
    def save_current_area(self):
        """Save the current area if both corners are marked, and immediately write to area_map.json"""
        if not self.current_area:
            print("No area being mapped!")
            return
        if None in self.current_bounds.values():
            print("Please mark both corners first!")
            return
        self.areas[self.current_area] = {
            "name": self.current_area,
            "x_range": [self.current_bounds["min_x"], self.current_bounds["max_x"]],
            "y_range": [self.current_bounds["min_y"], self.current_bounds["max_y"]],
        }
        self.save_areas()  # Immediately write to file
        print(f"Saved area: {self.current_area}")
        self.current_area = None
    
    def display_bounds(self):
        """Display the current area bounds and coordinates"""
        x, y = read_player_xy(self.gba)
        print("\nCurrent Status:")
        print(f"Current Position: ({x}, {y})")
        
        if self.current_area:
            print(f"Mapping Area: {self.current_area}")
            print("Bounds:")
            print(f"  Top-left:     ({self.current_bounds['min_x']}, {self.current_bounds['min_y']})")
            print(f"  Bottom-right: ({self.current_bounds['max_x']}, {self.current_bounds['max_y']})")
            missing = [k for k, v in self.current_bounds.items() if v is None]
            if missing:
                print(f"Missing bounds: {', '.join(missing)}")
        else:
            print("No area currently being mapped")
            
        if self.areas:
            print("\nMapped Areas:")
            for area_id, area_data in self.areas.items():
                print(f"  {area_id}:")
                print(f"    X range: {area_data['x_range']}")
                print(f"    Y range: {area_data['y_range']}")

    def run(self):
        """Main loop"""
        print("\nArea Mapping Tool")
        print("----------------")
        print("Commands:")
        print("  N: Start new area")
        print("  1: Mark top-left corner")
        print("  2: Mark bottom-right corner")
        print("  S: Save current area")
        print("  Q: Quit and save all areas")
        print("  I: Display current bounds")
        print("\nGame Controls:")
        print("Arrow keys: Movement")
        print("Z: A button")
        print("X: B button")
        print("Enter: Start")
        print("Right Shift: Select")
        print("A: L button")
        print("S: R button")
        print("F: Toggle fast-forward")
        print("P: Save state")
        print("L: Load last save state")
        print("ESC: Exit")
        
        last_coords = None
        fast_forward = False
        running = True
        last_save_state = None
        
        try:
            while running:
                # Handle pygame events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                        elif event.key == pygame.K_f:
                            fast_forward = not fast_forward
                            self.env.frameskip = 64 if fast_forward else 0
                            print("Fast-forward:", "ON" if fast_forward else "OFF")
                        elif event.key == pygame.K_p:  # Save state
                            save_file = create_save_state(self.env, ROM_PATH)
                            if save_file:
                                print(f"Save state created: {save_file}")
                                last_save_state = save_file
                            else:
                                print("Failed to create save state")
                        elif event.key == pygame.K_l:  # Load state
                            if last_save_state and last_save_state.exists():
                                if load_save_state(self.env, last_save_state):
                                    print(f"Loaded save state: {last_save_state}")
                                else:
                                    print("Failed to load save state")
                            else:
                                print("No save state available to load")
                        elif event.key == pygame.K_i:  # Display bounds
                            self.display_bounds()
                            time.sleep(0.2)  # Debounce
                        elif event.key == pygame.K_n:
                            name = input("\nEnter area name: ")
                            self.start_new_area(name)
                            time.sleep(0.2)  # Debounce
                        elif event.key == pygame.K_1:
                            self.mark_corner("top_left")
                            time.sleep(0.2)  # Debounce
                        elif event.key == pygame.K_2:
                            self.mark_corner("bottom_right")
                            time.sleep(0.2)  # Debounce
                        elif event.key == pygame.K_s:
                            self.save_current_area()
                            time.sleep(0.2)  # Debounce
                        elif event.key == pygame.K_q:
                            running = False
                
                # Handle game controls
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
                elif keys[pygame.K_s] and not keys[pygame.K_LCTRL] and not keys[pygame.K_RCTRL]:  # Avoid conflict with save shortcut
                    button = "R"
                
                # Update GBA
                action = self.env.get_action_id(direction, button)
                observation, reward, done, truncated, info = self.env.step(action)
                self.env.render()
                
                # Show coordinates when they change
                x, y = read_player_xy(self.gba)
                if (x, y) != last_coords:
                    print(f"\rCurrent position: ({x}, {y})   ", end="", flush=True)
                    area_name = get_area_description(self.gba)
                    print(f" | Area: {area_name}   ", end="", flush=True)
                    last_coords = (x, y)
                
        except KeyboardInterrupt:
            print("\nStopping mapping...")
        finally:
            self.save_areas()
            self.env.close()
            pygame.quit()
            print("\nMapping complete!")

if __name__ == "__main__":
    pygame.init()
    if not Path(ROM_PATH).exists():
        print(f"ROM file not found: {ROM_PATH}")
        sys.exit(1)
        
    mapper = AreaMapper()
    mapper.run() 