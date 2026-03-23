from __future__ import annotations

import os
from pathlib import Path

import torch

from project.models.siamese import load_siamese
from project.utils.embedding import embed_image
from project.utils.faiss_search import IrisSearcher
from project.utils.yolo_crop import IrisCropper


class IrisPipeline:
    def __init__(
        self,
        project_dir: str | Path | None = None,
        assets_dir: str | Path | None = None,
        crop_dir: str | Path | None = None,
        device: str | None = None,
        sim_threshold: float = 0.8,
    ):
        self.project_dir = (
            Path(project_dir) if project_dir else Path(__file__).resolve().parents[1]
        )
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.sim_threshold = sim_threshold

        self.assets_dir = Path(
            assets_dir
            or os.environ.get("PIGEON_MODELS_DIR")
            or (self.project_dir / "assets")
        )
        self.yolo_model = self.assets_dir / "best.pt"
        self.siamese_model = self.assets_dir / "best.pth"
        self.faiss_index = self.assets_dir / "idx.faiss"
        self.meta_csv = self.assets_dir / "meta.csv"
        self.crop_dir = Path(
            crop_dir
            or os.environ.get("PIGEON_CROP_DIR")
            or (self.project_dir / "tmp" / "crops")
        )

        self.cropper = IrisCropper(self.yolo_model, out_dir=self.crop_dir)
        self.siamese = load_siamese(str(self.siamese_model), self.device)
        self.searcher = IrisSearcher(str(self.faiss_index), str(self.meta_csv))

    def compare(self, img1_path: str, img2_path: str):
        crop1 = self.cropper.crop(img1_path)
        if crop1 is None:
            return {"error": "Image 1 iris not detected or invalid image"}

        crop2 = self.cropper.crop(img2_path)
        if crop2 is None:
            return {"error": "Image 2 iris not detected or invalid image"}

        e1 = embed_image(self.siamese, crop1, self.device)
        e2 = embed_image(self.siamese, crop2, self.device)

        similarity = float((e1 * e2).sum())
        return {
            "similarity": similarity,
            "same_blood": similarity >= self.sim_threshold,
            "crop1": crop1,
            "crop2": crop2,
        }

    def search(self, img_path: str, topk: int = 5):
        crop = self.cropper.crop(img_path)
        if crop is None:
            return {"error": "iris not detected"}

        emb = embed_image(self.siamese, crop, self.device)
        results = self.searcher.search(emb, topk)
        return {"query_crop": crop, "results": results}

    def embed(self, img_path: str):
        crop = self.cropper.crop(img_path)
        if crop is None:
            return {"error": "iris not detected"}

        emb = embed_image(self.siamese, crop, self.device)[0].tolist()
        return {"query_crop": crop, "embedding": emb}
