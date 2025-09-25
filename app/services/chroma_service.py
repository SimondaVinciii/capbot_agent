"""ChromaDB service for vector similarity search."""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from config import config
import logging
import os

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None  # Optional if using Google backend

try:
    import google.generativeai as genai
except Exception:
    genai = None  # Optional if using SentenceTransformers backend

class ChromaService:
    """Service for managing ChromaDB operations."""
    
    def __init__(self):
        self.logger = logging.getLogger("chroma_service")
        self.collection_name = config.CHROMA_COLLECTION_NAME
        self.db_path = config.CHROMA_DB_PATH
        
        # Initialize ChromaDB client
        self._init_client()
        
        # Initialize embedding backend
        self.embedding_backend = config.EMBEDDING_BACKEND
        self.embedding_model_name = config.EMBEDDING_MODEL_NAME
        self._init_embedding_provider()
        
        # Get or create collection
        self.collection = self._get_or_create_collection()
    
    def _init_client(self):
        """Initialize ChromaDB client."""
        try:
            # Ensure directory exists
            os.makedirs(self.db_path, exist_ok=True)
            
            # Create persistent client
            self.client = chromadb.PersistentClient(
                path=self.db_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            self.logger.info(f"ChromaDB client initialized at {self.db_path}")
            
        except Exception as e:
            self.logger.error(f"Error initializing ChromaDB client: {e}")
            raise
    
    def _get_or_create_collection(self):
        """Get existing collection or create new one."""
        try:
            # Try to get existing collection
            collection = self.client.get_collection(name=self.collection_name)
            self.logger.info(f"Using existing collection: {self.collection_name}")
            return collection
            
        except Exception:
            # Create new collection if it doesn't exist
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Topics collection for similarity search"}
            )
            self.logger.info(f"Created new collection: {self.collection_name}")
            return collection

    def _init_embedding_provider(self):
        """Initialize the configured embedding provider."""
        try:
            if self.embedding_backend == "sentence":
                if SentenceTransformer is None:
                    raise RuntimeError("sentence-transformers is not installed")
                self.embedding_provider = "sentence"
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
                self.logger.info(f"Initialized SentenceTransformers model: {self.embedding_model_name}")
            elif self.embedding_backend == "google":
                if genai is None:
                    raise RuntimeError("google-generativeai is not installed")
                if not config.GOOGLE_API_KEY:
                    raise RuntimeError("GOOGLE_API_KEY is required for Google embedding backend")
                genai.configure(api_key=config.GOOGLE_API_KEY)
                self.embedding_provider = "google"
                self.embedding_model = self.embedding_model_name  # model id string for genai.embed_content
                self.logger.info(f"Initialized Google Embeddings model: {self.embedding_model_name}")
            else:
                raise ValueError(f"Unsupported EMBEDDING_BACKEND: {self.embedding_backend}")
        except Exception as e:
            self.logger.error(f"Error initializing embedding provider: {e}")
            raise
    
    def add_topic(self, topic_id: str, title: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """Add a topic to the collection.
        
        Args:
            topic_id: Unique identifier for the topic
            title: Topic title
            content: Full topic content for embedding
            metadata: Additional metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create embedding for the content
            embedding = self._create_embedding(content)
            
            # Prepare metadata
            doc_metadata = self._sanitize_metadata(metadata or {})
            doc_metadata.update({
                "title": title,
                "content_length": len(content)
            })
            
            # Add to collection
            self.collection.add(
                documents=[content],
                embeddings=[embedding.tolist()],
                metadatas=[doc_metadata],
                ids=[topic_id]
            )
            
            self.logger.debug(f"Added topic {topic_id} to collection")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding topic {topic_id}: {e}")
            return False
    
    def add_topics_batch(self, topics: List[Dict[str, Any]]) -> int:
        """Add multiple topics to the collection in batch.
        
        Args:
            topics: List of topic dictionaries with id, title, content, metadata
            
        Returns:
            Number of successfully added topics
        """
        if not topics:
            return 0
        
        try:
            # Prepare batch data
            ids = []
            documents = []
            embeddings = []
            metadatas = []
            
            for topic in topics:
                topic_id = str(topic["id"])
                content = topic["content"]
                title = topic["title"]
                metadata = self._sanitize_metadata(topic.get("metadata", {}))
                
                # Create embedding
                embedding = self._create_embedding(content)
                
                # Prepare metadata
                doc_metadata = metadata.copy()
                doc_metadata.update({
                    "title": title,
                    "content_length": len(content)
                })
                
                ids.append(topic_id)
                documents.append(content)
                embeddings.append(embedding.tolist())
                metadatas.append(doc_metadata)
            
            # Add batch to collection
            self.collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            self.logger.info(f"Added {len(topics)} topics to collection in batch")
            return len(topics)
            
        except Exception as e:
            self.logger.error(f"Error adding topics batch: {e}")
            return 0
    
    def search_similar_topics(
        self, 
        query_content: str, 
        n_results: int = 10, 
        similarity_threshold: float = None
    ) -> List[Dict[str, Any]]:
        """Search for similar topics based on content similarity.
        
        Args:
            query_content: Content to search for similar topics
            n_results: Maximum number of results to return
            similarity_threshold: Minimum similarity score (optional)
            
        Returns:
            List of similar topics with similarity scores
        """
        try:
            # Create embedding for query
            query_embedding = self._create_embedding(query_content)
            
            # Search collection
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            # Process results
            similar_topics = []
            for i in range(len(results["ids"][0])):
                topic_id = results["ids"][0][i]
                document = results["documents"][0][i]
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                
                # Convert distance to similarity score (cosine similarity)
                similarity_score = 1 - distance
                
                # Apply threshold if specified
                if similarity_threshold and similarity_score < similarity_threshold:
                    continue
                
                similar_topic = {
                    "id": topic_id,
                    "title": metadata.get("title", ""),
                    "content": document,
                    "similarity_score": similarity_score,
                    "metadata": metadata
                }
                similar_topics.append(similar_topic)
            
            self.logger.debug(f"Found {len(similar_topics)} similar topics")
            return similar_topics
            
        except Exception as e:
            self.logger.error(f"Error searching similar topics: {e}")
            return []
    
    def update_topic(self, topic_id: str, title: str = None, content: str = None, metadata: Dict[str, Any] = None) -> bool:
        """Update an existing topic in the collection.
        
        Args:
            topic_id: Topic ID to update
            title: New title (optional)
            content: New content (optional)
            metadata: New metadata (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare update data
            update_data = {}
            
            if content:
                # Create new embedding if content changed
                embedding = self._create_embedding(content)
                update_data["embeddings"] = [embedding.tolist()]
                update_data["documents"] = [content]
            
            if title or metadata:
                # Get current metadata
                current_results = self.collection.get(ids=[topic_id], include=["metadatas"])
                if current_results["metadatas"]:
                    current_metadata = current_results["metadatas"][0]
                else:
                    current_metadata = {}
                
                # Update metadata
                new_metadata = current_metadata.copy()
                if title:
                    new_metadata["title"] = title
                if metadata:
                    new_metadata.update(metadata)
                if content:
                    new_metadata["content_length"] = len(content)
                
                update_data["metadatas"] = [new_metadata]
            
            # Update in collection
            self.collection.update(
                ids=[topic_id],
                **update_data
            )
            
            self.logger.debug(f"Updated topic {topic_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating topic {topic_id}: {e}")
            return False
    
    def delete_topic(self, topic_id: str) -> bool:
        """Delete a topic from the collection.
        
        Args:
            topic_id: Topic ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.collection.delete(ids=[topic_id])
            self.logger.debug(f"Deleted topic {topic_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting topic {topic_id}: {e}")
            return False

    def upsert_topic(self, topic_id: str, title: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """Upsert a single topic into the collection (insert or update)."""
        try:
            embedding = self._create_embedding(content)
            doc_metadata = self._sanitize_metadata((metadata or {}).copy())
            doc_metadata.update({
                "title": title,
                "content_length": len(content)
            })
            if hasattr(self.collection, "upsert"):
                self.collection.upsert(
                    documents=[content],
                    embeddings=[embedding.tolist()],
                    metadatas=[doc_metadata],
                    ids=[topic_id]
                )
            else:
                # Fallback
                self.collection.add(
                    documents=[content],
                    embeddings=[embedding.tolist()],
                    metadatas=[doc_metadata],
                    ids=[topic_id]
                )
            self.logger.debug(f"Upserted topic {topic_id} into collection")
            return True
        except Exception as e:
            self.logger.error(f"Error upserting topic {topic_id}: {e}")
            return False

    def upsert_topics_batch(self, topics: List[Dict[str, Any]]) -> int:
        """Upsert multiple topics into the collection."""
        if not topics:
            return 0

    def list_items(
        self,
        limit: int = 20,
        offset: int = 0,
        include_documents: bool = False,
        include_embeddings: bool = False,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """List items from the collection with optional pagination and includes.
        
        Args:
            limit: Max number of items to return
            offset: Number of items to skip
            include_documents: Whether to include full documents
            include_embeddings: Whether to include embeddings (heavy)
            ids: Optional explicit list of ids to fetch
            where: Optional metadata filter
        
        Returns:
            Dict with ids, metadatas, and optionally documents/embeddings
        """
        try:
            includes: List[str] = ["metadatas"]
            if include_documents:
                includes.append("documents")
            if include_embeddings:
                includes.append("embeddings")

            results = self.collection.get(
                ids=ids,
                where=where,
                limit=limit,
                offset=offset,
                include=includes
            )
            return results
        except Exception as e:
            self.logger.error(f"Error listing collection items: {e}")
            return {"ids": [], "metadatas": [], "documents": [], "embeddings": []}
        try:
            ids: List[str] = []
            documents: List[str] = []
            embeddings: List[List[float]] = []
            metadatas: List[Dict[str, Any]] = []
            for topic in topics:
                topic_id = str(topic["id"])
                content = topic["content"]
                title = topic["title"]
                metadata = self._sanitize_metadata(topic.get("metadata", {}))
                embedding = self._create_embedding(content)
                doc_metadata = metadata.copy()
                doc_metadata.update({
                    "title": title,
                    "content_length": len(content)
                })
                ids.append(topic_id)
                documents.append(content)
                embeddings.append(embedding.tolist())
                metadatas.append(doc_metadata)

            if hasattr(self.collection, "upsert"):
                self.collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
            else:
                self.collection.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

            self.logger.info(f"Upserted {len(topics)} topics to collection in batch")
            return len(topics)
        except Exception as e:
            self.logger.error(f"Error upserting topics batch: {e}")
            return 0
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.collection.count()
            return {
                "total_topics": count,
                "collection_name": self.collection_name,
                "db_path": self.db_path
            }
        except Exception as e:
            self.logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}
    
    def reset_collection(self) -> bool:
        """Reset (clear) the entire collection.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete the collection
            self.client.delete_collection(name=self.collection_name)
            
            # Recreate the collection
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Topics collection for similarity search"}
            )
            
            self.logger.info(f"Reset collection: {self.collection_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error resetting collection: {e}")
            return False
    
    def _create_embedding(self, text: str) -> np.ndarray:
        """Create embedding for text using configured backend.
        
        Args:
            text: Text to create embedding for
            
        Returns:
            Numpy array containing the embedding
        """
        try:
            # Clean and normalize text
            text = text.strip()
            if not text:
                text = "empty"
            
            if self.embedding_provider == "sentence":
                embedding = self.embedding_model.encode(text, normalize_embeddings=True)
                return embedding
            elif self.embedding_provider == "google":
                # Use Google Embeddings API (text-embedding-004) which returns 768-dim
                result = genai.embed_content(model=self.embedding_model, content=text)
                values = result.get("embedding") or result.get("data", {}).get("embedding")
                if values is None:
                    raise RuntimeError("Google embedding response missing 'embedding'")
                embedding = np.array(values, dtype=np.float32)
                # Normalize to unit vector for cosine similarity
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm
                return embedding
            else:
                raise RuntimeError("Embedding provider not initialized")
            
        except Exception as e:
            self.logger.error(f"Error creating embedding: {e}")
            # Return zero embedding as fallback (use common 768 dim to fit both backends like all-mpnet-base-v2/text-embedding-004)
            return np.zeros(768, dtype=np.float32)
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        try:
            # Create embeddings
            embedding1 = self._create_embedding(text1)
            embedding2 = self._create_embedding(text2)
            
            # Calculate cosine similarity
            similarity = np.dot(embedding1, embedding2) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
            )
            
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"Error calculating similarity: {e}")
            return 0.0

    def upsert_topic(self, topic_id: str, title: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        try:
            embedding = self._create_embedding(content)
            doc_metadata = self._sanitize_metadata((metadata or {}).copy())
            doc_metadata.update({
                "title": title,
                "content_length": len(content)
            })
            if hasattr(self.collection, "upsert"):
                self.collection.upsert(
                    documents=[content],
                    embeddings=[embedding.tolist()],
                    metadatas=[doc_metadata],
                    ids=[topic_id]
                )
            else:
                # Fallback nếu bản Chroma không có upsert
                self.collection.add(
                    documents=[content],
                    embeddings=[embedding.tolist()],
                    metadatas=[doc_metadata],
                    ids=[topic_id]
                )
            self.logger.debug(f"Upserted topic {topic_id} into collection")
            return True
        except Exception as e:
            self.logger.error(f"Error upserting topic {topic_id}: {e}")
            return False

    def upsert_topics_batch(self, topics: List[Dict[str, Any]]) -> int:
        if not topics:
            return 0
        try:
            ids, documents, embeddings, metadatas = [], [], [], []
            for topic in topics:
                topic_id = str(topic["id"])
                content = topic["content"]
                title = topic["title"]
                metadata = self._sanitize_metadata(topic.get("metadata", {}))
                embedding = self._create_embedding(content)
                doc_metadata = metadata.copy()
                doc_metadata.update({
                    "title": title,
                    "content_length": len(content)
                })
                ids.append(topic_id)
                documents.append(content)
                embeddings.append(embedding.tolist())
                metadatas.append(doc_metadata)

            if hasattr(self.collection, "upsert"):
                self.collection.upsert(
                    ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
                )
            else:
                self.collection.add(
                    ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
                )

            self.logger.info(f"Upserted {len(topics)} topics to collection in batch")
            return len(topics)
        except Exception as e:
            self.logger.error(f"Error upserting topics batch: {e}")
            return 0

    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure metadata contains only Chroma-supported primitive values.
        - Drop keys with None values
        - Convert non-primitive values to strings
        """
        sanitized: Dict[str, Any] = {}
        for key, value in (metadata or {}).items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            else:
                try:
                    sanitized[key] = str(value)
                except Exception:
                    # As a last resort, skip if cannot stringify
                    continue
        return sanitized

