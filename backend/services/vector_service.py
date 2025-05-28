import json
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Tuple

from models.embedding import Embedding
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
        model: str = "neural-chat",
        limit: int = 5
    ) -> List[Tuple[int, float]]:
        """Find similar entities based on vector similarity"""
        try:
            # Get embedding for query text
            response = await self.ollama_client.generate(
                model=model,
                prompt=text,
                options={"embedding": True}
            )
            
            # Parse response
            embedding_data = json.loads(response.text)
            if not embedding_data.get("embedding"):
                return []
            
            # Convert to vector format
            query_vector = f"[{','.join(map(str, embedding_data['embedding']))}]"
            
            # Query similar vectors
            result = self.db.execute(
                text("""
                    SELECT entity_id, 1 - (embedding_vector <=> :query_vector) as similarity
                    FROM embeddings
                    WHERE entity_type = :entity_type
                    AND model = :model
                    ORDER BY similarity DESC
                    LIMIT :limit
                """),
                {
                    "query_vector": query_vector,
                    "entity_type": entity_type,
                    "model": model,
                    "limit": limit
                }
            )
            
            # Return list of (entity_id, similarity) tuples
            return [(row[0], float(row[1])) for row in result]
            
        except Exception as e:
            print(f"Error finding similar entities: {str(e)}")
            return []

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