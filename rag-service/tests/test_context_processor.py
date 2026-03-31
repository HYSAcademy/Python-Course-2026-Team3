import pytest
from app.services.context_processor import ContextProcessor

@pytest.fixture
def processor():
    """Fixture for creating a processor instance before each test."""
    return ContextProcessor(model_name="gpt-4o-mini")

def test_lost_in_the_middle_reordering(processor):
    """
    Testing the Lost in the Middle pattern.
    We expect the best chunks to go to the edges (indices 0 and -1),
    and the worse ones to the middle.
    """
    chunks = ["Chunk 1", "Chunk 2", "Chunk 3", "Chunk 4", "Chunk 5"]

    reordered = processor._reorder_for_lost_in_the_middle(chunks)

    expected = ["Chunk 1", "Chunk 3", "Chunk 5", "Chunk 4", "Chunk 2"]
    
    assert reordered == expected, f"Expected {expected}, but got {reordered}"

def test_token_budgeting_respects_limit(mocker, processor):
    """
    Testing context trimming.
    We use mocker to avoid counting real tokens,
    and instead say: "let each chunk weigh 1000 tokens".
    """
    chunks = ["Text 1", "Text 2", "Text 3", "Text 4", "Text 5"]
    
    mocker.patch.object(processor, 'count_tokens', return_value=1000)
    budgeted_chunks = processor._apply_token_budgeting(chunks, max_tokens=3000)

    assert len(budgeted_chunks) == 3, "Only 3 chunks should remain to fit within 3000 tokens"
    assert budgeted_chunks == ["Text 1", "Text 2", "Text 3"], "Chunks should be dropped from the end"