from .gym_env import PyGBAEnv
from .pygba import PyGBA
from .game_wrappers.base import GameWrapper
from .game_wrappers.zelda_alttp import ZeldaALTTP
from gymnasium.envs.registration import register

__all__ = [
    "PyGBAEnv",
    "PyGBA",
    "GameWrapper",
]

register(id="PyGBA-v0", entry_point="pygba:PyGBAEnv")
