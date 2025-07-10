import pandas as pd
import matplotlib.pyplot as plt
import os
from pathlib import Path
import glob

# --- CONFIGURATION ---
# Set to None to use the manual list, or set to a model number (e.g., 26) to auto-load all CSVs in that model's directory
MODEL_NUMBER = 30

# --- CSV FILES SELECTION ---
if MODEL_NUMBER is None:
    # Manual mode: specify each file
    csv_files = [
        Path(__file__).parent.parent.parent / 'sessions/model 17/session_20250518_182059_f390dc4b_17.00/episode_stats.csv',
        Path(__file__).parent.parent.parent / 'sessions/model 23/session_20250521_163116_63ba0ead_23.00/episode_stats.csv',
        Path(__file__).parent.parent.parent / 'sessions/model 23/session_20250522_005947_f3ba140e_23.01/episode_stats.csv',
        Path(__file__).parent.parent.parent / 'sessions/model 23/session_20250522_142814_34297da3_23.02/episode_stats.csv',
        Path(__file__).parent.parent.parent / 'sessions/model 23/session_20250522_234225_d3d28d8d_23.03/episode_stats.csv',
        Path(__file__).parent.parent.parent / 'sessions/model 23/session_20250527_163439_ddd33c89_23.04/episode_stats.csv',
        Path(__file__).parent.parent.parent / 'sessions/model 23/session_20250527_231026_e90fbd10_23.05/episode_stats.csv',
    ]
else:
    # Auto mode: combine all CSVs in the specified model directory
    model_dir = Path(__file__).parent.parent.parent / f'sessions/model {MODEL_NUMBER}'
    csv_files = sorted(model_dir.glob('session_*/episode_stats.csv'))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {model_dir}")
    

for i in csv_files:
    print(i)

# --- LOAD AND CONCATENATE CSVs WITH CONTINUOUS EPISODE NUMBERING ---
df_list = []
episode_offset = 0
for i, f in enumerate(csv_files):
    df = pd.read_csv(str(f))
    if i > 0:
        # Shift episode numbers so they continue from the previous file
        df['episode'] += episode_offset + 1
    episode_offset = df['episode'].max()
    df_list.append(df)
df = pd.concat(df_list, ignore_index=True)

# Columns to average (exclude env_idx and episode)
avg_cols = [col for col in df.columns if col not in ["env_idx", "episode", "total_reward_steps"]]
# Use 'total_reward_components' instead of 'total_reward' if present
if "total_reward" in avg_cols:
    avg_cols.remove("total_reward")
if "total_reward_components" in df.columns and "total_reward_components" not in avg_cols:
    avg_cols.append("total_reward_components")
# Move 'total_reward_components' to the end if present
if "total_reward_components" in avg_cols:
    avg_cols = [col for col in avg_cols if col != "total_reward_components"] + ["total_reward_components"]

# Group by episode and calculate mean for each column
avg_per_episode = df.groupby("episode")[avg_cols].mean().reset_index()

# Plotting
plt.figure(figsize=(14, 9))
for col in avg_cols:
    plt.scatter(avg_per_episode["episode"], avg_per_episode[col], label=col, s=20)

plt.xlabel("Episode")
plt.ylabel("Average Value")
plt.title(f"Average Stats per Episode (Model {MODEL_NUMBER if MODEL_NUMBER is not None else 'Manual'})")
plt.legend(loc="upper left")
plt.grid(True, alpha=0.3)
plt.tight_layout()

# Save the plot
save_dir = Path(__file__).parent / 'Model Graphs' / 'Combined'
save_dir.mkdir(parents=True, exist_ok=True)
save_name = f"Model_{MODEL_NUMBER if MODEL_NUMBER is not None else 'Manual'}_AllSessions.png"
save_path = save_dir / save_name
plt.savefig(save_path)
print(f"Plot saved to {save_path}")
# plt.show()
plt.close() 