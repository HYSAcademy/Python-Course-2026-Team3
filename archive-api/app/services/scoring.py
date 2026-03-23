from abc import ABC, abstractmethod
import math
from collections import Counter
import re

class ISearchScorer(ABC):
    """
    Interface for various text relevance scoring algorithms.
    """
    @abstractmethod
    def calculate_scores(self, text: str) -> dict[str, float]:
        """Accepts text and returns a dictionary {word: weight}"""
        ...


class BM25Scorer(ISearchScorer):
    """
    Simplified on-the-fly BM25 implementation for a single document.
    Since we index the document in isolation (without having the entire corpus in memory),
    we focus on Term Frequency (TF) with saturation constants (k1, b).
    """
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.default_avgdl = 500 

    def calculate_scores(self, text: str) -> dict[str, float]:
        if not text:
            return {}
        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            return {}

        doc_length = len(words)
        term_frequencies = Counter(words)
        
        scores = {}
        for word, freq in term_frequencies.items():
            numerator = freq * (self.k1 + 1)
            denominator = freq + self.k1 * (1 - self.b + self.b * (doc_length / self.default_avgdl))
            scores[word] = round(numerator / denominator, 4)

        return scores


class ScorerFactory:
    """
    Determines which algorithm to use.
    """
    @staticmethod
    def get_scorer(strategy: str = "bm25") -> ISearchScorer:
        if strategy == "bm25":
            return BM25Scorer()
        raise ValueError(f"Unknown scoring strategy: {strategy}")