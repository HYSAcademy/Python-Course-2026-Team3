import re

def clean_text(text: str) -> str:
    """
    Clean text by converting to lowercase and removing punctuation.
    """
    return re.sub(r'[^\w\s]', '', text.lower())

def tokenize(text: str) -> list[str]:
    """
    Tokenize text by splitting on whitespace.
    """
    return text.split()