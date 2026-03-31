import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.llm_service import LLMService

@pytest.fixture
def llm_service():
    """Fixture for creating the service."""
    return LLMService()

@pytest.mark.asyncio
async def test_refine_query_success(mocker, llm_service):
    """
    Testing that refine_query successfully removes 'noise' from the query.
    We MOCK the OpenAI call so the test is fast and free.
    """
    raw_query = "Hi, bot! Could you please tell me what LangChain is?"
    expected_clean_query = "LangChain definition"

    mock_response = MagicMock()
    mock_response.content = expected_clean_query

    mock_ainvoke = mocker.patch(
        "langchain_openai.ChatOpenAI.ainvoke", 
        new_callable=AsyncMock, 
        return_value=mock_response
    )

    result = await llm_service.refine_query(raw_query)

    assert result == expected_clean_query, "The query was not cleaned properly!"
    
    mock_ainvoke.assert_called_once()

@pytest.mark.asyncio
async def test_refine_query_fallback_on_error(mocker, llm_service):
    """
    Testing resiliency:
    if OpenAI fails with an error, the method should return the original query (Fallback).
    """
    raw_query = "What is RAG?"
    mocker.patch(
        "langchain_openai.ChatOpenAI.ainvoke", 
        new_callable=AsyncMock, 
        side_effect=Exception("OpenAI is down 500 Internal Server Error")
    )

    result = await llm_service.refine_query(raw_query)

    assert result == raw_query, "Fallback did not work when OpenAI failed!"