import os

class Config:
    CSS_HOST = os.getenv("CSS_HOST","localhost")
    CSS_PORT = os.getenv("CSS_PORT",9200)
    CSS_USERNAME = os.getenv("CSS_USERNAME","admin")
    CSS_PASSWORD = os.getenv("CSS_PASSWORD","admin")
    DATA_FILE_PATH = os.getenv("DOC_PATH",'./data')
    CSS_OPENAI_KEY = os.getenv("CSS_OPENAI_KEY")
    CSS_OPENAI_VERSION = os.getenv("CSS_OPENAI_VERSION")
    CSS_OPENAI_MODEL = os.getenv("CSS_OPENAI_MODEL")
    CSS_OPENAI_ENDPOINT = "https://"+os.getenv("CSS_OPENAI_ENDPOINT")+"/"
    CSS_EMBEDDING_OPENAI_KEY = os.getenv("CSS_EMBEDDING_OPENAI_KEY")
    CSS_EMBEDDING_OPENAI_VERSION = os.getenv("CSS_EMBEDDING_OPENAI_VERSION")
    CSS_EMBEDDING_OPENAI_MODEL = os.getenv("CSS_EMBEDDING_OPENAI_MODEL")
    CSS_EMBEDDING_OPENAI_ENDPOINT = "https://"+os.getenv("CSS_EMBEDDING_OPENAI_ENDPOINT")
    CSS_EMBEDDING_OPENAI_DIMENSION = os.getenv("CSS_EMBEDDING_DIMENSION")
    INDEX_NAME = "prod_docs_index"
    NS_PIPELINE = "neural-search-pipeline"
    CSS_EMBEDDING_MODEL = "CML_embedding_model"
    CSS_SSL = os.getenv("CSS_SSL","False")
    CSS_CONNECTOR_NAME = 'CSS_CML_connector'
    INDEX_SETTINGS = {
                "settings": {
                    "index": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                        "knn": True,  # Enable k-Nearest Neighbors for nmslib
                        "default_pipeline": "neural-search-pipeline"
                    }
                },
                "mappings": {
                    "properties": {
                        "text": {"type": "text"},
                        "embedding": {
                            "type": "knn_vector",  # Vector type field
                            "dimension": int(CSS_EMBEDDING_OPENAI_DIMENSION),  # Number of dimensions from the embedding model
                            "method": {
                                "name": "hnsw",  # Method for the vector search
                                "space_type": "l2",  # Euclidean distance for similarity
                                "engine": "nmslib"  # Use nmslib as the vector search engine
                            }
                        }
                    }
                }
            }
