import os
from .text_reader import read_text_file
from .tokenizer import clean_and_tokenize
from .statistics import calculate_statistics

async def analyze_document(file_path: str) -> dict:
    """
    Main entry point for the analyzer package.
    Coordinates reading, cleaning, and calculating statistics, 
    then returns the structured data dictionary.
    """
    original_text = await read_text_file(file_path)
    cleaned_text, tokens = clean_and_tokenize(original_text)
    
    (
        total_chars, 
        total_words, 
        total_sentences, 
        word_freq, 
        top_10
    ) = calculate_statistics(original_text, tokens)
    
    return {
        "document": {
            "filename": os.path.basename(file_path),
            "total_characters": total_chars,
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