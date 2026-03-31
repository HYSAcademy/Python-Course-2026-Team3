from tenacity import retry, stop_after_attempt, wait_exponential
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import settings
from app.core.logger import logger
from app.services.context_processor import ContextProcessor

class LLMService:
    def __init__(self):
        model_name = getattr(settings, "llm_model_name", "gpt-4o-mini")
        self._llm = ChatOpenAI(
            model=model_name,
            api_key=settings.openai_api_key.get_secret_value(),
            temperature=0.3,
            max_retries=0 
        )
        self._context_processor = ContextProcessor(model_name=model_name)
        
        self._prompt_template = self._init_prompt_template()
        
        self._query_rewrite_prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are an expert search query optimizer for a vector database. "
                "Your task is to take a conversational user input and extract ONLY the core search intent. "
                "Remove all polite filler words, greetings, and unnecessary context. "
                "Fix any obvious typos. "
                "Translate the core intent into clear keywords. "
                "Respond ONLY with the optimized search query string, nothing else. "
                "Do not use quotes or introductory phrases."
            )),
            ("user", "{raw_query}")
        ])

    def _init_prompt_template(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", (
                "You are a professional and helpful AI assistant. "
                "Your task is to answer the user's question based EXCLUSIVELY on the provided context. "
                "If the context does not contain the information needed to answer, truthfully state: "
                "'Unfortunately, I could not find the answer to this question in the provided documents.' "
            )),
            ("user", "Context:\n{context}\n\nQuestion: {query}")
        ])

    async def refine_query(self, raw_query: str) -> str:
        """Cleans and optimizes the raw user query for better semantic vector search."""
        try:
            chain = self._query_rewrite_prompt | self._llm
            response = await chain.ainvoke({"raw_query": raw_query})
            clean_query = response.content.strip()
            
            logger.info(f"Query Refined: '{raw_query}' -> '{clean_query}'")
            return clean_query
        except Exception as e:
            logger.error(f"Failed to refine query, using original. Error: {e}", exc_info=True)
            return raw_query

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def _call_openai_api(self, context: str, query: str) -> str:
        """Calls the OpenAI API with retry logic."""
        chain = self._prompt_template | self._llm
        response = await chain.ainvoke({"context": context, "query": query})
        return response.content

    async def generate_answer(self, query: str, chunks: list[str]) -> dict:
        """Main method to generate answer based on query and context chunks"""
        if not chunks:
            return {"answer": "Unfortunately, I could not find any information in the archive.", "contexts": []}

        context_text, used_chunks = self._context_processor.prepare_context(chunks)
        
        logger.info(f"Generating answer. Context size: {self._context_processor.count_tokens(context_text)} tokens.")

        try:
            answer = await self._call_openai_api(context_text, query)
            logger.info("Answer successfully generated.")
            return {
                "answer": answer,
                "contexts": used_chunks
            } 
            
        except Exception as e:
            logger.error(f"Critical error in LLM Service: {e}", exc_info=True)
            return {
                "answer": "An internal error occurred. Please try again later.",
                "contexts": used_chunks
            }

llm_service = LLMService()