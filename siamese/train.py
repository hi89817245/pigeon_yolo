# siamese/train.py
import os
import random
import sys
from pathlib import Path
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from sklearn.metrics import roc_auc_score
import pandas as pd
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from siamese.dataset import SiamesePairsDataset, get_transforms
from siamese.model import SiameseNet

# ------------- CONFIG -------------
DATA_ROOT = Path(os.environ.get("PIGEON_DATA_ROOT", REPO_ROOT))

PAIRS_CSV = DATA_ROOT / "pairs.csv"  # your pairs.csv
CROPS_ROOT = DATA_ROOT / "crops"  # folder with images referenced in pairs.csv
CHECKPOINT_DIR = REPO_ROOT / "siamese" / "checkpoints"
os.makedirs(CHECKPOINT_DIR, exist_ok=True)

EMB_SIZE = 128
BACKBONE = "resnet50"  # change to resnet50 if GPU enough
BATCH = 32
EPOCHS = 15
LR = 1e-5
WEIGHT_DECAY = 1e-5
VAL_SPLIT = 0.1
MARGIN = 1.0  # for contrastive loss
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
# ----------------------------------


# Contrastive loss
class ContrastiveLoss(nn.Module):
    def __init__(self, margin=1.0):
        super().__init__()
        self.margin = margin

    def forward(self, e1, e2, label):
        # label 1 -> similar; 0 -> different
        dist_sq = torch.sum((e1 - e2) ** 2, dim=1)
        dist = torch.sqrt(dist_sq + 1e-8)
        pos = label * dist_sq
        neg = (1 - label) * torch.clamp(self.margin - dist, min=0.0) ** 2
        loss = torch.mean(0.5 * (pos + neg))
        return loss


def collate_fn(batch):
    a = torch.stack([b[0] for b in batch], dim=0)
    b = torch.stack([b[1] for b in batch], dim=0)
    label = torch.tensor([b[2] for b in batch], dtype=torch.float32)
    return a, b, label


def main():
    # load pairs, small sanity check
    df = pd.read_csv(PAIRS_CSV)
    print("Total pairs:", len(df))

    dataset = SiamesePairsDataset(
        PAIRS_CSV, CROPS_ROOT, transform=get_transforms(train=True)
    )
    val_len = int(len(dataset) * VAL_SPLIT)
    train_len = len(dataset) - val_len
    train_ds, val_ds = random_split(dataset, [train_len, val_len])
    train_loader = DataLoader(
        train_ds,
        batch_size=BATCH,
        shuffle=True,
        num_workers=4,
        collate_fn=collate_fn,
        pin_memory=True,
    )
    val_loader = DataLoader(
        val_ds, batch_size=BATCH, shuffle=False, num_workers=4, collate_fn=collate_fn
    )

    model = SiameseNet(emb_size=EMB_SIZE, pretrained=True).to(DEVICE)
    criterion = ContrastiveLoss(margin=MARGIN)
    optimizer = optim.Adam(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)

    best_val = 1e9

    for epoch in range(1, EPOCHS + 1):
        model.train()
        running_loss = 0.0
        for a, b, label in tqdm(train_loader, desc=f"Epoch {epoch} train"):
            a = a.to(DEVICE)
            b = b.to(DEVICE)
            label = label.to(DEVICE)
            e1 = model(a)
            e2 = model(b)
            loss = criterion(e1, e2, label)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * a.size(0)
        running_loss /= len(train_loader.dataset)

        # validation
        model.eval()
        val_loss = 0.0
        sims = []
        labs = []
        with torch.no_grad():
            for a, b, label in tqdm(val_loader, desc=f"Epoch {epoch} val"):
                a = a.to(DEVICE)
                b = b.to(DEVICE)
                label = label.to(DEVICE)
                e1 = model(a)
                e2 = model(b)
                loss = criterion(e1, e2, label)
                val_loss += loss.item() * a.size(0)

                # compute cosine similarity for ROC/AUC
                cos = (e1 * e2).sum(dim=1).cpu().numpy()
                sims.extend(list(cos))
                labs.extend(list(label.cpu().numpy()))
        val_loss /= len(val_loader.dataset)
        try:
            auc = roc_auc_score(labs, sims)
        except Exception:
            auc = 0.0

        print(
            f"Epoch {epoch}: train_loss={running_loss:.4f}, val_loss={val_loss:.4f}, val_auc={auc:.4f}"
        )

        # save best by val_loss
        if val_loss < best_val:
            best_val = val_loss
            torch.save(model.state_dict(), str(CHECKPOINT_DIR / "best.pth"))
            print("Saved best model.")
        scheduler.step()

    # final save
    torch.save(model.state_dict(), str(CHECKPOINT_DIR / f"final_epoch{EPOCHS}.pth"))
    print("Training finished. Best val loss:", best_val)


if __name__ == "__main__":
    main()
