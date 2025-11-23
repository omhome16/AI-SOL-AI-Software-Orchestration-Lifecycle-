"""
ProjectContextStore - Vector database for RAG-powered contextual responses
Uses Chroma DB to store and retrieve project documents for intelligent Q&A.
"""

import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb import EmbeddingFunction, Documents, Embeddings
from chromadb.config import Settings
from backend.core.config import Config
import google.generativeai as genai

logger = logging.getLogger(__name__)


class GoogleGenAIEmbeddingFunction(EmbeddingFunction):
    """Embedding function for Chroma using Google GenAI"""
    
    def __init__(self):
        self.__name__ = "GoogleGenAIEmbeddingFunction"
        self.name = "GoogleGenAIEmbeddingFunction"
        self.max_retries = 3
        try:
            genai.configure(api_key=Config.GOOGLE_API_KEY)
            logger.info("Google GenAI configured successfully for embeddings")
        except Exception as e:
            logger.error(f"Failed to configure GenAI: {e}")
            raise
        
    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        
        for text in input:
            embedding = self._embed_with_retry(text)
            embeddings.append(embedding if embedding else [])
        
        return embeddings
    
    def _embed_with_retry(self, text: str) -> list:
        """Embed text with exponential backoff retry logic"""
        import time
        
        for attempt in range(self.max_retries):
            try:
                result = genai.embed_content(
                    model="models/embedding-001",
                    content=text,
                    task_type="retrieval_document"
                )
                
                if 'embedding' in result and result['embedding']:
                    # Validate embedding
                    embedding = result['embedding']
                    if isinstance(embedding, list) and len(embedding) > 0:
                        logger.debug(f"Successfully embedded text (length={len(embedding)})")
                        return embedding
                    else:
                        logger.warning(f"Invalid embedding format: {type(embedding)}")
                else:
                    logger.warning(f"No embedding in result for text: {text[:50]}...")
                
            except Exception as e:
                logger.error(f"Embedding attempt {attempt + 1}/{self.max_retries} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {self.max_retries} embedding attempts failed for: {text[:50]}...")
        
        # Return empty list if all retries failed
        return []


class ProjectContextStore:
    """
    Manages vector storage of project documents using Chroma DB.
    Enables semantic search for context-aware AI responses.
    """
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize the context store with Chroma DB.
        
        Args:
            persist_directory: Path to store Chroma database
        """
        self.persist_directory = persist_directory
        
        # Initialize Chroma client with persistence FIRST
        try:
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            logger.info(f"Chroma client initialized at {persist_directory}")
        except Exception as e:
            logger.error(f"Failed to initialize Chroma client: {e}")
            self.client = None
        
        # Initialize Google embeddings as singleton
        try:
            self._embedding_function = GoogleGenAIEmbeddingFunction()
            logger.info("GoogleGenAIEmbeddingFunction initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            self._embedding_function = None
    
    def get_collection(self, project_id: str):
        """
        Get or create a Chroma collection for a specific project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Chroma collection instance
        """
        if not self.client:
            raise Exception("Chroma client not initialized")
        
        collection_name = f"project_{project_id.replace('-', '_')}"
        
        try:
            collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self._embedding_function,
                metadata={"project_id": project_id}
            )
            return collection
        except Exception as e:
            logger.error(f"Failed to get/create collection for {project_id}: {e}")
            raise
    
    def add_document(
        self,
        project_id: str,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a document to the project's vector store.
        
        Args:
            project_id: Project identifier
            doc_id: Unique document identifier
            content: Document content to embed
            metadata: Optional metadata (filename, doc_type, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        if not content or not content.strip():
            logger.warning(f"Empty content for doc_id: {doc_id}")
            return False
        
        try:
            collection = self.get_collection(project_id)
            
            # Prepare metadata
            meta = metadata or {}
            meta["project_id"] = project_id
            
            # Add to collection
            collection.add(
                ids=[doc_id],
                documents=[content],
                metadatas=[meta]
            )
            
            logger.info(f"Added document {doc_id} to project {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add document {doc_id}: {e}")
            return False
    
    def query(
        self,
        project_id: str,
        query_text: str,
        n_results: int = 3,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query the vector store for similar documents.
        
        Args:
            project_id: Project identifier
            query_text: Query string
            n_results: Number of results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            Dict with 'documents', 'metadatas', 'distances', 'ids'
        """
        try:
            collection = self.get_collection(project_id)
            
            # Query with optional filtering
            results = collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=filter_metadata if filter_metadata else None
            )
            
            logger.info(f"Query for '{query_text[:50]}...' returned {len(results['ids'][0])} results")
            
            return {
                "documents": results['documents'][0] if results['documents'] else [],
                "metadatas": results['metadatas'][0] if results['metadatas'] else [],
                "distances": results['distances'][0] if results['distances'] else [],
                "ids": results['ids'][0] if results['ids'] else []
            }
            
        except Exception as e:
            logger.error(f"Failed to query project {project_id}: {e}")
            return {
                "documents": [],
                "metadatas": [],
                "distances": [],
                "ids": []
            }
    
    def get_all_documents(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get all documents for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of document dicts with 'id', 'content', 'metadata'
        """
        try:
            collection = self.get_collection(project_id)
            results = collection.get()
            
            documents = []
            for i, doc_id in enumerate(results['ids']):
                documents.append({
                    "id": doc_id,
                    "content": results['documents'][i],
                    "metadata": results['metadatas'][i]
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Failed to get all documents for {project_id}: {e}")
            return []
    
    def delete_document(self, project_id: str, doc_id: str) -> bool:
        """
        Delete a specific document from the vector store.
        
        Args:
            project_id: Project identifier
            doc_id: Document identifier to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            collection = self.get_collection(project_id)
            collection.delete(ids=[doc_id])
            logger.info(f"Deleted document {doc_id} from project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False
    
    def clear_project(self, project_id: str) -> bool:
        """
        Clear all documents for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            collection_name = f"project_{project_id.replace('-', '_')}"
            self.client.delete_collection(name=collection_name)
            logger.info(f"Cleared all documents for project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear project {project_id}: {e}")
            return False
    
    def get_stats(self, project_id: str) -> Dict[str, Any]:
        """
        Get statistics about the project's vector store.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Dict with 'total_documents', 'doc_types', 'latest_update'
        """
        try:
            collection = self.get_collection(project_id)
            results = collection.get()
            
            doc_types = {}
            for metadata in results['metadatas']:
                doc_type = metadata.get('doc_type', 'unknown')
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            
            return {
                "total_documents": len(results['ids']),
                "doc_types": doc_types,
                "collection_name": f"project_{project_id.replace('-', '_')}"
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for {project_id}: {e}")
            return {
                "total_documents": 0,
                "doc_types": {},
                "error": str(e)
            }
