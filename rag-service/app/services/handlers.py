import json
from redis.asyncio import Redis

from app.core.config import settings
from app.core.logger import logger
from app.core.db import AsyncSessionLocal
from app.models.chunk import DocumentChunk
from app.services.embedding_service import embedding_service
from app.services.llm_service import llm_service
from app.services.s3_service import S3Service       
from app.core.s3 import get_s3_client               
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.archive_repository import ArchiveRepository
from app.core.redis_client import get_redis_client


async def handle_index_command(data: dict):
    """
    Handles the "index" command: fetches file metadata from DB, 
    downloads files from S3, generates chunks, and saves to DB.
    """
    correlation_id = data.get("correlation_id", "UNKNOWN")
    archive_id = data.get("archive_id")
    
    req_logger = logger.bind(correlation_id=correlation_id)
    
    if not archive_id:
        req_logger.error("Missing 'archive_id' in payload. Aborting.")
        return

    req_logger.info(f"Starting indexing for archive '{archive_id}' via MinIO")

    try:
        async with AsyncSessionLocal() as session:
            extracted_files = await ArchiveRepository.get_extracted_files(session, archive_id)

        if not extracted_files:
            req_logger.warning(f"No extracted files found for archive '{archive_id}' in DB.")
            return

        total_chunks_saved = 0
        async with get_s3_client() as s3_client:
            s3_svc = S3Service(s3_client)

            for file_info in extracted_files:
                filename = file_info.get("file_name")
                s3_key = file_info.get("s3_object_name")
                            
                try:
                    text_content = await s3_svc.get_text_file(s3_key)
                except Exception as e:
                    req_logger.warning(f"Skipping '{filename}' due to S3 error: {e}")
                    continue

                if not text_content or not text_content.strip():
                    req_logger.warning(f"Skipping '{filename}': File is empty.")
                    continue

                req_logger.info(f"Successfully downloaded '{filename}'. Generating embeddings...")
                
                processed_chunks = await embedding_service.generate_chunks_and_embeddings(text_content)
                if not processed_chunks:
                    continue

                db_chunks = [
                    DocumentChunk(
                        archive_id=archive_id,
                        filename=filename, 
                        chunk_text=item["chunk_text"],
                        embedding=item["embedding"]
                    )
                    for item in processed_chunks
                ]
                
                async with AsyncSessionLocal() as save_session:
                    await ChunkRepository.save_chunks(save_session, db_chunks)
                
                total_chunks_saved += len(db_chunks)

        req_logger.info(f"Successfully indexed archive! Total vectorized chunks saved: {total_chunks_saved}")

    except Exception as e:
        req_logger.error(f"Failed to index archive {archive_id}: {e}", exc_info=True)


async def handle_search_request(data: dict):
    """
    Handles the "search" command: refines the query, generates its embedding, 
    performs a GLOBAL search for similar chunks in the DB, and generates an answer.
    """
    correlation_id = data.get("correlation_id", "UNKNOWN")
    query = data.get("query")
    top_k = data.get("top_k", 10) 

    req_logger = logger.bind(correlation_id=correlation_id)

    if not query:
        req_logger.error("Missing 'query' in payload. Aborting search.")
        return

    req_logger.info(f"Starting global vector search for raw query: '{query}' (top_k={top_k})")

    try:
        refined_query = await llm_service.refine_query(query)

        query_embedding = await embedding_service.embeddings_client.aembed_query(refined_query)
        
        async with AsyncSessionLocal() as session:
            db_chunks = await ChunkRepository.search_similar_chunks(
                session=session,
                query_embedding=query_embedding,
                limit=top_k 
            )
            
        chunk_texts = [chunk.chunk_text for chunk in db_chunks]
        req_logger.info(f"Found {len(chunk_texts)} relevant chunks across the DB for refined query '{refined_query}'.")
        
        answer = await llm_service.generate_answer(query, chunk_texts)

        response_payload = {
            "correlation_id": correlation_id,
            "query": query,
            "answer": answer
        }

        redis_client = get_redis_client()
        await redis_client.publish(f"rag_responses:{correlation_id}", json.dumps(response_payload))

        req_logger.info("Answer successfully generated and published back to Redis!")

    except Exception as e:
        req_logger.error(f"Error during search processing: {e}", exc_info=True)
        
        error_payload = {
            "correlation_id": correlation_id,
            "query": query,
            "answer": "An internal error occurred during the search. Please try again later."
        }
        
        redis_client = get_redis_client()
        await redis_client.publish(f"rag_responses:{correlation_id}", json.dumps(error_payload))