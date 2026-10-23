"""ChromaDB Vector Store Adapter for Aegis Knowledge Base."""
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
import chromadb
from app.core.paths import get_app_data_dir


class VectorStore:
    """Persistent ChromaDB vector store adapter."""

    def __init__(self, collection_name: str = "aegis_kb") -> None:
        """
        Initialize the persistent ChromaDB client and collection.

        Args:
            collection_name: Name of the vector collection (default: 'aegis_kb').
        """
        self.chroma_path = Path(get_app_data_dir()) / "chroma"
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.chroma_path))
        self.collection_name = collection_name
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_documents(
        self,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        """
        Upsert document chunks into the collection with deterministic IDs.

        Args:
            ids: List of unique chunk IDs.
            documents: List of text chunk strings.
            embeddings: List of embedding vectors.
            metadatas: List of chunk metadata dictionaries.
        """
        if not ids:
            return
        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    # Alias for backward-compatibility with reference code
    def add_documents(
        self,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        """Alias for upsert_documents."""
        self.upsert_documents(ids, documents, embeddings, metadatas)

    def query(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Query the collection for the nearest chunks.

        Args:
            query_embedding: Vector embedding of the search query.
            n_results: Maximum number of chunks to return.
            where: Optional Chroma filter metadata dict.

        Returns:
            Dict containing 'ids', 'documents', 'metadatas', 'distances'.
        """
        kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
        }
        if where:
            kwargs["where"] = where
        return self.collection.query(**kwargs)

    def get_by_ids(self, ids: List[str]) -> Dict[str, Any]:
        """
        Retrieve chunks by their exact deterministic IDs.

        Args:
            ids: List of chunk IDs.

        Returns:
            Dict containing 'ids', 'documents', 'metadatas'.
        """
        if not ids:
            return {"ids": [], "documents": [], "metadatas": []}
        return self.collection.get(ids=ids)

    def get_simple(self, risk_ids: Union[Set[str], List[str]]) -> Dict[str, Any]:
        """
        Retrieve plain-language chunks for the specified risk IDs.

        Args:
            risk_ids: Set or list of risk identifiers (e.g. {'LLM08:2026', 'LLM01:2026'}).

        Returns:
            Dict containing 'ids', 'documents', 'metadatas'.
        """
        cleaned_risks = [r for r in risk_ids if r]
        if not cleaned_risks:
            return {"ids": [], "documents": [], "metadatas": []}

        try:
            if len(cleaned_risks) == 1:
                where_clause: Dict[str, Any] = {
                    "$and": [
                        {"level": "simple"},
                        {"risk_id": cleaned_risks[0]},
                    ]
                }
            else:
                where_clause = {
                    "$and": [
                        {"level": "simple"},
                        {"risk_id": {"$in": cleaned_risks}},
                    ]
                }
            return self.collection.get(where=where_clause)
        except Exception:
            # Fallback to level-only query and client filter if complex where clause fails
            res = self.collection.get(where={"level": "simple"})
            docs = res.get("documents", [])
            metas = res.get("metadatas", [])
            ids = res.get("ids", [])
            filtered_docs = []
            filtered_metas = []
            filtered_ids = []
            for d, m, i in zip(docs, metas, ids):
                if m.get("risk_id") in cleaned_risks:
                    filtered_docs.append(d)
                    filtered_metas.append(m)
                    filtered_ids.append(i)
            return {"ids": filtered_ids, "documents": filtered_docs, "metadatas": filtered_metas}

    def count(self) -> int:
        """Return total number of chunks in the collection."""
        return self.collection.count()

    def reset(self) -> None:
        """Delete and recreate the collection."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
