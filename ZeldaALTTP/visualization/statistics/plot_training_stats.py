import pandas as pd
import matplotlib.pyplot as plt
import os
import matplotlib.ticker as mticker
import glob
import sys
from pathlib import Path


# List of model numbers to process
MODEL_NUMBERS = [f'{i}.{j:02d}' for i in range(25, 35) for j in range(6)]
# MODEL_NUMBERS = ['28.01']

# Set to True to save the plot instead of showing it
SAVE_FIG = True  

# Reward scale for normalization
REWARD_SCALE = 1

# Set to True to exclude the revisit_reward column from plots
REMOVE_REVISIT_REWARD = False

# Directory to save figures
MODEL_GRAPHS_DIR = Path(__file__).parent / 'Model Graphs'
MODEL_GRAPHS_DIR.mkdir(exist_ok=True)

# If removing revisit reward, use a subfolder
if REMOVE_REVISIT_REWARD:
    MODEL_GRAPHS_DIR = MODEL_GRAPHS_DIR / 'No Revisit Reward'
    MODEL_GRAPHS_DIR.mkdir(exist_ok=True)
else:
    MODEL_GRAPHS_DIR = MODEL_GRAPHS_DIR / 'Per Model'
    MODEL_GRAPHS_DIR.mkdir(exist_ok=True)

# Base sessions directory (relative to this script)
SESSIONS_BASE = Path(__file__).parent.parent.parent / 'sessions'

for MODEL_NUMBER in MODEL_NUMBERS:
    MODEL_NUMBER_PADDED = MODEL_NUMBER.zfill(6)  # e.g., '020.00'
    MODEL_BASE = MODEL_NUMBER.split('.')[0]
    MODEL_BASE_PADDED = MODEL_BASE.zfill(3)  # e.g., '020'\

    # Find the session directory for the given model number
    model_dir = SESSIONS_BASE / f"model {MODEL_BASE}"
    session_pattern = str(model_dir / f"session_*_{MODEL_NUMBER}")
    session_dirs = glob.glob(session_pattern)

    if not session_dirs:
        print(f"No session directory found for model {MODEL_NUMBER} in {model_dir}")
        continue

    # If multiple, pick the latest (sorted by name, which includes timestamp)
    session_dir = sorted(session_dirs)[-1]
    csv_path = os.path.join(session_dir, "episode_stats.csv")

    if not os.path.exists(csv_path):
        print(f"CSV file not found: {csv_path}")
        continue

    # Load the CSV data
    df = pd.read_csv(csv_path)

    # Rename 'total_reward_components' to 'total_reward' if present
    if 'total_reward_components' in df.columns:
        df = df.rename(columns={'total_reward_components': 'total_reward'})

    # Columns to average (exclude env_idx and episode)
    avg_cols = [col for col in df.columns if col not in ["env_idx", "episode", "total_reward_steps"]]
    if REMOVE_REVISIT_REWARD and "revisit" in avg_cols:
        avg_cols.remove("revisit")
    # Move 'total_reward' to the end if it exists
    if "total_reward" in avg_cols:
        avg_cols.append(avg_cols.pop(avg_cols.index("total_reward")))
    print(avg_cols)

    # Group by episode and calculate mean for each column
    avg_per_episode = df.groupby("episode")[avg_cols].mean().reset_index()
    print(avg_per_episode)

    # Apply reward scaling
    avg_per_episode[avg_cols] = avg_per_episode[avg_cols] / REWARD_SCALE

    # Plotting
    plt.figure(figsize=(10, 6))
    for col in avg_cols:
        plt.scatter(avg_per_episode["episode"], avg_per_episode[col], label=col, s=20)

    plt.xlabel("Episode")
    plt.ylabel("Average Value")
    plt.title(f"Average Stats per Episode (Model {MODEL_NUMBER})")
    plt.legend(loc="upper left")
    plt.grid(True, alpha=0.3)
    plt.gca().xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    plt.tight_layout()

    # Save or show the plot
    if SAVE_FIG:
        model_major, model_minor = MODEL_NUMBER.split('.')
        MODEL_NUMBER_FILENAME = f"{int(model_major):03d}_{int(model_minor):02d}"
        save_path = MODEL_GRAPHS_DIR / f"Model_{MODEL_NUMBER_FILENAME}.png"
        plt.savefig(save_path)
        print(f"Plot saved to {save_path}")
    else:
        plt.show()
    plt.close()
