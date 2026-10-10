"""ChromaDB Vector Store Adapter."""
class VectorStore:
    def __init__(self, collection_name: str = "aegis_kb"):
        self.collection_name = collection_name
