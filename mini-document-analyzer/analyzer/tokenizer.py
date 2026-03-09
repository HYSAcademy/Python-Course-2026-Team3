import re

def clean_and_tokenize(text: str) -> tuple[str, list[str]]:
    """
    Clean text by converting to lowercase and removing punctuation,
    then tokenize it by splitting on whitespace.
    """
    
    cleaned_text = re.sub(r'[^\w\s]', '', text.lower())
    tokens = cleaned_text.split()
    
    return cleaned_text, tokens