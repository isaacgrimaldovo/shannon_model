"""Loop de entrenamiento básico."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from tqdm import tqdm

from shannon_model.config import load_config, resolve_device, set_seed
from shannon_model.model import ShannonBaseline


def build_synthetic_loaders(
    batch_size: int,
    input_size: int = 64,
    num_classes: int = 2,
    n_train: int = 512,
    n_val: int = 128,
) -> tuple[DataLoader, DataLoader]:
    """Datos sintéticos para validar el pipeline antes del dataset real."""
    x_train = torch.randn(n_train, input_size)
    y_train = torch.randint(0, num_classes, (n_train,))
    x_val = torch.randn(n_val, input_size)
    y_val = torch.randint(0, num_classes, (n_val,))

    train_loader = DataLoader(
        TensorDataset(x_train, y_train), batch_size=batch_size, shuffle=True
    )
    val_loader = DataLoader(
        TensorDataset(x_val, y_val), batch_size=batch_size, shuffle=False
    )
    return train_loader, val_loader


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> float:
    model.train()
    total_loss = 0.0
    n = 0
    for xb, yb in loader:
        xb, yb = xb.to(device), yb.to(device)
        optimizer.zero_grad()
        logits = model(xb)
        loss = criterion(logits, yb)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * xb.size(0)
        n += xb.size(0)
    return total_loss / max(n, 1)


@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> tuple[float, float]:
    model.eval()
    total_loss = 0.0
    correct = 0
    n = 0
    for xb, yb in loader:
        xb, yb = xb.to(device), yb.to(device)
        logits = model(xb)
        loss = criterion(logits, yb)
        total_loss += loss.item() * xb.size(0)
        pred = logits.argmax(dim=1)
        correct += (pred == yb).sum().item()
        n += xb.size(0)
    return total_loss / max(n, 1), correct / max(n, 1)


def run_training(config_path: str | Path = "configs/default.yaml") -> dict[str, Any]:
    cfg = load_config(config_path)
    set_seed(int(cfg["seed"]))
    device = resolve_device(cfg.get("device", "auto"))

    train_cfg = cfg["train"]
    model_cfg = cfg["model"]
    checkpoint_dir = Path(train_cfg["checkpoint_dir"])
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    input_size = 64
    num_classes = 2
    train_loader, val_loader = build_synthetic_loaders(
        batch_size=int(train_cfg["batch_size"]),
        input_size=input_size,
        num_classes=num_classes,
    )

    model = ShannonBaseline(
        input_size=input_size,
        hidden_size=int(model_cfg["hidden_size"]),
        num_classes=num_classes,
        dropout=float(model_cfg["dropout"]),
    ).to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(train_cfg["learning_rate"]),
        weight_decay=float(train_cfg["weight_decay"]),
    )

    history: dict[str, list[float]] = {
        "train_loss": [],
        "val_loss": [],
        "val_acc": [],
    }
    best_val_loss = float("inf")

    epochs = int(train_cfg["epochs"])
    for epoch in tqdm(range(1, epochs + 1), desc="epochs"):
        train_loss = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc = evaluate(model, val_loader, criterion, device)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)

        print(
            f"epoch={epoch} train_loss={train_loss:.4f} "
            f"val_loss={val_loss:.4f} val_acc={val_acc:.4f}"
        )

        if train_cfg.get("save_every_epoch", True):
            torch.save(
                {
                    "epoch": epoch,
                    "model_state": model.state_dict(),
                    "optimizer_state": optimizer.state_dict(),
                    "val_loss": val_loss,
                    "config": cfg,
                },
                checkpoint_dir / f"epoch_{epoch:03d}.pt",
            )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(
                {
                    "epoch": epoch,
                    "model_state": model.state_dict(),
                    "optimizer_state": optimizer.state_dict(),
                    "val_loss": val_loss,
                    "config": cfg,
                },
                checkpoint_dir / "best.pt",
            )

    return {"history": history, "best_val_loss": best_val_loss, "device": str(device)}


if __name__ == "__main__":
    result = run_training()
    print(result)
