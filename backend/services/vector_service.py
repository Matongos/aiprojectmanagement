import json
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Tuple

from models.embedding import Embedding
from models.vector_embedding import VectorEmbedding
from services.ollama_service import get_ollama_client

class VectorService:
    def __init__(self, db: Session):
        self.db = db
        self.ollama_client = get_ollama_client()

    async def create_embedding(
        self,
        text: str,
        entity_type: str,
        entity_id: int,
        model: str = "neural-chat"
    ) -> Optional[Embedding]:
        """Create an embedding for the given text"""
        try:
            # Get embedding from Ollama
            response = await self.ollama_client.generate(
                model=model,
                prompt=text,
                options={"embedding": True}
            )
            
            # Parse response
            embedding_data = json.loads(response.text)
            if not embedding_data.get("embedding"):
                return None
            
            # Create embedding record
            embedding = Embedding(
                entity_type=entity_type,
                entity_id=entity_id,
                embedding=json.dumps(embedding_data["embedding"]),
                embedding_vector=f"[{','.join(map(str, embedding_data['embedding']))}]",
                model=model
            )
            
            self.db.add(embedding)
            self.db.commit()
            self.db.refresh(embedding)
            
            return embedding
            
        except Exception as e:
            print(f"Error creating embedding: {str(e)}")
            return None

    async def find_similar(
        self,
        text: str,
        entity_type: str,
        limit: int = 5,
        threshold: float = 0.7
    ) -> List[Tuple[int, float]]:
        """Find similar items based on text similarity"""
        try:
            # Get embedding for the query text
            query_embedding = await self._get_embedding(text)
            if not query_embedding:
                return []

            # Get all embeddings of the specified type
            embeddings = self.db.query(VectorEmbedding).filter(
                VectorEmbedding.entity_type == entity_type
            ).all()

            if not embeddings:
                return []

            # Calculate similarities
            similarities = []
            for emb in embeddings:
                similarity = self._cosine_similarity(
                    query_embedding,
                    emb.embedding
                )
                if similarity >= threshold:
                    similarities.append((emb.entity_id, similarity))

            # Sort by similarity and return top matches
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:limit]

        except Exception as e:
            print(f"Error finding similar items: {str(e)}")
            return []

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding vector for text using Ollama"""
        try:
            response = await self.ollama_client.generate(
                prompt=text,
                model="llama2",
                options={"embedding": True}
            )
            
            if isinstance(response, dict) and "embedding" in response:
                return response["embedding"]
            return None

        except Exception as e:
            print(f"Error getting embedding: {str(e)}")
            return None

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            v1 = np.array(vec1)
            v2 = np.array(vec2)
            return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
        except Exception as e:
            print(f"Error calculating similarity: {str(e)}")
            return 0.0

    def delete_embeddings(self, entity_type: str, entity_id: int) -> bool:
        """Delete embeddings for an entity"""
        try:
            self.db.query(Embedding).filter(
                Embedding.entity_type == entity_type,
                Embedding.entity_id == entity_id
            ).delete()
            self.db.commit()
            return True
        except Exception as e:
            print(f"Error deleting embeddings: {str(e)}")
            return False 