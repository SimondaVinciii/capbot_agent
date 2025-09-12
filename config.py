"""Configuration settings for the AI Agent system."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Main configuration class."""
    
    # Google AI Configuration
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "mssql+pyodbc://username:password@server/capbot_db?driver=ODBC+Driver+17+for+SQL+Server"
    )
    
    # ChromaDB Configuration
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./chroma_db")
    CHROMA_COLLECTION_NAME: str = os.getenv("CHROMA_COLLECTION_NAME", "topics_collection")
    
    # API Configuration
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.8"))
    TRENDING_API_URL: str = os.getenv("TRENDING_API_URL", "https://api.example.com/trending-topics")
    TRENDING_API_KEY: str = os.getenv("TRENDING_API_KEY", "")
    
    # Application Configuration
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # Embedding Configuration
    # Options: 'sentence' (SentenceTransformers) or 'google' (Google Generative AI embeddings)
    EMBEDDING_BACKEND: str = os.getenv("EMBEDDING_BACKEND", "sentence").lower()
    # For 'sentence': e.g., 'all-mpnet-base-v2' (768-dim)
    # For 'google': e.g., 'text-embedding-004' (768-dim)
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "all-mpnet-base-v2")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        required_fields = ["GOOGLE_API_KEY"]
        missing_fields = []
        
        for field in required_fields:
            if not getattr(cls, field):
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Missing required configuration: {', '.join(missing_fields)}")
        
        return True

# Global config instance
config = Config()

