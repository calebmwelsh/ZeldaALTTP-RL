import os
from pathlib import Path
from datetime import datetime
import uuid
import json
import shutil

def get_latest_model_dir(base_sessions_dir):
    model_dirs = [d for d in base_sessions_dir.iterdir() if d.is_dir() and d.name.startswith('model ')]
    if not model_dirs:
        return None
    # Sort by model number
    model_dirs.sort(key=lambda d: int(d.name.split(' ')[1]), reverse=True)
    return model_dirs[0]

def get_latest_session_dir(model_dir):
    session_dirs = [d for d in model_dir.iterdir() if d.is_dir() and d.name.startswith('session_')]
    if not session_dirs:
        return None
    # Sort by session number (last _#.0#)
    def session_sort_key(d):
        try:
            return float(d.name.split('_')[-1])
        except Exception:
            return 0
    session_dirs.sort(key=session_sort_key, reverse=True)
    return session_dirs[0]

def get_latest_model_file(models_dir):
    final_model = models_dir / 'final_model.zip'
    if final_model.exists():
        return final_model
    # Otherwise, find latest zelda_model_*.zip
    candidates = list(models_dir.glob('zelda_model_*.zip'))
    if not candidates:
        return None
    candidates.sort(key=os.path.getctime, reverse=True)
    return candidates[0]

def get_latest_session_and_model(base_sessions_dir):
    model_dir = get_latest_model_dir(base_sessions_dir)
    if not model_dir:
        raise FileNotFoundError('No model directories found.')
    session_dir = get_latest_session_dir(model_dir)
    if not session_dir:
        raise FileNotFoundError('No session directories found in latest model dir.')
    models_dir = session_dir / 'models'
    model_path = get_latest_model_file(models_dir)
    return {
        'session_dir': session_dir,
        'model_path': model_path
    }

def get_next_model_number(base_sessions_dir):
    model_dirs = [d for d in base_sessions_dir.iterdir() if d.is_dir() and d.name.startswith('model ')]
    if not model_dirs:
        return 1
    model_dirs.sort(key=lambda d: int(d.name.split(' ')[1]), reverse=True)
    return int(model_dirs[0].name.split(' ')[1]) + 1

def get_next_session_number(model_dir):
    # Extract model number from directory name (e.g., 'model 8' -> 8)
    try:
        model_number = int(model_dir.name.split(' ')[1])
    except Exception:
        model_number = 1
    session_dirs = [d for d in model_dir.iterdir() if d.is_dir() and d.name.startswith('session_')]
    if not session_dirs:
        return float(f"{model_number}.00")
    # Find max float at end
    max_num = float(f"{model_number}.00")
    for d in session_dirs:
        try:
            num = float(d.name.split('_')[-1])
            if num > max_num:
                max_num = num
        except Exception:
            continue
    return round(max_num + 0.01, 2)

def prepare_new_session_from_latest_model(base_sessions_dir, model_config, general_config, device, override_model=None):
    save_video = general_config["save_video"]
    episode_length = model_config["episode_length"]
    episode_count = model_config["episode_count"]
    num_envs = model_config["num_envs"]
    frameskip = model_config["action_freq"]
    checkpointing = model_config["checkpointing"]
    headless = model_config["headless"]

    if override_model is not None:
        # Use the override model number to get the latest model file
        model_path = get_latest_model_file_from_model_number(base_sessions_dir, override_model)
        # Use the model dir for session creation
        model_dir = base_sessions_dir / f"model {int(override_model)}"
        if not model_dir.exists() or not model_dir.is_dir():
            raise FileNotFoundError(f"Model directory for model {override_model} not found.")
    else:
        model_dir = get_latest_model_dir(base_sessions_dir)
        if not model_dir:
            raise FileNotFoundError('No model directories found.')
        latest_session_dir = get_latest_session_dir(model_dir)
        if not latest_session_dir:
            raise FileNotFoundError('No session directories found in latest model dir.')
        models_dir = latest_session_dir / 'models'
        model_path = get_latest_model_file(models_dir)
    # Create a new session directory in the same model dir
    session_num = get_next_session_number(model_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = str(uuid.uuid4())[:8]
    session_dir = model_dir / f"session_{timestamp}_{uid}_{session_num:.2f}"
    session_dir.mkdir(parents=True, exist_ok=True)
    # Subdirs
    models_dir_new = session_dir / "models"
    models_dir_new.mkdir(exist_ok=True)
    script_dir = session_dir / "scripts"
    script_dir.mkdir(exist_ok=True)
    # Only create videos dir if save_video and headless (rgb_array)
    video_dir = None
    if save_video and headless:
        video_dir = session_dir / "videos"
        video_dir.mkdir(exist_ok=True)
    # Save metadata
    total_timesteps = episode_length * episode_count * num_envs
    simulated_time = calculate_simulated_game_time(total_timesteps, frameskip)
    metadata = {
        "session_id": session_dir.name,
        "timestamp": datetime.now().isoformat(),
        "simulated_game_time": simulated_time,
        "config": {
            "frameskip": frameskip,
            "episode_length": episode_length,
            "episode_count": episode_count,
            "checkpointing": checkpointing,
            "headless": headless,
            "num_envs": num_envs,
            "device_type": device
        }
    }
    with open(session_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)

    # Copy relevant scripts for reproducibility
    shutil.copy2(Path(__file__).parent.parent.parent / "pygba-main/src/pygba/game_wrappers/zelda_alttp.py", script_dir / "zelda_alttp.py")
    shutil.copy2(Path(__file__).parent.parent.parent / "pygba-main/src/pygba/game_wrappers/utils/area_mapping.py", script_dir / "area_mapping.py")
    shutil.copy2(Path(__file__).parent.parent.parent / "pygba-main/src/pygba/game_wrappers/utils/zelda_utils.py", script_dir / "zelda_utils.py")
    shutil.copy2(Path(__file__).parent.parent / "train_agents.py", script_dir / "train_agents.py")
    shutil.copy2(Path(__file__).parent.parent / "config.toml", script_dir / "config.toml")
    shutil.copy2(Path(__file__).parent.parent / "utils/callbacks/movement_callback.py", script_dir / "movement_callback.py")
    shutil.copy2(Path(__file__).parent.parent / "utils/callbacks/statistic_callback.py", script_dir / "statistic_callback.py")
    
    return {
        'session_dir': session_dir,
        'model_path': model_path,
        'override_model': override_model
    }

def create_new_model_and_session(base_sessions_dir, model_config, general_config, device):
    save_video = general_config["save_video"]
    episode_length = model_config["episode_length"]
    episode_count = model_config["episode_count"]
    num_envs = model_config["num_envs"]
    frameskip = model_config["action_freq"]
    checkpointing = model_config["checkpointing"]
    headless = model_config["headless"]

    # Create new model dir if none exists, else increment
    model_num = get_next_model_number(base_sessions_dir)
    model_dir = base_sessions_dir / f"model {model_num}"
    model_dir.mkdir(parents=True, exist_ok=True)
    # Create new session dir with incremented session number
    session_num = get_next_session_number(model_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = str(uuid.uuid4())[:8]
    session_dir = model_dir / f"session_{timestamp}_{uid}_{session_num:.2f}"
    session_dir.mkdir(parents=True, exist_ok=True)
    # Subdirs
    models_dir = session_dir / "models"
    models_dir.mkdir(exist_ok=True)
    script_dir = session_dir / "scripts"
    script_dir.mkdir(exist_ok=True)
    # Only create videos dir if save_video and headless (rgb_array)
    video_dir = None
    if save_video and headless:
        video_dir = session_dir / "videos"
        video_dir.mkdir(exist_ok=True)
    # Save metadata
    total_timesteps = episode_length * episode_count * num_envs
    simulated_time = calculate_simulated_game_time(total_timesteps, frameskip)
    metadata = {
        "session_id": session_dir.name,
        "timestamp": datetime.now().isoformat(),
        "simulated_game_time": simulated_time,
        "config": {
            "frameskip": frameskip,
            "episode_length": episode_length,
            "episode_count": episode_count,
            "checkpointing": checkpointing,
            "headless": headless,
            "num_envs": num_envs,
            "device_type": device
        }
    }
    with open(session_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)
    
    # Copy relevant scripts for reproducibility
    shutil.copy2(Path(__file__).parent.parent.parent / "pygba-main/src/pygba/game_wrappers/zelda_alttp.py", script_dir / "zelda_alttp.py")
    shutil.copy2(Path(__file__).parent.parent.parent / "pygba-main/src/pygba/game_wrappers/utils/area_mapping.py", script_dir / "area_mapping.py")
    shutil.copy2(Path(__file__).parent.parent.parent / "pygba-main/src/pygba/game_wrappers/utils/zelda_utils.py", script_dir / "zelda_utils.py")
    shutil.copy2(Path(__file__).parent.parent / "train_agents.py", script_dir / "train_agents.py")
    shutil.copy2(Path(__file__).parent.parent / "config.toml", script_dir / "config.toml")
    shutil.copy2(Path(__file__).parent.parent / "utils/callbacks/movement_callback.py", script_dir / "movement_callback.py")
    shutil.copy2(Path(__file__).parent.parent / "utils/callbacks/statistic_callback.py", script_dir / "statistic_callback.py")

    return {
        'session_dir': session_dir
    }

def calculate_simulated_game_time(total_timesteps, frameskip, frame_rate=60):
    total_frames = total_timesteps * frameskip
    seconds = total_frames / frame_rate
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return {
        "seconds": seconds,
        "formatted": f"{hours}h {minutes}m {secs}s"
    }

def get_latest_model_file_from_model_number(base_sessions_dir, model_number):
    """
    Given a base sessions directory and a model number (int or str),
    returns the latest model file (final_model.zip or latest checkpoint) in that model folder.
    Returns None if not found.
    """
    model_dir = base_sessions_dir / f"model {int(model_number)}"
    if not model_dir.exists() or not model_dir.is_dir():
        return None
    # Find the latest session in this model dir
    session_dir = get_latest_session_dir(model_dir)
    if not session_dir:
        return None
    models_dir = session_dir / "models"
    return get_latest_model_file(models_dir) 