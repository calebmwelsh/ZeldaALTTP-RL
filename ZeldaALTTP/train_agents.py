from ZeldaALTTP.utils.settings import load_config
from ZeldaALTTP.utils.callbacks.movement_callback import MovementTrackingCallback
from ZeldaALTTP.utils.callbacks.statistic_callback import StatisticLoggingCallback
from ZeldaALTTP.utils.callbacks.video_callback import VideoRecordingCallback
from ZeldaALTTP.utils.device_utils import setup_device
from ZeldaALTTP.stream_wrapper import StreamWrapper
from ZeldaALTTP.utils import session_manager

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback, CallbackList
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from pygba.pygba import PyGBA
from pygba.gym_env import PyGBAEnv
from pygba.game_wrappers.zelda_alttp import ZeldaALTTP
import pygame
import mgba.log
from pathlib import Path

mgba.log.silence()

def load_state_to_gba(gba, state_path):
    from mgba._pylib import ffi
    save_data = Path(state_path).read_bytes()
    state = ffi.new("uint8_t[]", save_data)
    gba.core.load_raw_state(state)


class VisualizeCallback(BaseCallback):
    def __init__(self, verbose=0):
        super().__init__(verbose)
        pygame.init()  # Initialize pygame only if visualizing
    
    def _on_step(self):
        self.training_env.env_method("render")
        pygame.event.pump()
        return True

def run_agent():
    print("\nStarting agent mode...")

    # Set device and utilization for PyTorch using utility
    DEVICE = setup_device(model_config)

    # Determine override_model argument
    override_model = int(OVERRIDE_MODEL_PATH) if (OVERRIDE_MODEL_PATH and str(OVERRIDE_MODEL_PATH).isdigit()) else None

    # Use session_manager to get session/model paths
    if USE_PREV_MODEL:
        session_info = session_manager.prepare_new_session_from_latest_model(BASE_SESSIONS_DIR, model_config, general_config, DEVICE, override_model=override_model)
        session_dir = session_info["session_dir"]
        model_path = session_info["model_path"]
        print(f"Continuing from previous model: {model_path}")
    else:
        session_info = session_manager.create_new_model_and_session(BASE_SESSIONS_DIR, model_config, general_config, DEVICE)
        session_dir = session_info["session_dir"]
        model_path = None
        print(f"Created new model/session: {session_dir}")
    print(f"\nSession Information:")
    print(f"├── Directory: {session_dir}")
    print(f"└── Checkpointing: {'Enabled' if CHECKPOINTING else 'Disabled'}")
    print(f"Observation space: {env.observation_space}")
    
    # Setup callbacks
    callbacks = []
    
    # Add checkpoint callback if enabled in config
    if CHECKPOINTING:
        # Calculate total timesteps
        total_timesteps = EPISODE_LENGTH * EPISODE_COUNT 
        save_freq = total_timesteps // CHECKPOINT_SAVE_FREQ
        
        checkpoint_callback = CheckpointCallback(
            save_freq=save_freq,
            save_path=session_dir / "models",
            name_prefix="zelda_model"
        )
        callbacks.append(checkpoint_callback)
        print(f"Checkpointing enabled - saving {CHECKPOINT_SAVE_FREQ} checkpoints during training (every {save_freq * NUM_ENVS} steps)")
    
    # Add VisualizeCallback only if rendering mode is human
    if RENDER_MODE == "human":
        callbacks.extend([VisualizeCallback()])

    # Add video recording callback if enabled
    if SAVE_VIDEO and RENDER_MODE == "rgb_array":
        video_callback = VideoRecordingCallback(session_dir / "videos", record_freq=1, max_videos=10)
        callbacks.append(video_callback)
    
    # Add movement tracking callback
    movement_callback = MovementTrackingCallback(session_dir)
    callbacks.append(movement_callback)
    
    # Add statistics logging callback
    statistical_callback = StatisticLoggingCallback(session_dir)
    callbacks.append(statistical_callback)

    
    
    # Create callback list
    callback_list = CallbackList(callbacks)
    
    
    # Create or load model
    if (USE_PREV_MODEL or (OVERRIDE_MODEL_PATH and Path(OVERRIDE_MODEL_PATH).exists())) and model_path:
        print(f"Loading model from: {model_path}")
        model = PPO.load(
            model_path,
            env=env,
            device=DEVICE
        )
        model.n_steps = UPDATE_FREQ
        model.n_envs = NUM_ENVS
        model.rollout_buffer.buffer_size = UPDATE_FREQ
        model.rollout_buffer.n_envs = NUM_ENVS
        model.rollout_buffer.reset()
    else:
        print("\nCreating PPO model...")
        policy_kwargs = dict(
            net_arch=[dict(pi=[64, 64], vf=[64, 64])],
            ortho_init=False,  
            optimizer_kwargs=dict(weight_decay=1e-4) 
        )

        model = PPO(
            "CnnPolicy",
            env,
            verbose=1,
            n_steps=UPDATE_FREQ,
            batch_size=BATCH_SIZE,
            n_epochs=1,
            gamma=0.997,
            ent_coef=ENT_COEF,
            device=DEVICE,
            # policy_kwargs=policy_kwargs
        )
    
    # print("\nModel Policy:")
    # print(model.policy)
    print(f"Model device: {next(model.policy.parameters()).device}")
    
    TOTAL_TIMESTEPS = EPISODE_LENGTH * EPISODE_COUNT * NUM_ENVS
    print(f"\nStarting training for {EPISODE_COUNT} episodes per environment (total {TOTAL_TIMESTEPS} timesteps across {NUM_ENVS} environments)...")
    
    try:
        model.learn(
            total_timesteps=TOTAL_TIMESTEPS,
            callback=callback_list,
        )
        
        # Save final model if checkpointing is enabled
        if CHECKPOINTING:
            final_model_path = session_dir / "models" / "final_model.zip"
            model.save(final_model_path)
            print(f"\nFinal model saved to: {final_model_path}")
        
    except KeyboardInterrupt:
        print("\nTraining interrupted!")
        if CHECKPOINTING:
            print("Saving checkpoint...")
            interrupt_path = session_dir / "models" / "interrupted_model.zip"
            model.save(interrupt_path)
            print(f"Interrupted model saved to: {interrupt_path}")
        raise
    
def make_env(rank):
    def _init():
        gba = PyGBA.load(ROM_PATH)
        load_state_to_gba(gba, STATE_PATH)
        zelda_wrapper = ZeldaALTTP()
        env = PyGBAEnv(
            gba,
            game_wrapper=zelda_wrapper,
            frameskip=FRAMESKIP,
            render_mode=RENDER_MODE,
            max_episode_steps=EPISODE_LENGTH,
            reset_to_initial_state=True
        )
        env.rank = rank  # Attach rank to environment
        # Conditionally wrap with streaming wrapper
        if ENABLE_STREAM_WRAPPER:
            env = StreamWrapper(env, ws_address="ws://localhost:8765", stream_metadata={"env_rank": rank})
        return env
    return _init

if __name__ == "__main__":
    print("\nStarting training...")
    config = load_config()
    print()
    # ====== GLOBAL CONFIG AND VARS ======
    paths_config = config["Paths"]
    model_config = config["TrainModel"]
    general_config = config["General"]
    # path variables
    ROM_PATH = paths_config["gb_path"]
    STATE_PATH = paths_config["init_state"]  
    SESSION_PATH = paths_config["session_path"]    
    # model variables
    FRAMESKIP = model_config["action_freq"]
    EPISODE_LENGTH = model_config["episode_length"]
    RENDER_MODE = "rgb_array" if model_config["headless"] else "human"
    EPISODE_COUNT = model_config["episode_count"]
    BATCH_SIZE = model_config["batch_size"]
    ENT_COEF = model_config["ent_coef"]
    NUM_ENVS = model_config["num_envs"]
    CHECKPOINTING = model_config["checkpointing"]
    CHECKPOINT_SAVE_FREQ = model_config["checkpoint_save_freq"]
    UPDATE_FREQ = model_config["update_freq"]
    USE_PREV_MODEL = model_config["use_prev_model"]
    # general variables
    ENABLE_STREAM_WRAPPER = general_config["enable_stream_wrapper"]
    SAVE_VIDEO = general_config["save_video"]
    OVERRIDE_MODEL_PATH = paths_config["override_model_path"]
    # Create base sessions directory
    BASE_SESSIONS_DIR = Path(SESSION_PATH)
    BASE_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    env = SubprocVecEnv([
        make_env(i) for i in range(NUM_ENVS)
    ])
    run_agent()
