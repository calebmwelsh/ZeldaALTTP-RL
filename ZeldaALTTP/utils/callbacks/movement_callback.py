import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

from ZeldaALTTP.utils.callbacks.episode_callback_base import EpisodeAwareCallback
import numpy as np
import json
from datetime import datetime

def convert_numpy_types(obj):
    """Convert numpy types to native Python types for JSON serialization
    
    Args:
        obj: Any Python object that might contain numpy types
        
    Returns:
        obj with all numpy types converted to native Python types
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj

class MovementTrackingCallback(EpisodeAwareCallback):
    """Callback for tracking Link's movements during training and evaluation (supports multiple envs)"""
    def __init__(self, session_dir, verbose=0):
        super().__init__(verbose)
        self.session_dir = session_dir
        self.movements = []  # List of lists, one per env
        self.movement_dirs = []  # List of Path objects, one per env
        self.current_area = []  # List, one per env
        self.seen_coords = []  # List of sets, one per env
    
    def _on_training_start(self):
        super()._on_training_start()
        self.movement_dir = self.session_dir / "movements"
        self.movement_dir.mkdir(exist_ok=True)
        self.movements = [[] for _ in range(self.num_envs)]
        self.movement_dirs = []
        self.current_area = [None for _ in range(self.num_envs)]
        self.seen_coords = [set() for _ in range(self.num_envs)]
        for i in range(self.num_envs):
            env_dir = self.movement_dir / f"env_{i}"
            env_dir.mkdir(exist_ok=True)
            self.movement_dirs.append(env_dir)
    
    def _on_step(self):
        actions = self.locals.get('actions', [None]*self.num_envs)
        dones = self.locals.get('dones')
        truncateds = self.locals.get('truncateds')
        infos = self.locals.get('infos')
        if infos is not None and isinstance(infos, (list, tuple, np.ndarray)):
            for i in range(self.num_envs):
                info = infos[i]
                coords = info.get('current_coords')
                if coords is not None:
                    x, y, tile_x, tile_y, area = coords
                    coord_tuple = (tile_x, tile_y)
                    if coord_tuple not in self.seen_coords[i]:
                        self.seen_coords[i].add(coord_tuple)
                        action = actions[i] if isinstance(actions, (list, np.ndarray)) else actions
                        direction = get_direction_from_action(action)
                        movement_data = {
                            'tile_x': tile_x,
                            'tile_y': tile_y,
                            'world_x': x,
                            'world_y': y,
                            'direction': direction,
                            'action': action,
                            'area': area,
                            'timestamp': datetime.now().isoformat()
                        }
                        self.movements[i].append(convert_numpy_types(movement_data))
                        self.current_area[i] = area
                if self.is_episode_end(dones, truncateds, i):
                    self._save_episode_movements(i)
        return True

    def _save_episode_movements(self, env_idx):
        """Save movements for each episode for a given env_idx"""
        if self.movements[env_idx]:
            data = {
                'metadata': {
                    'unique_movements': len(self.movements[env_idx]),
                    'areas_visited': list(set(m['area'] for m in self.movements[env_idx] if m['area'])),
                    'timestamp': datetime.now().isoformat()
                },
                'movements': self.movements[env_idx]
            }
            episode_file = self.movement_dirs[env_idx] / f"episode_{self.episode_count[env_idx]}_movements.json"
            with open(episode_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.movements[env_idx] = []  # Clear movements for next episode
            self.seen_coords[env_idx] = set()  # Reset seen coords for next episode
            self.episode_count[env_idx] += 1

def decode_action(action_idx):
    # Reproduce the action space logic from PyGBAEnv
    arrow_keys = [None, "up", "down", "right", "left"]
    buttons = [None, "A", "B", "L", "R"]
    actions = [(a, b) for a in arrow_keys for b in buttons]
    if hasattr(action_idx, 'item'):
        action_idx = action_idx.item()
    return actions[action_idx]

def get_direction_from_action(action):
    arrow, button = decode_action(action)
    direction_map = {
        "up": "up",
        "right": "right",
        "down": "down",
        "left": "left",
        None: "none"  # No direction
    }
    return direction_map.get(arrow, "none")
