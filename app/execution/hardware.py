from __future__ import annotations

import shutil
import subprocess
from typing import Any

from app.logging_config import get_logger

logger = get_logger("execution.hardware")


def get_gpu_info() -> dict[str, Any]:
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        try:
            res = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if res.returncode == 0 and res.stdout.strip():
                parts = [p.strip() for p in res.stdout.strip().split(",")]
                if len(parts) >= 5:
                    name = parts[0]
                    mem_used = int(parts[1])
                    mem_total = int(parts[2])
                    util = int(parts[3])
                    temp = int(parts[4])
                    return {
                        "available": True,
                        "name": name,
                        "usage": util,
                        "memory_used_mb": mem_used,
                        "memory_total_mb": mem_total,
                        "temperature_c": temp,
                        "detail": f"{name} ({temp}°C, {util}% load, {mem_used}/{mem_total} MB VRAM)",
                    }
        except Exception as e:
            logger.debug("nvidia-smi query failed: %s", e)

    try:
        import torch
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            return {
                "available": True,
                "name": device_name,
                "usage": 0,
                "memory_used_mb": 0,
                "memory_total_mb": 0,
                "temperature_c": 0,
                "detail": f"{device_name} (CUDA available)",
            }
    except Exception:
        pass

    return {
        "available": False,
        "name": "N/A",
        "usage": 0,
        "memory_used_mb": 0,
        "memory_total_mb": 0,
        "temperature_c": 0,
        "detail": "No dedicated GPU detected",
    }
