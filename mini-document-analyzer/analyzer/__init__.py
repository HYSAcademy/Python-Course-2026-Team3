import os
from .text_reader import read_text_file
from .tokenizer import clean_text, tokenize
from .statistics import count_sentences, get_word_frequencies, get_top_n_words

async def analyze_document(file_path: str) -> dict:
    """
    Main entry point for the analyzer package.
    Coordinates reading, cleaning, and calculating statistics, 
    then returns the structured data dictionary.
    """
    original_text = await read_text_file(file_path)
    
    cleaned_text = clean_text(original_text)
    tokens = tokenize(cleaned_text)
    
    total_characters = len(original_text)
    total_words = len(tokens)
    total_sentences = count_sentences(original_text)
    
    word_freq = get_word_frequencies(tokens)
    top_10 = get_top_n_words(tokens, n=10)
    
    return {
        "document": {
            "filename": os.path.basename(file_path),
            "total_characters": total_characters,
            "total_words": total_words,
            "total_sentences": total_sentences,
        },
        "content": {
            "cleaned_text": cleaned_text,
            "tokens": tokens,
        },
        "statistics": {
            "word_frequencies": word_freq,
            "top_10_words": top_10,
        },
    }