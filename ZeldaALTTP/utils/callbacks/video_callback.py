from ZeldaALTTP.utils.callbacks.episode_callback_base import EpisodeAwareCallback
import mediapy as media
from pathlib import Path
import numpy as np

class VideoRecordingCallback(EpisodeAwareCallback):
    def __init__(self, save_dir, record_freq=1, max_videos=10, verbose=0):
        super().__init__(verbose)
        self.save_dir = Path(save_dir)
        self.record_freq = record_freq
        self.max_videos = max_videos
        self.writer = None         # List per env
        self.frame_shape = None
        self.fps = 60
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def _on_training_start(self):
        super()._on_training_start()
        self.writer = [None for _ in range(self.num_envs)]
        self.frame_shape = [None for _ in range(self.num_envs)]

    def _on_step(self) -> bool:
        dones = self.locals.get('dones')
        truncateds = self.locals.get('truncateds')
        frames = self.training_env.env_method("render", mode="rgb_array")
        for i in range(self.num_envs):
            # Start new video if needed
            if (self.episode_count[i] < self.max_videos and
                self.episode_count[i] % self.record_freq == 0 and
                self.writer[i] is None):
                video_path = self.save_dir / f"env_{i}_episode_{self.episode_count[i]}.mp4"
                frame = frames[i]
                self.frame_shape[i] = frame.shape[:2]
                self.writer[i] = media.VideoWriter(str(video_path), self.frame_shape[i], fps=self.fps)
                self.writer[i].__enter__()
            # Add frame if writer is active
            if self.writer[i] is not None:
                self.writer[i].add_image(frames[i])
            # Check for episode end
            if self.is_episode_end(dones, truncateds, i) and self.writer[i] is not None:
                self.writer[i].close()
                self.writer[i] = None
                self.episode_count[i] += 1
        return True

    def _on_rollout_end(self):
        if self.writer is not None:
            for w in self.writer:
                if w is not None:
                    w.close()
            self.writer = [None for _ in range(self.num_envs)] 