from stable_baselines3.common.callbacks import BaseCallback
import numpy as np

class EpisodeAwareCallback(BaseCallback):
    """
    Base class for RL callbacks that need per-environment episode tracking and episode boundary detection.
    - Initializes per-env episode counters in _on_training_start.
    - Provides is_episode_end() static method for episode boundary detection.
    Inherit from this class in callbacks that need to track episode state per environment.
    """
    def _on_training_start(self):
        self.num_envs = self.training_env.num_envs
        self.episode_count = [0 for _ in range(self.num_envs)]

    @staticmethod
    def is_episode_end(dones, truncateds, idx):
        done = dones[idx] if isinstance(dones, (list, np.ndarray)) else dones
        truncated = (
            truncateds[idx] if (truncateds is not None and isinstance(truncateds, (list, np.ndarray)))
            else (truncateds if truncateds is not None else False)
        )
        return done or truncated 