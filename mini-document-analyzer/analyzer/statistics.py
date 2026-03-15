import collections
import re

def count_sentences(text: str) -> int:
    """
    Calculate the number of sentences using regex to handle 
    multiple punctuations like '...' or '?!'.
    """
    if not text.strip():
        return 0
    parts = re.split(r'[.!?]+', text)
    sentences = [p for p in parts if p.strip()]
    
    return len(sentences) or 1

def get_word_frequencies(tokens: list[str]) -> dict[str, int]:
    """
    Calculate the frequency of each word.
    """
    return dict(collections.Counter(tokens))

def get_top_n_words(tokens: list[str], n: int = 10) -> list[tuple[str, int]]:
    """
    Get the top N most frequent words.
    """
    return collections.Counter(tokens).most_common(n)