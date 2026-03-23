# utils/faiss_search.py
import faiss
import pandas as pd
import numpy as np
from pathlib import Path


class IrisSearcher:
    def __init__(self, index_path, meta_csv):
        self.index = faiss.read_index(str(Path(index_path)))
        self.meta = pd.read_csv(meta_csv)

    def search(self, emb, topk=5):
        if emb.ndim == 1:
            emb = emb.reshape(1, -1)

        D, I = self.index.search(emb.astype("float32"), topk)

        results = []
        for score, idx in zip(D[0], I[0]):
            row = self.meta.iloc[idx]
            results.append(
                {
                    "path": row["path"],
                    "blood_id": row["blood_id"],
                    "score": float(score),  # cosine
                }
            )

        return results
