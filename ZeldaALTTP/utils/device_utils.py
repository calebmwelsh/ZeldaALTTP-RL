import torch
import os
import math

def setup_device(config_section):
    """
    Sets up device and utilization based on config_section (dict-like).
    Returns the device string ('cuda' or 'cpu').
    """
    device_type = config_section.get("device_type", "cuda")
    device_util = float(config_section.get("device_util", 1.0))

    if device_type == "cuda" and torch.cuda.is_available():
        device = "cuda"
        # torch.cuda.set_per_process_memory_fraction(device_util, 0)
        print(f"\nUsing device: {device} (GPU fraction: {device_util*100:.0f}%)")
    elif device_type == "cpu":
        device = "cpu"
        num_threads = max(1, math.ceil(os.cpu_count() * device_util))
        torch.set_num_threads(num_threads)
        print(f"\nUsing device: {device} (CPU threads: {num_threads})")
    else:
        device = "cpu"
        print(f"\nRequested device '{device_type}' not available. Falling back to CPU.")
    return device 