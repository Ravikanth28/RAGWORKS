"""
MCP RAG Module — Simulated Retrieval-Augmented Generation
----------------------------------------------------------
Loads a structured knowledge base (``parking_knowledge.json``) and
retrieves the most relevant entries for a given user query using
keyword-overlap scoring.

The retrieved context is injected into the MCP intent dict so that
downstream agents can ground their responses in factual information.

Note
~~~~
This is a *simulated* RAG implementation using keyword matching rather
than vector embeddings, which is appropriate for academic demonstration
purposes.  A production upgrade would replace the scorer with a vector
store (FAISS / ChromaDB / Pinecone) and a sentence-embedding model.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional

from utils.config import Config
from utils.logger import get_logger


class RAGModule:
    """
    Simulated Retrieval-Augmented Generation for parking knowledge.

    Each entry in the knowledge base has:

    * ``id``       — unique identifier
    * ``category`` — topic category (pricing, policy, location, tips)
    * ``keywords`` — list of trigger words for retrieval
    * ``content``  — factual text to return when the entry is selected

    Parameters
    ----------
    knowledge_file:
        Path to the JSON knowledge base file.  Defaults to
        ``Config.KNOWLEDGE_FILE``.
    """

    def __init__(self, knowledge_file: Optional[Path] = None):
        self.logger = get_logger(__name__)
        self.knowledge_file = knowledge_file or Config.KNOWLEDGE_FILE
        self.knowledge_base: List[Dict] = []
        self._load_knowledge_base()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _load_knowledge_base(self) -> None:
        """Load entries from the JSON knowledge base file."""
        try:
            with open(self.knowledge_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.knowledge_base = data.get("knowledge", [])
            self.logger.info(
                f"RAGModule: loaded {len(self.knowledge_base)} knowledge entries "
                f"from '{self.knowledge_file.name}'"
            )
        except FileNotFoundError:
            self.logger.warning(
                f"RAGModule: knowledge file not found at '{self.knowledge_file}' — "
                "RAG context will be empty."
            )
            self.knowledge_base = []
        except json.JSONDecodeError as exc:
            self.logger.error(f"RAGModule: failed to parse knowledge base — {exc}")
            self.knowledge_base = []

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve_context(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Retrieve the *top_k* most relevant knowledge entries for *query*.

        Scoring:
        - Tokenise the query on whitespace.
        - For each knowledge entry, count how many query tokens appear in
          the entry's ``keywords`` list.
        - Return the top-k entries sorted by score descending.

        Parameters
        ----------
        query:
            User query string.
        top_k:
            Maximum number of entries to return.

        Returns
        -------
        List[Dict]
            Relevant knowledge entry dicts, most relevant first.
        """
        if not self.knowledge_base:
            return []

        query_tokens = set(query.lower().split())
        scored: List[tuple] = []

        for entry in self.knowledge_base:
            entry_keywords = {kw.lower() for kw in entry.get("keywords", [])}
            score = len(query_tokens & entry_keywords)
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [entry for _, entry in scored[:top_k]]

        self.logger.debug(
            f"RAGModule: retrieved {len(results)} entries for query '{query[:60]}'"
        )
        return results

    def get_context_text(self, query: str) -> str:
        """
        Return retrieved context as a single formatted string.

        Format:  ``[CATEGORY] <content text>``

        Parameters
        ----------
        query:
            User query string.

        Returns
        -------
        str
            Multi-line context string, or ``""`` if nothing retrieved.
        """
        entries = self.retrieve_context(query)
        if not entries:
            return ""

        lines = []
        for entry in entries:
            category = entry.get("category", "info").upper()
            content  = entry.get("content", "")
            lines.append(f"[{category}] {content}")

        return "\n".join(lines)

    def enrich_intent(self, intent: dict, query: str) -> dict:
        """
        Attach RAG-retrieved context to an MCP intent dict.

        Adds two fields:
        - ``rag_context``      — list of raw knowledge-entry dicts
        - ``rag_context_text`` — pre-formatted context string

        Parameters
        ----------
        intent:
            MCP intent dict to enrich.
        query:
            Original user query used for retrieval.

        Returns
        -------
        dict
            The same *intent* dict with RAG fields added in-place.
        """
        entries = self.retrieve_context(query)
        intent["rag_context"]      = entries
        intent["rag_context_text"] = self.get_context_text(query)

        self.logger.debug(
            f"RAGModule: enriched intent with {len(entries)} context entries"
        )
        return intent
