from ZeldaALTTP.utils.callbacks.episode_callback_base import EpisodeAwareCallback
import numpy as np
import os
import csv

class StatisticLoggingCallback(EpisodeAwareCallback):
    """Callback for logging training statistics including rewards and exploration metrics every N steps during training."""
    def __init__(self, session_dir, log_freq=4000, verbose=0):
        super().__init__(verbose)
        self.session_dir = session_dir
        self.log_freq = log_freq
        self.rewards = []
        self.last_log_step = 0
        self.episode_rewards = []  # Track rewards for each episode per env
        self.episode_reward_components = []  # Track per-episode reward components

    def _on_training_start(self) -> None:
        super()._on_training_start()
        self.episode_rewards = [[] for _ in range(self.num_envs)]  # Initialize per-episode rewards
        self.episode_reward_components = [{} for _ in range(self.num_envs)]  # Track per-episode reward components
        self.log_file = None
        if hasattr(self, 'session_dir') and self.session_dir is not None:
            log_path = os.path.join(self.session_dir, 'episode_stats.csv')
            self.log_file = log_path
            if not os.path.exists(log_path):
                with open(log_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        'env_idx', 'episode', 'total_reward_steps', 'total_reward_components',
                        'rupees', 'health', 'explore', 'death', 'area_discovery', 'sword', 'revisit', 'enemies_killed', 'small_keys'
                    ])

    def _on_step(self) -> bool:
        rewards = self.locals.get('rewards')
        if rewards is not None:
            if isinstance(rewards, (list, np.ndarray)):
                self.rewards.extend(rewards)
                for idx, r in enumerate(rewards):
                    self.episode_rewards[idx].append(r)
                    infos = self.locals.get('infos')
                    if infos is not None and isinstance(infos, (list, tuple, np.ndarray)):
                        info = infos[idx]
                        reward_components = info.get('reward_components', None)
                        if reward_components is not None:
                            for k, v in reward_components.items():
                                if k not in self.episode_reward_components[idx]:
                                    self.episode_reward_components[idx][k] = 0.0
                                self.episode_reward_components[idx][k] += v
            else:
                self.rewards.append(rewards)
                self.episode_rewards[0].append(rewards)
                infos = self.locals.get('infos')
                if infos is not None and isinstance(infos, (list, tuple, np.ndarray)):
                    info = infos[0]
                    reward_components = info.get('reward_components', None)
                    if reward_components is not None:
                        for k, v in reward_components.items():
                            if k not in self.episode_reward_components[0]:
                                self.episode_reward_components[0][k] = 0.0
                            self.episode_reward_components[0][k] += v

        dones = self.locals.get('dones')
        truncateds = self.locals.get('truncateds')
        infos = self.locals.get('infos')
        if dones is not None:
            for idx in range(self.num_envs):
                if self.is_episode_end(dones, truncateds, idx):
                    total_steps = sum(self.episode_rewards[idx])
                    total_components = sum(self.episode_reward_components[idx].values())
                    print(f"[Env {idx}] Total reward for episode {self.episode_count[idx]} (steps): {total_steps:.2f}")
                    print(f"[Env {idx}] Total reward for episode {self.episode_count[idx]} (components): {total_components:.2f}")
                    if self.log_file:
                        reward_components = self.episode_reward_components[idx]
                        with open(self.log_file, 'a', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow([
                                idx, self.episode_count[idx], total_steps, total_components,
                                *(reward_components.get(k, 0.0) for k in [
                                    'rupees', 'health', 'explore', 'death', 'area_discovery', 'sword', 'revisit', 'enemies_killed', 'small_keys'
                                ])
                            ])
                        print(f"[Env {idx}] Reward components: {self.episode_reward_components[idx]}")
                    self.episode_rewards[idx] = []
                    self.episode_reward_components[idx] = {}
                    self.episode_count[idx] += 1
                    if infos is not None:
                        info = infos[idx] if isinstance(infos, (list, tuple, np.ndarray)) else infos
                        if info.get("is_dead", False):
                            print(f"[Env {idx}] DIED at step {self.num_timesteps}")

        if self.num_timesteps - self.last_log_step >= self.log_freq:
            if self.rewards:
                avg_reward = np.mean(self.rewards[-self.log_freq:])
                infos = self.locals.get('infos')
                for idx in range(self.num_envs):
                    info = infos[idx] if infos is not None and isinstance(infos, (list, tuple, np.ndarray)) else None
                    if info is not None:
                        explored_locations = info.get('explored_locations', None)
                        area_discovery_timestamps = info.get('area_discovery_timestamps', None)
                        sword_discovery_timestamp = info.get('sword_discovery_timestamp', None)
                        total_enemies_killed = info.get('total_enemies_killed', None)
                        total_small_keys = info.get('total_small_keys', None)
                        total_deaths = info.get('total_deaths', None)
                        print()
                        print(f"[Env {idx}] (episode: {self.episode_count[idx]})")
                        print(f"  ├── Unique locations explored: {explored_locations}")
                        print(f"  ├── Total enemies killed (all episodes): {total_enemies_killed}")
                        print(f"  ├── Total small keys (all episodes): {total_small_keys}")
                        print(f"  ├── Total deaths (all episodes): {total_deaths}")
                        print(f"  ├── Sword discovery time: {sword_discovery_timestamp}")
                        print(f"  └── Unique areas discovered: {area_discovery_timestamps}")
                        print()
                    else:
                        print(f"[Env {idx}] No info found.")
                print(f"[Step {self.num_timesteps}] Average reward (last {self.log_freq} steps): {avg_reward:.4f}")
            self.last_log_step = self.num_timesteps
        return True 