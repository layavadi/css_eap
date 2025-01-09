import os

class Config:
    CSS_HOST = os.getenv("CSS_HOST","localhost")
    CSS_PORT = os.getenv("CSS_PORT",9200)
    CSS_USERNAME = os.getenv("CSS_USERNAME","admin")
    CSS_PASSWORD = os.getenv("CSS_PASSWORD","admin")
    INDEX_NAME = "image_docs_index"
    CSS_EMBEDDING_MODEL = "ViT-B/32"
    CSS_SSL = os.getenv("CSS_SSL","False")
    INDEX_SETTINGS = {
                "settings": {
                    "index": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                        "knn": True,
                    }
                },
                "mappings": {
                    "properties": {
                        "image_path": {"type": "text"},
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": 512
                        }
                    }
                }
            }
