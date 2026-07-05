import logging

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"


class EmbeddingService:
    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        except Exception as exc:
            logger.error("Failed to load embedding model '%s': %s", self.model_name, exc)
            self._model = None

    def embed(self, text: str) -> list[float]:
        self._load_model()
        if self._model is None:
            return []
        try:
            vec = self._model.encode(text, convert_to_numpy=True)
            return vec.tolist()
        except Exception as exc:
            logger.error("Failed to embed text: %s", exc)
            return []

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self._load_model()
        if self._model is None:
            return []
        try:
            mat = self._model.encode(texts, convert_to_numpy=True)
            return [row.tolist() for row in mat]
        except Exception as exc:
            logger.error("Failed to embed batch: %s", exc)
            return []
