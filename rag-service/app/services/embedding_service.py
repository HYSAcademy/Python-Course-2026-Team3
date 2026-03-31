from tenacity import retry, stop_after_attempt, wait_exponential
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.core.logger import logger 

class EmbeddingService:
    def __init__(self):
        model_name = getattr(settings, "embedding_model_name", "text-embedding-3-small")
        self.embeddings_client = OpenAIEmbeddings(
            model=model_name,
            api_key=settings.openai_api_key.get_secret_value(),
            max_retries=0
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=75,
            separators=["\n\n", "\n", ".", "?", "!", " ", ""]
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def _embed_documents_with_retry(self, chunks: list[str]) -> list[list[float]]:
        return await self.embeddings_client.aembed_documents(chunks)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def generate_query_embedding(self, query: str) -> list[float]:
        """
        Generates an embedding vector for the user's query with retry logic.
        """
        return await self.embeddings_client.aembed_query(query)

    async def generate_chunks_and_embeddings(self, text: str) -> list[dict]:
        """
        Takes a long text, splits it into chunks, and generates embeddings for each chunk.
        Returns a list of dictionaries with chunk index, chunk text, and embedding vector.
        """
        logger.info("Starting text chunking.")
        
        chunks = self.text_splitter.split_text(text)
        logger.info(f"Text split into {len(chunks)} chunks. Requesting embeddings...")

        if not chunks:
            return []

        vectors = await self._embed_documents_with_retry(chunks)
        logger.info("Embeddings received from OpenAI.")

        result = []
        for index, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
            result.append({
                "chunk_index": index,
                "chunk_text": chunk_text,
                "embedding": vector
            })
            
        return result

embedding_service = EmbeddingService()