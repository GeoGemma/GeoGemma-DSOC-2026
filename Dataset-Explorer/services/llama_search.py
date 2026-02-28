"""
Enhanced search implementation for GEE Catalog using LlamaIndex
This module provides search services using LlamaIndex and transformers models
"""
import os
import logging
import torch
from typing import List, Dict, Any, Optional, Union
import numpy as np

logger = logging.getLogger(__name__)

# Check for available hardware
def get_device():
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch, 'mps') and torch.backends.mps.is_available():
        return "mps"
    else:
        return "cpu"

# Global device setting
DEVICE = get_device()
logger.info(f"Using device: {DEVICE}")

class EnhancedDatasetSearch:
    """
    Enhanced search functionality for GEE datasets using LlamaIndex
    with weighted multi-field search and easy model switching.
    """
    
    def __init__(
        self,
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        llm_model_name: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        cache_dir: str = "saved_indexes"
    ):
        """
        Initialize the enhanced search with specified models.
        
        Args:
            embedding_model_name: HuggingFace embedding model to use
            llm_model_name: HuggingFace language model to use
            cache_dir: Directory to save/load vector indexes
        """
        self.embedding_model_name = embedding_model_name
        self.llm_model_name = llm_model_name
        self.cache_dir = cache_dir
        self.datasets = []

        
        # LlamaIndex components (initialized lazily)
        self.index = None
        self.embedding_model = None
        self.llm = None
        
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
        
        # Field weights for search
        self.weights = {
            "title": 0.35,
            "id": 0.15,
            "description": 0.30,
            "keywords": 0.20
        }
        
        logger.info(f"Initialized EnhancedDatasetSearch with embedding model: {embedding_model_name}")
        logger.info(f"Using LLM model: {llm_model_name}")

    def _init_models(self):
        """Initialize the embedding model and LLM"""
        try:
            # Import here to avoid loading dependencies unnecessarily
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
            from llama_index.llms.huggingface import HuggingFaceLLM
            from llama_index.core import Settings
            
            if self.embedding_model is None:
                logger.info(f"Initializing embedding model: {self.embedding_model_name}")
                self.embedding_model = HuggingFaceEmbedding(
                    model_name=self.embedding_model_name,
                    device=DEVICE
                )
                # Update global settings
                Settings.embed_model = self.embedding_model
            
            if self.llm is None and self.llm_model_name is not None:
                logger.info(f"Initializing LLM: {self.llm_model_name}")
                self.llm = HuggingFaceLLM(
                    model_name=self.llm_model_name,
                    context_window=512,
                    max_new_tokens=256,
                    tokenizer_name=self.llm_model_name,
                    generate_kwargs={"temperature": 0.1, "do_sample": False},
                    device_map=DEVICE
                )
                # Update global settings
                Settings.llm = self.llm
                
            # Set additional settings
            Settings.chunk_size = 512
                
        except ImportError as e:
            logger.error(f"Failed to initialize LlamaIndex models: {str(e)}")
            logger.error("Please install llama-index and its dependencies")
            raise
    
    def change_models(
        self, 
        embedding_model_name: Optional[str] = None,
        llm_model_name: Optional[str] = None
    ):
        """
        Change the embedding model and/or LLM model.
        
        Args:
            embedding_model_name: New embedding model name (HuggingFace)
            llm_model_name: New LLM model name (HuggingFace)
        """
        if embedding_model_name:
            logger.info(f"Changing embedding model to: {embedding_model_name}")
            self.embedding_model_name = embedding_model_name
            self.embedding_model = None  # Reset so it will be initialized on next use
            self.index = None  # Reset index since embeddings will change
        
        if llm_model_name:
            logger.info(f"Changing LLM to: {llm_model_name}")
            self.llm_model_name = llm_model_name
            self.llm = None  # Reset so it will be initialized on next use
    
    def _prepare_dataset_nodes(self, datasets: Dict[str, Dict[Any, Any]]) -> List:
        """
        Convert dataset dictionaries to TextNode objects with appropriate metadata.
        
        Args:
            datasets: Dictionary of dataset dictionaries
            
        Returns:
            List of TextNode objects
        """
        from llama_index.core.schema import TextNode
        
        nodes = []
        
        for i, (dataset_key, dataset) in enumerate(datasets.items()):
            # Extract key information
            title = dataset.get('title', '')
            dataset_id = dataset.get('id', '')
            description = dataset.get('description', '')
            
            # Extract keywords from various locations in the dataset
            keywords = []
            
            # From summaries
            if 'summaries' in dataset:
                summaries = dataset['summaries']
                if 'keywords' in summaries and isinstance(summaries.get('keywords', []), list):
                    keywords.extend(summaries.get('keywords', []))
                if 'gee:terms' in summaries and isinstance(summaries.get('gee:terms', []), list):
                    keywords.extend(summaries.get('gee:terms', []))
                    
            # From properties
            if 'properties' in dataset:
                props = dataset['properties']
                if 'keywords' in props:
                    if isinstance(props['keywords'], list):
                        keywords.extend(props['keywords'])
                    elif isinstance(props['keywords'], str):
                        keywords.extend([k.strip() for k in props['keywords'].split(',')])
            
            # Get dataset type
            gee_type = dataset.get('gee:type', '')
            
            # Format keywords
            keywords_text = ", ".join(keywords) if keywords else ""
            
            # Create a text representation with field labels
            node_text = (
                f"TITLE: {title}\n"
                f"ID: {dataset_id}\n"
                f"TYPE: {gee_type}\n"
                f"KEYWORDS: {keywords_text}\n"
                f"DESCRIPTION: {description}\n"
            )
            
            # Create node with metadata
            node = TextNode(
                text=node_text,
                metadata={
                    "title": title,
                    "id": dataset_id,
                    "description": description,
                    "keywords": keywords_text,
                    "gee_type": gee_type,
                    "dataset_key": dataset_key,  # Store original key
                    "dataset_index": i  # Store original index for retrieval
                }
            )
            nodes.append(node)
        
        logger.info(f"Created {len(nodes)} dataset nodes for LlamaIndex")
        return nodes


    def build_index(self, datasets: Dict[str, Dict[Any, Any]]):
        """
        Build vector index from the datasets.
        
        Args:
            datasets: Dictionary of dataset dictionaries
        """
        from llama_index.core import VectorStoreIndex, Settings, StorageContext
        from llama_index.core import load_index_from_storage
        
        self._init_models()
        self.datasets = datasets
        
        # Create a unique cache directory for this model
        model_cache_dir = os.path.join(
            self.cache_dir, 
            f"{self.embedding_model_name.replace('/', '_')}_index"
        )
        
        # Check if we have a cached index
        if os.path.exists(model_cache_dir) and os.path.isdir(model_cache_dir):
            logger.info(f"Loading cached index from {model_cache_dir}")
            try:
                # Load index from storage
                storage_context = StorageContext.from_defaults(persist_dir=model_cache_dir)
                self.index = load_index_from_storage(storage_context)
                return self.index
            except Exception as e:
                logger.warning(f"Error loading cached index: {str(e)}. Building new index.")
        
        # Create nodes from datasets
        nodes = self._prepare_dataset_nodes(datasets)
        
        # Build the index with storage context for saving
        logger.info("Building vector index...")
        storage_context = StorageContext.from_defaults()
        self.index = VectorStoreIndex(nodes, storage_context=storage_context)
        
        # Cache the index
        logger.info(f"Caching index to {model_cache_dir}")
        storage_context.persist(persist_dir=model_cache_dir)
        
        return self.index


    def update_weights(self, new_weights: Dict[str, float]):
        """
        Update the field weights for search.
        
        Args:
            new_weights: Dictionary of field names to weights
        """
        # Validate weights
        total = sum(new_weights.values())
        if abs(total - 1.0) > 0.01:
            logger.warning(f"Weights don't sum to 1.0 (sum = {total}). Normalizing.")
            # Normalize weights
            for key in new_weights:
                new_weights[key] /= total
        
        self.weights = new_weights
        logger.info(f"Updated search weights: {self.weights}")
    
    def expand_query(self, query: str) -> str:
        """
        Use the LLM to expand the query for better search.
        
        Args:
            query: Original user query
            
        Returns:
            Expanded query string
        """
        # Skip expansion if no LLM is set or if query is very short
        if self.llm is None or len(query.split()) <= 2:
            return query
            
        prompt = f"""
        Your task is to expand the following search query for an Earth Engine geospatial dataset search.
        The expanded query should include relevant keywords, alternatives, and specific Earth observation terms.
        Keep the expansion concise (max 3-4 additional terms).
        
        Original query: "{query}"
        
        Expanded query:
        """
        
        try:
            self._init_models()
            # Get response from LLM
            response = self.llm.complete(prompt)
            expanded = response.text.strip()
            
            # If expansion looks reasonable, use it
            if expanded and len(expanded) < 200 and len(expanded) > len(query):
                logger.info(f"Expanded query: {query} -> {expanded}")
                return expanded
            else:
                return query
        except Exception as e:
            logger.warning(f"Query expansion failed: {e}")
            return query
    
    def search(self, query: str, top_k: int = 20, use_reranking: bool = True, expand_query: bool = True) -> List[Dict[Any, Any]]:
        """
        Search for datasets matching the query.
        
        Args:
            query: Search query
            top_k: Number of results to return
            use_reranking: Whether to use field-weighted reranking
            expand_query: Whether to use LLM for query expansion
            
        Returns:
            List of matched datasets with similarity scores
        """
        if self.index is None and self.datasets:
            self.build_index(self.datasets)
            
        if self.index is None:
            raise ValueError("Index not built yet. Call build_index first.")
        
        self._init_models()
        
        from llama_index.core.retrievers import VectorIndexRetriever
        
        # Step 1: Optionally expand the query
        if expand_query and self.llm is not None:
            search_query = self.expand_query(query)
        else:
            search_query = query
        
        # Step 2: Set up retriever for initial search
        retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=min(top_k * 3, 60)  # Get more results than needed for reranking
        )
        
        # Step 3: Execute search
        nodes = retriever.retrieve(search_query)
        logger.info(f"Retrieved {len(nodes)} nodes for query: {search_query}")
        
        # Step 4: Optionally apply weighted field reranking
        if use_reranking and len(nodes) > 0:
            # Get query embedding
            query_embedding = self.embedding_model.get_text_embedding(query)
            
            # Score each result by weighted field similarity
            scored_results = []
            for node in nodes:
                # Get key from metadata
                dataset_key = node.metadata.get("dataset_key")
                if dataset_key is None or dataset_key not in self.datasets:
                    continue
                    
                # Get the actual dataset
                dataset = self.datasets[dataset_key]
                    
                # Get field embeddings and calculate weighted score
                weighted_score = 0.0
                for field, weight in self.weights.items():
                    field_content = node.metadata.get(field, "")
                    if field_content:
                        # Get embedding for this field
                        field_embed = self.embedding_model.get_text_embedding(field_content)
                        
                        # Calculate cosine similarity
                        dot_product = np.dot(query_embedding, field_embed)
                        magnitude = np.linalg.norm(query_embedding) * np.linalg.norm(field_embed)
                        
                        if magnitude > 0:
                            similarity = dot_product / magnitude
                            weighted_score += similarity * weight
                
                # Add to scored results
                scored_results.append((dataset_key, weighted_score, dataset))
            
            # Sort by score (descending)
            sorted_results = sorted(scored_results, key=lambda x: x[1], reverse=True)
            
            # Get final results
            search_results = []
            seen_ids = set()
            for key, score, dataset in sorted_results[:top_k]:
                # Get original dataset
                dataset_copy = dataset.copy()
                
                # Skip duplicates
                dataset_id = dataset_copy['id']
                if dataset_id in seen_ids:
                    continue
                    
                # Add similarity score
                dataset_copy['similarity_score'] = float(score)
                search_results.append(dataset_copy)
                seen_ids.add(dataset_id)
                
                # Stop when we have enough results
                if len(search_results) >= top_k:
                    break
        else:
            # Without reranking, just use the original node scores
            search_results = []
            seen_ids = set()
            for node in nodes:
                dataset_key = node.metadata.get("dataset_key")
                if dataset_key is None or dataset_key not in self.datasets:
                    continue
                    
                # Get original dataset and add similarity score
                dataset = self.datasets[dataset_key].copy()
                
                # Skip duplicates
                dataset_id = dataset['id']
                if dataset_id in seen_ids:
                    continue
                    
                dataset['similarity_score'] = float(node.score) if hasattr(node, 'score') else 1.0
                search_results.append(dataset)
                seen_ids.add(dataset_id)
                
                # Stop when we have enough results
                if len(search_results) >= top_k:
                    break
        
        logger.info(f"Returning {len(search_results)} search results")
        return search_results


# Create function to easily integrate with existing code
def create_enhanced_search_manager(datasets, model_size="small"):
    """
    Factory function to create an EnhancedDatasetSearch instance
    with appropriate models based on desired size.
    
    Args:
        datasets: Dictionary of dataset dictionaries
        model_size: Size of models to use ("small", "medium", "large", "minimal")
        
    Returns:
        Initialized EnhancedDatasetSearch with built index
    """
    if model_size == "small":
        # ~100MB models
        embedding_model = "sentence-transformers/all-MiniLM-L6-v2"  # Faster alternative (~90MB)
        llm_model = "sentence-transformers/all-MiniLM-L6-v2"
    elif model_size == "medium":
        # ~500MB models
        embedding_model = "BAAI/bge-base-en-v1.5"
        llm_model = "microsoft/phi-2"
    elif model_size == "large":
        # ~2-7GB models
        embedding_model = "BAAI/bge-large-en-v1.5"
        llm_model = "google/gemma-2b-it"
    elif model_size == "minimal":
        # Smallest possible option (~60MB total)
        embedding_model = "sentence-transformers/paraphrase-MiniLM-L3-v2"
        llm_model = None  # No LLM for query expansion
    else:
        raise ValueError(f"Unknown model size: {model_size}")
    
    search_manager = EnhancedDatasetSearch(
        embedding_model_name=embedding_model,
        llm_model_name=llm_model
    )
    
    # Build index
    search_manager.build_index(datasets)
    return search_manager