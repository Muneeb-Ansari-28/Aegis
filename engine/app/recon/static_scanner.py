"""Tier 3 Static Project Folder Scanner.

Analyzes dependency manifests, Docker Compose services, AST import statements,
and environment variable names (strictly excluding values) to identify AI stack
components with high confidence.
"""
import ast
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

KNOWN_VECTOR_DBS = {
    "chromadb": "ChromaDB",
    "pinecone": "Pinecone",
    "pinecone-client": "Pinecone",
    "qdrant-client": "Qdrant",
    "qdrant": "Qdrant",
    "weaviate-client": "Weaviate",
    "weaviate": "Weaviate",
    "faiss-cpu": "FAISS",
    "faiss-gpu": "FAISS",
    "faiss": "FAISS",
    "pgvector": "pgvector",
    "milvus": "Milvus",
    "pymilvus": "Milvus",
}

KNOWN_FRAMEWORKS = {
    "langchain": "LangChain",
    "langchain-core": "LangChain",
    "langchain-community": "LangChain",
    "llama-index": "LlamaIndex",
    "llamaindex": "LlamaIndex",
    "langgraph": "LangGraph",
    "crewai": "CrewAI",
    "autogen": "AutoGen",
    "mcp": "Model Context Protocol",
    "streamlit": "Streamlit",
    "gradio": "Gradio",
    "fastapi": "FastAPI",
    "openai": "OpenAI SDK",
    "anthropic": "Anthropic SDK",
}

SENSITIVE_ENV_KEY_HINTS = {
    "PINECONE_API_KEY": "Pinecone Vector DB",
    "PINECONE_ENVIRONMENT": "Pinecone Vector DB",
    "CHROMA_HOST": "ChromaDB",
    "CHROMA_PORT": "ChromaDB",
    "WEAVIATE_URL": "Weaviate Vector DB",
    "QDRANT_URL": "Qdrant Vector DB",
    "OPENAI_API_KEY": "OpenAI API",
    "ANTHROPIC_API_KEY": "Anthropic API",
    "OLLAMA_BASE_URL": "Ollama LLM",
}


class StaticScanResult(BaseModel):
    project_path: str
    has_rag: bool = False
    has_vector_db: bool = False
    vector_db_names: List[str] = Field(default_factory=list)
    has_tools: bool = False
    detected_frameworks: List[str] = Field(default_factory=list)
    detected_dependencies: List[str] = Field(default_factory=list)
    detected_env_keys: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)


class StaticProjectScanner:
    """
    Scans an optional local project directory to extract ground-truth architectural evidence.
    """

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)

    def scan(self) -> StaticScanResult:
        if not self.project_path.exists() or not self.project_path.is_dir():
            return StaticScanResult(
                project_path=str(self.project_path),
                evidence=[f"Project directory '{self.project_path}' does not exist or is not a directory."],
            )

        found_dependencies: Set[str] = set()
        found_vector_dbs: Set[str] = set()
        found_frameworks: Set[str] = set()
        found_env_keys: List[str] = []
        evidence: List[str] = []
        has_tools = False

        # 1. Scan requirements.txt
        req_file = self.project_path / "requirements.txt"
        if req_file.exists():
            try:
                for line in req_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                    clean = line.strip().split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0].strip().lower()
                    if clean in KNOWN_VECTOR_DBS:
                        found_vector_dbs.add(KNOWN_VECTOR_DBS[clean])
                        evidence.append(f"requirements.txt specifies vector DB: {clean}")
                    if clean in KNOWN_FRAMEWORKS:
                        found_frameworks.add(KNOWN_FRAMEWORKS[clean])
                        evidence.append(f"requirements.txt specifies framework: {clean}")
                    if clean:
                        found_dependencies.add(clean)
            except Exception as e:
                logger.debug(f"Error parsing requirements.txt: {e}")

        # 2. Scan pyproject.toml
        pyproject_file = self.project_path / "pyproject.toml"
        if pyproject_file.exists():
            try:
                content = pyproject_file.read_text(encoding="utf-8", errors="ignore").lower()
                for dep, name in KNOWN_VECTOR_DBS.items():
                    if dep in content:
                        found_vector_dbs.add(name)
                        evidence.append(f"pyproject.toml contains vector DB reference: {dep}")
                for dep, name in KNOWN_FRAMEWORKS.items():
                    if dep in content:
                        found_frameworks.add(name)
                        evidence.append(f"pyproject.toml contains framework reference: {dep}")
            except Exception as e:
                logger.debug(f"Error parsing pyproject.toml: {e}")

        # 3. Scan package.json
        package_file = self.project_path / "package.json"
        if package_file.exists():
            try:
                data = json.loads(package_file.read_text(encoding="utf-8", errors="ignore"))
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                for dep in deps.keys():
                    d_lower = dep.lower()
                    if "chroma" in d_lower:
                        found_vector_dbs.add("ChromaDB")
                        evidence.append(f"package.json has dependency: {dep}")
                    if "@vercel/ai" in d_lower or "ai" == d_lower:
                        found_frameworks.add("Vercel AI SDK")
                        evidence.append(f"package.json has dependency: {dep}")
                    if "langchain" in d_lower:
                        found_frameworks.add("LangChain JS")
                        evidence.append(f"package.json has dependency: {dep}")
            except Exception as e:
                logger.debug(f"Error parsing package.json: {e}")

        # 4. Scan docker-compose.yml
        for compose_name in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]:
            compose_file = self.project_path / compose_name
            if compose_file.exists():
                try:
                    c_text = compose_file.read_text(encoding="utf-8", errors="ignore").lower()
                    for db_key, db_name in [("chroma", "ChromaDB"), ("qdrant", "Qdrant"), ("weaviate", "Weaviate"), ("pgvector", "pgvector")]:
                        if db_key in c_text:
                            found_vector_dbs.add(db_name)
                            evidence.append(f"{compose_name} specifies container service: {db_name}")
                except Exception as e:
                    logger.debug(f"Error parsing {compose_name}: {e}")

        # 5. Scan Python AST imports in top-level and src/app dirs
        py_files: List[Path] = []
        for ext in ["*.py"]:
            py_files.extend(list(self.project_path.glob(ext)))
            for sub in ["src", "app", "backend", "engine"]:
                sub_dir = self.project_path / sub
                if sub_dir.exists() and sub_dir.is_dir():
                    py_files.extend(list(sub_dir.glob(f"**/{ext}"))[:20])

        for py_path in py_files[:30]:  # Cap at 30 files for bounded performance
            try:
                tree = ast.parse(py_path.read_text(encoding="utf-8", errors="ignore"), filename=str(py_path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            root_mod = alias.name.split(".")[0].lower()
                            if root_mod in KNOWN_VECTOR_DBS:
                                found_vector_dbs.add(KNOWN_VECTOR_DBS[root_mod])
                                evidence.append(f"AST import in {py_path.name}: import {alias.name}")
                            if root_mod in KNOWN_FRAMEWORKS:
                                found_frameworks.add(KNOWN_FRAMEWORKS[root_mod])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            root_mod = node.module.split(".")[0].lower()
                            if root_mod in KNOWN_VECTOR_DBS:
                                found_vector_dbs.add(KNOWN_VECTOR_DBS[root_mod])
                                evidence.append(f"AST import in {py_path.name}: from {node.module} import ...")
                            if root_mod in KNOWN_FRAMEWORKS:
                                found_frameworks.add(KNOWN_FRAMEWORKS[root_mod])
                            if "tool" in node.module.lower() or "agent" in node.module.lower():
                                has_tools = True
            except Exception:
                continue

        # 6. Privacy-Guarded .env Scanning (KEY NAMES ONLY, NEVER VALUES)
        for env_name in [".env", ".env.local", ".env.development", ".env.example"]:
            env_file = self.project_path / env_name
            if env_file.exists():
                try:
                    for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            # STRICT PRIVACY: extract ONLY the key name, discard the value
                            key_name = line.split("=", 1)[0].strip()
                            if key_name:
                                found_env_keys.append(key_name)
                                if key_name in SENSITIVE_ENV_KEY_HINTS:
                                    hint = SENSITIVE_ENV_KEY_HINTS[key_name]
                                    evidence.append(f"{env_name} defines configuration key: {key_name} (indicates {hint})")
                                    if "Vector" in hint or "Chroma" in hint or "Pinecone" in hint:
                                        found_vector_dbs.add(hint.split()[0])
                except Exception as e:
                    logger.debug(f"Error inspecting {env_name}: {e}")

        # Check for vector store folders
        for folder_name in ["chroma", "faiss_index", "vector_store", "vectorstore"]:
            folder = self.project_path / folder_name
            if folder.exists() and folder.is_dir():
                found_vector_dbs.add(folder_name)
                evidence.append(f"Project directory contains persistent vector index folder: {folder_name}/")

        has_rag = bool(found_vector_dbs) or any("langchain" in f.lower() or "llamaindex" in f.lower() for f in found_frameworks)
        has_vector_db = bool(found_vector_dbs)

        return StaticScanResult(
            project_path=str(self.project_path),
            has_rag=has_rag,
            has_vector_db=has_vector_db,
            vector_db_names=list(found_vector_dbs),
            has_tools=has_tools or "LangGraph" in found_frameworks or "CrewAI" in found_frameworks,
            detected_frameworks=list(found_frameworks),
            detected_dependencies=list(found_dependencies),
            detected_env_keys=found_env_keys,
            evidence=evidence,
        )

