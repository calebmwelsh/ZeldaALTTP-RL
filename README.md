# Zelda RL Test

This project is a reinforcement learning environment and tooling for Zelda: A Link to the Past (GBA) using Python and mGBA Python bindings.

## Prerequisites

Before installing Python dependencies, you **must** install and build several external libraries and Python bindings. Please follow the instructions below **in order**.

### 1. Install mGBA and Python Bindings

#### a. [libmgba-py (Python bindings for mGBA)](https://github.com/hanzi/libmgba-py/tree/master)
- Follow the build instructions in the repo for your OS (Windows or Mac).
- **Windows users:**
  - If you encounter a build error related to `ffmpeg-encoder.c`, you must manually edit `libmgba-py\mgba-src\src\feature\ffmpeg\ffmpeg-encoder.c` and replace its contents with the version provided in this repository at `ffmpeg-encoder.c`.
- After building, copy the resulting `mgba` directory (from the build output) into your Python project or ensure it is importable by Python.

#### b. [pygba (Python wrapper for mGBA)](https://github.com/dvruette/pygba/tree/main)
- Follow the instructions in the repo to build/install. This may require building mGBA from source as well.

#### c. [mGBA Emulator (C library)](https://github.com/mgba-emu/mgba/)
- You may need to build mGBA from source for your platform, especially if required by the above bindings.
- Follow the official instructions for your OS.

**Note:** This project has been tested on **Windows** and **Mac** only.

### 2. Python Dependencies

Once the above libraries and bindings are installed and working, install the Python dependencies:

```bash
pip install -r requirements.txt
```

## ROM Placement

Place your GBA ROM file(s) in the `roms/gba` directory.

## Usage

To train a reinforcement learning agent for Zelda: A Link to the Past, use the `train_agents.py` script located in the `ZeldaALTTP` directory. Training parameters (such as episode length, number of environments, reward weights, etc.) are configured in the `ZeldaALTTP/config.toml` file.

### Basic Training Steps

1. Ensure all prerequisites and Python dependencies are installed (see above).
2. Place your GBA ROM in the correct location (see ROM Placement above).
3. (Optional) Adjust training parameters in `ZeldaALTTP/config.toml` to suit your experiment.
4. Run the training script:

```bash
python ZeldaALTTP/train_agents.py
```

This will start training a PPO agent using Stable Baselines3. Model checkpoints and training logs will be saved in the sessions directory specified in the config file.

This project also provides tools to **visualize agent behavior and analyze training statistics** to better understand and present your model's learning progress:

### Visualizing and Analyzing Training Progress

#### 1. Replay Visualization (`visualization/replay/`)
- **`replay_movements.py`**:  
  Visually replays the movements of your RL agent(s) on the Zelda world map using Pygame. Loads movement data from training sessions and animates the agent's path, allowing you to inspect navigation, decision points, and overall exploration.
  - **Configurable**: Adjust which episodes, environments, and models to visualize via the `config.toml` file.
  - **Usage**:  
    ```bash
    python ZeldaALTTP/visualization/replay/replay_movements.py
    ```
  - **Purpose**: Great for debugging, qualitative analysis, and presentations.

#### 2. Training Statistics & Plotting (`visualization/statistics/`)
- **`plot_training_stats.py`**:  
  Generates per-model plots of training statistics (e.g., rewards, custom metrics) across episodes. Processes CSV logs from training sessions and saves plots to the `Model Graphs/` directory for easy comparison.
  - **Usage**:  
    ```bash
    python ZeldaALTTP/visualization/statistics/plot_training_stats.py
    ```
- **`combined_plot_training_stats.py`**:  
  Combines statistics from multiple sessions or models into a single plot, allowing you to compare performance or track progress over time.
  - **Usage**:  
    ```bash
    python ZeldaALTTP/visualization/statistics/combined_plot_training_stats.py
    ```

**Tip:**
All scripts are configurable and can be adapted to your experiment setup. See comments and config files in each directory for details.

## Additional Notes
- If you encounter issues with the Python bindings or emulator, consult the documentation and issues in the respective repositories linked above.
- For Windows users, the manual edit to `ffmpeg-encoder.c` is required for successful build of the Python bindings.
- The reward calculation and logic for the RL environment are implemented in [`pygba-main/src/pygba/game_wrappers/zelda_alttp.py`](./pygba-main/src/pygba/game_wrappers/zelda_alttp.py).

## Progress & Experimentation

Ongoing progress, reward parameter updates, and experiment notes are documented in detail in the [PROGRESS.md](./PROGRESS.md) file. 

## Contributing

I am passionate about improving this project and will be updating it periodically with new features, fixes, and enhancements. If you are interested in contributing, your help is very welcome! Whether it's code, documentation, or ideas, every contribution counts.

If you have deep experience with reinforcement learning (RL) and have any pointers, suggestions, or best practices to share, please let me know. Your insights could help shape the direction and quality of this project.

If you are interested in more in-depth results or details about the project, I am happy to share them—just ask!

Feel free to open issues, submit pull requests, or reach out with feedback. Let's make this project better together!

## License
This project and its dependencies are subject to their respective licenses. See the linked repositories for details. 

