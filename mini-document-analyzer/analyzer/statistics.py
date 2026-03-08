import collections

def calculate_statistics(
    original_text: str, tokens: list[str]
) -> tuple[int, int, int, dict[str, int], list[tuple[str, int]]]:
    """
    Calculate text statistics: characters, words, sentences, word frequencies, 
    and the top 10 most frequent words.
    """

    total_characters = len(original_text)
    total_words = len(tokens)
    total_sentences = sum(original_text.count(char) for char in ".!?")
    
    if total_sentences == 0 and total_words > 0:
        total_sentences = 1
        
    word_counts = collections.Counter(tokens)
    word_frequencies = dict(word_counts)
    top_10_words = word_counts.most_common(10)
    
    return total_characters, total_words, total_sentences, word_frequencies, top_10_words