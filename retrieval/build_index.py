# retrieval/build_index.py
from pathlib import Path
import faiss, numpy as np

BASE_DIR = Path(__file__).resolve().parent
emb = np.load(BASE_DIR / "embeddings.npy").astype("float32")
print("emb shape:", emb.shape)
d = emb.shape[1]
# use inner product on normalized vectors -> equivalent to cosine
index = faiss.IndexFlatIP(d)
# if many vectors, consider IndexIVFFlat + training
index.add(emb)
faiss.write_index(index, str(BASE_DIR / "idx.faiss"))
print("Index built. n=", index.ntotal)
