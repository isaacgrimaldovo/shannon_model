#!/usr/bin/env python3
"""Entrypoint local/Colab: python scripts/train.py --config configs/default.yaml"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shannon_model.train import run_training  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Entrenar shannon_model")
    parser.add_argument(
        "--config",
        default="configs/default.yaml",
        help="Ruta al YAML de configuración",
    )
    args = parser.parse_args()
    result = run_training(args.config)
    print("Entrenamiento terminado:", result)


if __name__ == "__main__":
    main()
