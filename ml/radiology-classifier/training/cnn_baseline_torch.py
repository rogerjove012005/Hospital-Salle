"""
Prototipo CNN 2D en PyTorch para radiografías de tórax (triple clase).
Complementa el baseline sklearn (PCA+MLP) sin sustituirlo en la API Docker por defecto.
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import List, Tuple

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from configs.config import Config, resolve_radiology_dataset_dir


def _collect_samples(root: Path, class_names: List[str]) -> List[Tuple[Path, int]]:
    samples: List[Tuple[Path, int]] = []
    ok = {".png", ".jpg", ".jpeg"}
    for idx, name in enumerate(class_names):
        d = root / name
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if p.is_file() and p.suffix.lower() in ok:
                samples.append((p, idx))
    return samples


class CXRDataset(Dataset):
    """Imagen en escala de gris → tensor 1×224×224 (un canal; la CNN usa entrada 1 canal)."""

    def __init__(self, items: List[Tuple[Path, int]], img_size: int = 224):
        self.items = items
        self.img_size = img_size

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, i: int):
        path, y = self.items[i]
        img = Image.open(path).convert("L").resize((self.img_size, self.img_size))
        x = np.asarray(img, dtype=np.float32) / 255.0
        t = torch.from_numpy(x).unsqueeze(0)  # (1, H, W)
        return t, torch.tensor(y, dtype=torch.long)


class SmallCXRNet(nn.Module):
    """CNN pequeña: tres bloques conv + cabeza densa (suficiente como prototipo docente)."""

    def __init__(self, num_classes: int = 3):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((4, 4)),
        )
        self.head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 4 * 4, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.35),
            nn.Linear(256, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = self.features(x)
        return self.head(z)


def _device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def run_training(
    *,
    epochs: int = 12,
    batch_size: int = 24,
    lr: float = 1e-3,
    max_per_class: int | None = 800,
    seed: int = 42,
    output_dir: Path | None = None,
) -> dict:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    root = resolve_radiology_dataset_dir()
    class_names = list(Config.CLASSES)
    all_items = _collect_samples(Path(root), class_names)
    if len(all_items) < 30:
        raise RuntimeError(f"Muy pocas imágenes en {root}; ejecute sync o generate_synthetic.")

    if max_per_class:
        by_c: dict[int, list] = {i: [] for i in range(len(class_names))}
        for p, y in all_items:
            by_c[y].append((p, y))
        trimmed: List[Tuple[Path, int]] = []
        for y, lst in by_c.items():
            rng = random.Random(seed + y)
            rng.shuffle(lst)
            trimmed.extend(lst[:max_per_class])
        all_items = trimmed

    paths_y = np.array([y for _, y in all_items])
    idx = np.arange(len(all_items))
    tr_idx, va_idx = train_test_split(
        idx, test_size=0.15, random_state=seed, stratify=paths_y
    )
    train_items = [all_items[i] for i in tr_idx]
    val_items = [all_items[i] for i in va_idx]

    out = output_dir or Path(Config.MODELS_DIR)
    out.mkdir(parents=True, exist_ok=True)

    device = _device()
    model = SmallCXRNet(num_classes=len(class_names)).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    crit = nn.CrossEntropyLoss()

    train_loader = DataLoader(
        CXRDataset(train_items), batch_size=batch_size, shuffle=True, num_workers=0
    )
    val_loader = DataLoader(CXRDataset(val_items), batch_size=batch_size, shuffle=False, num_workers=0)

    history = {"train_loss": [], "val_acc": []}
    for ep in range(epochs):
        model.train()
        losses = []
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            logits = model(xb)
            loss = crit(logits, yb)
            loss.backward()
            opt.step()
            losses.append(loss.item())
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb = xb.to(device)
                logits = model(xb)
                pred = logits.argmax(dim=1).cpu()
                correct += (pred == yb).sum().item()
                total += yb.size(0)
        va = correct / max(total, 1)
        history["train_loss"].append(float(np.mean(losses)))
        history["val_acc"].append(float(va))
        print(f"  época {ep+1}/{epochs}  loss={history['train_loss'][-1]:.4f}  val_acc={va:.4f}")

    # Evaluación en validación (matriz)
    model.eval()
    y_true, y_pred = [], []
    with torch.no_grad():
        for xb, yb in val_loader:
            xb = xb.to(device)
            pred = model(xb).argmax(dim=1).cpu().numpy()
            y_pred.extend(pred.tolist())
            y_true.extend(yb.numpy().tolist())

    acc = float(accuracy_score(y_true, y_pred))
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(class_names))))
    report = classification_report(
        y_true, y_pred, target_names=class_names, output_dict=True, zero_division=0
    )

    ckpt = out / "cnn_baseline.pt"
    torch.save(
        {
            "state_dict": model.state_dict(),
            "class_names": class_names,
            "img_size": Config.IMG_SIZE,
            "model": "SmallCXRNet",
        },
        ckpt,
    )

    metrics = {
        "backend": "pytorch_cnn",
        "dataset_root": str(root),
        "epochs": epochs,
        "val_accuracy": acc,
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
        "class_names": class_names,
        "history": history,
        "device": str(device),
    }
    with (out / "cnn_evaluation.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    # Matriz con matplotlib (sin seaborn)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
    ax.figure.colorbar(im, ax=ax)
    tick = np.arange(len(class_names))
    ax.set(xticks=tick, yticks=tick, xticklabels=class_names, yticklabels=class_names, ylabel="Real", xlabel="Predicho", title="CNN — matriz de confusión (validación)")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], "d"), ha="center", va="center", color="white" if cm[i, j] > thresh else "black")
    fig.tight_layout()
    fig.savefig(out / "cnn_confusion_matrix.png", dpi=110)
    plt.close(fig)

    print(f"\n✓ CNN: pesos en {ckpt}, métricas en {out / 'cnn_evaluation.json'}")
    return metrics


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=12)
    ap.add_argument("--batch-size", type=int, default=24)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--max-per-class", type=int, default=800)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    os.environ.setdefault("MPLBACKEND", "Agg")
    run_training(
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        max_per_class=args.max_per_class,
        seed=args.seed,
    )
