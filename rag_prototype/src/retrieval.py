from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from .config import (
    AUTHORITY_WEIGHT,
    CHUNKS_PATH,
    DISEASE_ALIASES,
    INDEX_PATH,
    INTENT_KEYWORDS,
    ensure_directories,
)


TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]+")


def tokenize(text: str) -> list[str]:
    words = [token.lower() for token in TOKEN_RE.findall(text)]
    # Korean endings make exact word matching brittle. Character bigrams supply a
    # compact lexical bridge without requiring a morphological analyzer.
    compact = "".join(words)
    bigrams = [compact[i : i + 2] for i in range(max(0, len(compact) - 1))]
    return words + bigrams


def classify_intents(query: str) -> list[str]:
    low = query.lower()
    intents = [
        intent
        for intent, keywords in INTENT_KEYWORDS.items()
        if any(keyword.lower() in low for keyword in keywords)
    ]
    return intents or ["source_check"]


def detect_diseases(query: str) -> list[str]:
    low = query.lower()
    return [
        disease
        for disease, aliases in DISEASE_ALIASES.items()
        if any(alias.lower() in low for alias in aliases)
    ]


@dataclass
class SearchResult:
    rank: int
    score: float
    chunk: dict

    @property
    def citation(self) -> str:
        locator = self.chunk.get("locator") or self.chunk.get("section_path") or "위치 미상"
        return f"[{self.chunk['source_org']}, {self.chunk['title']}, {locator}]"


class HybridRetriever:
    def __init__(self, payload: dict):
        self.chunks = payload["chunks"]
        self.vectorizer = payload["vectorizer"]
        self.matrix = payload["matrix"]
        self.bm25 = payload["bm25"]

    @classmethod
    def load(cls, path: Path = INDEX_PATH) -> "HybridRetriever":
        return cls(joblib.load(path))

    def search(
        self,
        query: str,
        top_k: int = 5,
        diseases: list[str] | None = None,
        intents: list[str] | None = None,
        include_historical: bool = False,
    ) -> list[SearchResult]:
        diseases = diseases if diseases is not None else detect_diseases(query)
        intents = intents if intents is not None else classify_intents(query)
        query_vec = normalize(self.vectorizer.transform([query]))
        dense_scores = (self.matrix @ query_vec.T).toarray().ravel()
        bm25_scores = np.asarray(self.bm25.get_scores(tokenize(query)), dtype=float)
        if bm25_scores.size and bm25_scores.max() > bm25_scores.min():
            bm25_scores = (bm25_scores - bm25_scores.min()) / (bm25_scores.max() - bm25_scores.min())
        combined = 0.58 * dense_scores + 0.42 * bm25_scores

        scored: list[tuple[float, int]] = []
        for index, chunk in enumerate(self.chunks):
            status = chunk.get("effective_status", "unknown")
            if status == "historical_unverified" and not include_historical:
                continue
            if "card_insurance" in intents and not include_historical:
                # The corpus contains only historical/unverified card-insurance
                # material. Returning an unrelated current medical document would
                # be more dangerous than returning an explicit evidence gap.
                if chunk.get("source_type") != "insurance_terms" or status != "current":
                    continue
            if "private_insurance" in intents:
                # No current private-policy terms are in the corpus. Returning
                # medical guidance as if it were policy evidence would be unsafe.
                if chunk.get("source_type") != "insurance_terms" or status != "current":
                    continue
            score = float(combined[index])
            score *= AUTHORITY_WEIGHT.get(chunk.get("authority_level", "D"), 0.8)
            chunk_diseases = set(chunk.get("disease_tags", []))
            chunk_intents = set(chunk.get("intent_tags", []))
            if diseases:
                score *= 1.34 if chunk_diseases.intersection(diseases) else 0.82
            if intents:
                score *= 1.22 if chunk_intents.intersection(intents) else 0.9
            if "military_care" in intents:
                military_official = (
                    chunk.get("source_type") in {"directive", "law"}
                    and "국방" in chunk.get("source_org", "")
                )
                score *= 1.35 if military_official else 0.94
            if status == "current":
                score *= 1.06
            scored.append((score, index))
        scored.sort(reverse=True)
        return [
            SearchResult(rank=rank, score=score, chunk=self.chunks[index])
            for rank, (score, index) in enumerate(scored[:top_k], start=1)
        ]


def build_index(chunks_path: Path = CHUNKS_PATH, output_path: Path = INDEX_PATH) -> dict:
    ensure_directories()
    with chunks_path.open(encoding="utf-8") as handle:
        chunks = [json.loads(line) for line in handle if line.strip()]
    texts = [
        " ".join(
            [
                chunk["title"],
                chunk.get("section_path", ""),
                " ".join(chunk.get("disease_tags", [])),
                " ".join(chunk.get("intent_tags", [])),
                chunk["text"],
            ]
        )
        for chunk in chunks
    ]
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(2, 5),
        min_df=1,
        max_df=0.995,
        sublinear_tf=True,
        max_features=180_000,
    )
    matrix = normalize(vectorizer.fit_transform(texts))
    bm25 = BM25Okapi([tokenize(text) for text in texts], k1=1.45, b=0.72)
    payload = {"chunks": chunks, "vectorizer": vectorizer, "matrix": matrix, "bm25": bm25}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, output_path, compress=3)
    return {
        "chunks": len(chunks),
        "features": len(vectorizer.vocabulary_),
        "index_size_bytes": output_path.stat().st_size,
    }


def main() -> None:
    print(json.dumps(build_index(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
