"""Regulatory document indexer using Sentence-Transformers and FAISS."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

# Standard stop words for fallback lexical matching
STOP_WORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "by", "as", "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "what", "which", "who", "whom", "this", "that",
    "these", "those", "from", "it", "its", "they", "them", "their", "how", "why"
}

_FAISS_AVAILABLE = False
_ST_AVAILABLE = False

try:
    import faiss
    _FAISS_AVAILABLE = True
except ImportError:
    logger.warning("FAISS not installed. RAG will use vectorized NumPy cosine similarity fallback.")

try:
    from sentence_transformers import SentenceTransformer
    _ST_AVAILABLE = True
except ImportError:
    logger.warning("sentence-transformers not installed. RAG will use keyword filtering fallback.")


class RegulatoryChunk:
    def __init__(
        self,
        chunk_id: str,
        document_title: str,
        section_reference: str,
        publication_year: Optional[int],
        url: Optional[str],
        text: str,
    ):
        self.chunk_id = chunk_id
        self.document_title = document_title
        self.section_reference = section_reference
        self.publication_year = publication_year
        self.url = url
        self.text = text

    def to_dict(self) -> Dict:
        return {
            "chunk_id": self.chunk_id,
            "document_title": self.document_title,
            "section_reference": self.section_reference,
            "publication_year": self.publication_year,
            "url": self.url,
            "text": self.text,
        }


def parse_raw_regulatory_file(filepath: Path) -> List[RegulatoryChunk]:
    """Parses text regulatory documents into metadata-tagged chunks."""
    content = filepath.read_text(encoding="utf-8")
    lines = content.split("\n")

    doc_title = None
    section_ref = "General"
    pub_year = None
    url = None

    body_lines = []
    for line in lines:
        if line.startswith("# Document Title:"):
            doc_title = line.replace("# Document Title:", "").strip()
        elif line.startswith("# Section Reference:"):
            section_ref = line.replace("# Section Reference:", "").strip()
        elif line.startswith("# Publication Date:"):
            date_str = line.replace("# Publication Date:", "").strip()
            try:
                pub_year = int(date_str[:4])
            except ValueError:
                pass
        elif line.startswith("# Reference URL:"):
            url = line.replace("# Reference URL:", "").strip()
        elif not line.startswith("#"):
            body_lines.append(line)

    full_body = "\n".join(body_lines).strip()
    if not full_body or not doc_title or pub_year is None or not url:
        logger.warning("Skipping %s: source text, official title, publication year, and source URL are required.", filepath)
        return []

    paragraphs = [p.strip() for p in full_body.split("\n\n") if p.strip()]
    chunks = []
    for idx, p in enumerate(paragraphs):
        p_sec = section_ref
        first_line = p.split("\n")[0]
        if any(first_line.startswith(prefix) for prefix in ["1.", "2.", "3.", "4.", "ARTICLE", "QUESTION"]):
            p_sec = first_line.strip()

        chunk_id = f"{filepath.stem}_{idx}"
        chunks.append(
            RegulatoryChunk(
                chunk_id=chunk_id,
                document_title=doc_title,
                section_reference=p_sec,
                publication_year=pub_year,
                url=url,
                text=p,
            )
        )
    return chunks


def load_all_regulatory_chunks(docs_dir: Path) -> List[RegulatoryChunk]:
    """Loads all regulatory text documents from data/regulatory_docs."""
    chunks: List[RegulatoryChunk] = []
    for ext in ["*.txt", "*.md"]:
        for file in docs_dir.glob(ext):
            try:
                chunks.extend(parse_raw_regulatory_file(file))
            except Exception as e:
                logger.error(f"Error parsing regulatory file {file}: {e}")
    return chunks


class RegulatoryVectorStore:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.chunks: List[RegulatoryChunk] = []
        self.embeddings: Optional[np.ndarray] = None
        self.faiss_index = None
        self._model = None

    def _get_embedding_model(self):
        if self._model is None and _ST_AVAILABLE:
            try:
                self._model = SentenceTransformer(self.model_name)
            except Exception as e:
                logger.warning(f"Could not initialize SentenceTransformer '{self.model_name}': {e}")
        return self._model

    def build_index(self, docs_dir: Path, output_dir: Path):
        """Builds embeddings and FAISS index from documents."""
        self.chunks = load_all_regulatory_chunks(docs_dir)
        if not self.chunks:
            logger.warning(f"No regulatory documents found in {docs_dir}")
            return

        texts = [c.text for c in self.chunks]
        model = self._get_embedding_model()

        if model:
            embs = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
            self.embeddings = embs.astype(np.float32)
            dim = self.embeddings.shape[1]

            if _FAISS_AVAILABLE:
                index = faiss.IndexFlatIP(dim)
                index.add(self.embeddings)
                self.faiss_index = index

                output_dir.mkdir(parents=True, exist_ok=True)
                faiss.write_index(index, str(output_dir / "cbam_regulations.index"))

        meta_path = output_dir / "chunks_metadata.json"
        meta_path.write_text(
            json.dumps([c.to_dict() for c in self.chunks], indent=2),
            encoding="utf-8",
        )
        logger.info(f"Successfully indexed {len(self.chunks)} regulatory chunks into {output_dir}")

    def load_index(self, index_dir: Path) -> bool:
        """Loads FAISS index and chunk metadata from disk."""
        meta_path = index_dir / "chunks_metadata.json"
        index_path = index_dir / "cbam_regulations.index"

        if not meta_path.exists():
            return False

        try:
            raw_meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self.chunks = [
                RegulatoryChunk(
                    chunk_id=item["chunk_id"],
                    document_title=item["document_title"],
                    section_reference=item["section_reference"],
                    publication_year=item["publication_year"],
                    url=item["url"],
                    text=item["text"],
                )
                for item in raw_meta
            ]

            if _FAISS_AVAILABLE and index_path.exists():
                self.faiss_index = faiss.read_index(str(index_path))
            return True
        except Exception as e:
            logger.error(f"Failed to load vector store from {index_dir}: {e}")
            return False

    def search(self, query: str, top_k: int = 3) -> List[Tuple[RegulatoryChunk, float]]:
        """Searches index for top_k most relevant regulatory chunks."""
        if not self.chunks:
            return []

        model = self._get_embedding_model()
        if model and self.faiss_index is not None:
            q_emb = model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype(np.float32)
            distances, indices = self.faiss_index.search(q_emb, min(top_k, len(self.chunks)))
            results = []
            for score, idx in zip(distances[0], indices[0]):
                if idx >= 0 and idx < len(self.chunks):
                    results.append((self.chunks[idx], float(score)))
            return results

        # Semantic/Lexical keyword score with stop-word filtering
        q_words = [w.lower().strip(".,?!:;\"'") for w in query.split()]
        informative_q_words = [w for w in q_words if w and w not in STOP_WORDS]

        if not informative_q_words:
            return []

        scores = []
        for c in self.chunks:
            c_text_lower = c.text.lower()
            matches = sum(1 for w in informative_q_words if w in c_text_lower)
            score = matches / len(informative_q_words)
            scores.append(score)

        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(self.chunks[i], float(scores[i])) for i in top_indices if scores[i] > 0]


# Singleton vector store instance
regulatory_store = RegulatoryVectorStore(model_name=settings.EMBEDDING_MODEL_NAME)


def get_vector_store() -> RegulatoryVectorStore:
    """Returns initialized regulatory vector store, building it if not yet indexed."""
    if not regulatory_store.chunks:
        success = regulatory_store.load_index(settings.FAISS_INDEX_DIR)
        if not success or not regulatory_store.chunks:
            regulatory_store.build_index(settings.RAG_DATA_DIR, settings.FAISS_INDEX_DIR)
    return regulatory_store
