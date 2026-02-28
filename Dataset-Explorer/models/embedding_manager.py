import os
import pickle
import json
import logging

# Import our enhanced search module
from services.llama_search import EnhancedDatasetSearch, create_enhanced_search_manager

logger = logging.getLogger(__name__)

class DatasetEmbeddingManager:
    """Manages dataset embeddings for similarity search using LlamaIndex capabilities"""
    
    def __init__(self, model_size="small"):
        """
        Initialize the DatasetEmbeddingManager with specified model size.
        
        Args:
            model_size (str): Size of the models to use ("small", "medium", or "large")
        """
        self.model_size = model_size
        
        # Enhanced search attributes
        self.enhanced_search = None
        
        # Dataset storage
        self.datasets = None
        
        logger.info(f"Using LlamaIndex search with {model_size} models")

    def load_datasets(self, datasets_file_path):
        """
        Load datasets from the specified file path and initialize the search index.
        
        Args:
            datasets_file_path (str): Path to the pickled datasets file
            
        Returns:
            bool: True if successful
            
        Raises:
            Exception: If loading fails
        """
        logger.info(f"Loading datasets from {datasets_file_path}")
        
        try:
            with open(datasets_file_path, 'rb') as f:
                self.datasets = pickle.load(f)
            logger.info(f"Successfully loaded {len(self.datasets)} datasets")
            
            # Initialize the enhanced search
            logger.info("Initializing enhanced search with loaded datasets...")
            self.enhanced_search = create_enhanced_search_manager(
                self.datasets, 
                model_size=self.model_size
            )
            logger.info("Enhanced search index built successfully from loaded datasets")
            return True
        except Exception as e:
            logger.error(f"Error loading datasets: {str(e)}")
            raise

    def load_state(self, embeddings_file_path, faiss_index_file_path, datasets_file_path):
        """
        Legacy method - now just loads datasets and ignores other parameters.
        This is kept for backward compatibility.
        
        Args:
            embeddings_file_path (str): Ignored
            faiss_index_file_path (str): Ignored
            datasets_file_path (str): Path to the pickled datasets file
            
        Returns:
            bool: Result from load_datasets
        """
        logger.info("Note: Using legacy load_state method, consider switching to load_datasets")
        return self.load_datasets(datasets_file_path)

    def retrieve_datasets(self, query, top_k=20):
        """
        Retrieve most similar datasets based on query.
        
        Args:
            query (str): The search query
            top_k (int): Number of results to return
            
        Returns:
            list: List of matching datasets
            
        Raises:
            ValueError: If datasets or search is not initialized
        """
        if self.datasets is None:
                raise ValueError("No datasets loaded. Please load datasets first.")
                    
        if self.enhanced_search is None:
            raise ValueError("Enhanced search not initialized")
                
        # Use enhanced search
        logger.info(f"Performing enhanced search for query: {query}")
        return self.enhanced_search.search(query, top_k=top_k)

    def update_model_size(self, model_size):
        """
        Update the model size and reinitialize the search index.
        
        Args:
            model_size (str): New model size ("small", "medium", or "large")
            
        Returns:
            bool: True if successful
        """
        if model_size == self.model_size:
            logger.info(f"Model size already set to {model_size}, no change needed")
            return True
            
        logger.info(f"Updating model size from {self.model_size} to {model_size}")
        self.model_size = model_size
        
        # Rebuild the search index if datasets are loaded
        if self.datasets is not None:
            self.enhanced_search = create_enhanced_search_manager(
                self.datasets, 
                model_size=model_size
            )
            logger.info(f"Search index rebuilt with {model_size} models")
        
        return True
        
    def update_search_weights(self, weights):
        """
        Update the field weights for search.
        
        Args:
            weights (dict): Dictionary mapping field names to weights
            
        Returns:
            bool: True if successful
            
        Raises:
            ValueError: If enhanced search is not initialized
        """
        if self.enhanced_search is None:
            raise ValueError("Enhanced search not initialized")
            
        self.enhanced_search.update_weights(weights)
        logger.info(f"Updated search weights: {weights}")
        return True