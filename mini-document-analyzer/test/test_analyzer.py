import pytest
from analyzer import analyze_document
from analyzer.tokenizer import clean_and_tokenize

def test_clean_and_tokenize_happy_path():
    """Tests tokenization of a standard sentence."""
    text = "Hello, World! Welcome to Python 2026."
    cleaned, tokens = clean_and_tokenize(text)
    assert tokens == ["hello", "world", "welcome", "to", "python", "2026"]

def test_clean_and_tokenize_case_insensitivity():
    """Verifies that tokenization is case-insensitive."""
    text = "Apple APPLE aPpLe."
    cleaned, tokens = clean_and_tokenize(text)
    assert tokens == ["apple", "apple", "apple"]
    assert len(tokens) == 3

def test_clean_and_tokenize_only_punctuation():
    """Tests tokenization of a string containing only punctuation."""
    text = "   ... !!! ??? ,,,   -  "
    cleaned, tokens = clean_and_tokenize(text)
    assert len(tokens) == 0 
    assert len(cleaned.strip()) == 0

@pytest.mark.asyncio
async def test_analyze_document_standard(tmp_path):
    """Tests analysis metrics for a standard text document."""
    test_file = tmp_path / "standard.txt"
    test_file.write_text("Hello world! Hello Python. Are you ready?", encoding="utf-8")
    
    result = await analyze_document(str(test_file))
    
    assert result["document"]["filename"] == "standard.txt"
    assert result["document"]["total_sentences"] == 3
    assert result["document"]["total_words"] == 7
    assert result["statistics"]["word_frequencies"]["hello"] == 2

@pytest.mark.asyncio
async def test_analyze_document_empty_file(tmp_path):
    """Verifies handling of a 0-byte empty file."""
    test_file = tmp_path / "empty.txt"
    test_file.touch() 
    
    result = await analyze_document(str(test_file))
    
    assert result["document"]["total_sentences"] == 0
    assert result["document"]["total_words"] == 0
    assert result["document"]["total_characters"] == 0
    assert result["content"]["tokens"] == []
    assert result["statistics"]["top_10_words"] == []
    assert result["statistics"]["word_frequencies"] == {}

@pytest.mark.asyncio
async def test_analyze_document_multiline(tmp_path):
    """Tests analysis of a file with multiple newlines and varying whitespace."""
    test_file = tmp_path / "multiline.txt"
    content = "Line one.\n\n\nLine two!\n\t\nLine three?"
    test_file.write_text(content, encoding="utf-8")
    
    result = await analyze_document(str(test_file))
    
    assert result["document"]["total_sentences"] == 3
    assert result["document"]["total_words"] == 6
    assert "one" in result["content"]["tokens"]

@pytest.mark.asyncio
async def test_analyze_missing_file():
    """Ensures FileNotFoundError is raised when attempting to analyze a non-existent file."""
    with pytest.raises(FileNotFoundError):
        await analyze_document("this_file_does_not_exist_at_all.txt")