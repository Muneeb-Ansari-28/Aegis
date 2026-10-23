"""Retrieval module for Aegis RAG Assistant and Knowledge Base."""
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.config import get_settings
from app.rag.embedder import NomicEmbedder
from app.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)

RISK_CODE_RE = re.compile(r"\b(LLM\d\d(?::2026)?)\b", re.I)


class AssistantRetriever:
    """Retrieves and re-ranks relevant knowledge chunks for the Aegis AI Assistant."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedder: Optional[NomicEmbedder] = None,
    ) -> None:
        """Initialize retriever with vector store and embedder."""
        self.settings = get_settings()
        self.store = vector_store or VectorStore()
        self.embedder = embedder or NomicEmbedder()

    async def retrieve(
        self,
        query: str,
        n_results: int = 5,
        relevance_cutoff: Optional[float] = None,
        exclude_simple: bool = True,
    ) -> Tuple[List[str], List[Dict[str, Any]], List[str]]:
        """
        Embed the query and retrieve relevant chunks below the cosine distance cutoff.
        Applies level filtering, multi-topic balancing for comparisons, and deduplication.

        Args:
            query: User search query string.
            n_results: Maximum results to retrieve.
            relevance_cutoff: Maximum acceptable cosine distance.
            exclude_simple: Whether to exclude simple plain-language companion chunks.

        Returns:
            Tuple of (kept_documents, kept_metadatas, kept_ids).
        """
        cutoff = relevance_cutoff if relevance_cutoff is not None else self.settings.RAG_RELEVANCE_CUTOFF
        try:
            vec = await self.embedder.embed_query(query)
            where_filter: Optional[Dict[str, Any]] = {"level": {"$ne": "simple"}} if exclude_simple else None
            res = self.store.query(vec, n_results=n_results * 2, where=where_filter)
        except Exception as e:
            logger.error(f"Vector search failed for query '{query}': {e}")
            return [], [], []

        raw_docs = res.get("documents", [[]])[0]
        raw_metas = res.get("metadatas", [[]])[0]
        raw_ids = res.get("ids", [[]])[0]
        raw_dists = res.get("distances", [[]])[0]

        # If filtered search returned nothing, fallback to unfiltered
        if not raw_docs and exclude_simple:
            try:
                res_fallback = self.store.query(vec, n_results=n_results * 2)
                raw_docs = res_fallback.get("documents", [[]])[0]
                raw_metas = res_fallback.get("metadatas", [[]])[0]
                raw_ids = res_fallback.get("ids", [[]])[0]
                raw_dists = res_fallback.get("distances", [[]])[0]
            except Exception as e:
                logger.error(f"Fallback vector search failed for query '{query}': {e}")

        # Check if query asks for a comparison across multiple risks
        detected_risks: List[str] = []
        for r_match in RISK_CODE_RE.finditer(query):
            code = r_match.group(1).upper()
            canonical = code if ":2026" in code else f"{code}:2026"
            if canonical not in detected_risks:
                detected_risks.append(canonical)

        # Multi-risk balance: if comparing 2 risks, ensure both risks have representation
        if len(detected_risks) >= 2:
            collected_by_risk: Dict[str, List[Tuple[str, Dict[str, Any], str, float]]] = {
                r: [] for r in detected_risks
            }
            general_items: List[Tuple[str, Dict[str, Any], str, float]] = []

            for d, m, i, dist in zip(raw_docs, raw_metas, raw_ids, raw_dists):
                if dist > cutoff:
                    continue
                r_id = m.get("risk_id", "")
                if r_id in collected_by_risk:
                    collected_by_risk[r_id].append((d, m, i, dist))
                else:
                    general_items.append((d, m, i, dist))

            # If any detected risk has no chunks in initial retrieval, query specifically for it
            for r_id in detected_risks:
                if not collected_by_risk[r_id]:
                    try:
                        r_res = self.store.query(
                            vec,
                            n_results=2,
                            where={"$and": [{"risk_id": r_id}, {"level": {"$ne": "simple"}}]},
                        )
                        r_docs = r_res.get("documents", [[]])[0]
                        r_metas = r_res.get("metadatas", [[]])[0]
                        r_ids = r_res.get("ids", [[]])[0]
                        r_dists = r_res.get("distances", [[]])[0]
                        for rd, rm, ri, rdist in zip(r_docs, r_metas, r_ids, r_dists):
                            if rdist <= cutoff + 0.12:
                                collected_by_risk[r_id].append((rd, rm, ri, rdist))
                    except Exception as err:
                        logger.warning(f"Specific query for {r_id} failed: {err}")

            # Interleave balanced results
            balanced_candidates: List[Tuple[str, Dict[str, Any], str, float]] = []
            max_per_risk = max(2, n_results // len(detected_risks))
            for r_id in detected_risks:
                balanced_candidates.extend(collected_by_risk[r_id][:max_per_risk])
            balanced_candidates.extend(general_items)
            candidates = sorted(balanced_candidates, key=lambda x: x[3])
        else:
            candidates = [
                (d, m, i, dist)
                for d, m, i, dist in zip(raw_docs, raw_metas, raw_ids, raw_dists)
                if dist <= cutoff
            ]

            # Cross-source balance: if an OWASP risk code is queried alongside Aegis operations/testing,
            # guarantee that both OWASP risk definition and Aegis system documents appear in candidates
            if len(detected_risks) == 1:
                target_risk = detected_risks[0]
                q_lower = query.lower()
                mentions_aegis_ops = any(
                    term in q_lower
                    for term in ("aegis", "canary", "test", "scan", "playwright", "calibration", "report")
                )
                if mentions_aegis_ops:
                    owasp_cands = [c for c in candidates if "owasp" in c[1].get("source", "")]
                    aegis_cands = [c for c in candidates if "aegis" in c[1].get("source", "")]

                    if not owasp_cands:
                        try:
                            owasp_res = self.store.query(
                                vec,
                                n_results=2,
                                where={"$and": [{"risk_id": target_risk}, {"level": {"$ne": "simple"}}]},
                            )
                            for rd, rm, ri, rdist in zip(
                                owasp_res.get("documents", [[]])[0],
                                owasp_res.get("metadatas", [[]])[0],
                                owasp_res.get("ids", [[]])[0],
                                owasp_res.get("distances", [[]])[0],
                            ):
                                if rdist <= cutoff + 0.15:
                                    owasp_cands.append((rd, rm, ri, rdist))
                        except Exception as err:
                            logger.warning(f"Cross-source retrieval failed for {target_risk}: {err}")

                    if owasp_cands and aegis_cands:
                        # Interleave so both sources appear within top n_results
                        candidates = (
                            owasp_cands[:2]
                            + aegis_cands[: max(1, n_results - min(2, len(owasp_cands)))]
                            + owasp_cands[2:]
                            + aegis_cands[max(1, n_results - min(2, len(owasp_cands))) :]
                        )

        # Deduplicate chunks: avoid returning duplicate sections for the same risk
        seen_sections: Set[Tuple[str, str]] = set()
        kept_docs: List[str] = []
        kept_metas: List[Dict[str, Any]] = []
        kept_ids: List[str] = []

        for d, m, i, dist in candidates:
            r_id = m.get("risk_id", "")
            sec = m.get("section", "")
            key = (r_id, sec) if (r_id and sec) else (m.get("source_title", ""), sec)

            if key in seen_sections:
                continue
            seen_sections.add(key)

            clean_meta = dict(m)
            # Normalize source titles and source names
            if clean_meta.get("source") == "aegis_plain_language" or "owasp" in clean_meta.get("source", ""):
                clean_meta["source"] = "owasp_llm_top10_2026"
                clean_meta["source_title"] = "OWASP Top 10 for LLM Applications 2026"
            elif not clean_meta.get("source_title"):
                clean_meta["source_title"] = "Aegis System Documentation"

            clean_meta["distance"] = round(float(dist), 4)
            clean_meta["score"] = round(1.0 - float(dist), 4)
            clean_meta["chunk_id"] = i
            clean_meta["excerpt"] = d[:220].strip() + ("..." if len(d) > 220 else "")

            kept_docs.append(d)
            kept_metas.append(clean_meta)
            kept_ids.append(i)

            if len(kept_docs) >= n_results:
                break

        return kept_docs, kept_metas, kept_ids

    @staticmethod
    def format_context(documents: List[str], metadatas: List[Dict[str, Any]]) -> str:
        """
        Format retrieved document chunks with clean citation markers into a single string.

        Args:
            documents: List of chunk text passages.
            metadatas: List of chunk metadata dictionaries.

        Returns:
            Formatted context string.
        """
        formatted_chunks: List[str] = []
        for doc, meta in zip(documents, metadatas):
            risk_id = meta.get("risk_id", "")
            page = meta.get("page")
            source_title = meta.get("source_title") or (
                "OWASP Top 10 for LLM Applications 2026" if risk_id else "Aegis System Documentation"
            )
            section = meta.get("section", "Overview")

            if risk_id and page:
                cite_label = f"[{risk_id}, p.{page}]"
            elif risk_id:
                cite_label = f"[{risk_id}]"
            elif page:
                cite_label = f"[{source_title}, p.{page}]"
            else:
                cite_label = f"[{source_title}]"

            header = f"=== CONTEXT ITEM: {source_title} | Section: {section} | Inline Citation: {cite_label} ==="
            formatted_chunks.append(f"{header}\n{doc}")

        return "\n\n---\n\n".join(formatted_chunks)


class KBRetriever:
    """Attack path vs evaluation path retriever (backward compatible)."""

    async def retrieve_seeds(self, category: str) -> List[str]:
        """Retrieve seed prompts for a given vulnerability category."""
        return []
