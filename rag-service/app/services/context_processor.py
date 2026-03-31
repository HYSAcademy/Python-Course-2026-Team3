import tiktoken
from app.core.logger import logger
from app.core.config import settings

class ContextProcessor:
    """Class responsible for preparing and optimizing context for LLM input."""
    def __init__(self, model_name: str):
        self.model_name = model_name
        try:
            self._encoding = tiktoken.encoding_for_model(self.model_name)
            logger.info(f"Successfully loaded tokeniser for '{self.model_name}'")
        except KeyError:
            logger.warning(f"tiktoken does not recognize model '{self.model_name}'. Falling back to default encodings.")
            try:
                self._encoding = tiktoken.get_encoding("o200k_base")
            except ValueError:
                self._encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self._encoding.encode(text))

    def prepare_context(self, chunks: list[str], max_tokens: int = 3000) -> str:
        """Main method for preparing context."""
        budgeted = self._apply_token_budgeting(chunks, max_tokens)
        optimized = self._reorder_for_lost_in_the_middle(budgeted)
        return "\n\n---\n\n".join(optimized)

    def _apply_token_budgeting(self, chunks: list[str], max_tokens: int) -> list[str]:
        """Applies token budgeting to limit the number of tokens in the context."""
        selected_chunks = []
        total_tokens = 0
        
        for chunk in chunks:
            chunk_tokens = self.count_tokens(chunk)
            if total_tokens + chunk_tokens > max_tokens:
                logger.warning(f"Token limit reached. Dropped {len(chunks) - len(selected_chunks)} chunks.")
                break
            selected_chunks.append(chunk)
            total_tokens += chunk_tokens
        
        return selected_chunks

    def _reorder_for_lost_in_the_middle(self, chunks: list[str]) -> list[str]:
        """
        The most important data — at the beginning and end of the list.
        """
        if len(chunks) <= 2:
            return chunks
            
        reordered = [None] * len(chunks)
        start_idx, end_idx = 0, len(chunks) - 1
        
        for i, chunk in enumerate(chunks):
            if i % 2 == 0:
                reordered[start_idx] = chunk
                start_idx += 1
            else:
                reordered[end_idx] = chunk
                end_idx -= 1
        return reordered