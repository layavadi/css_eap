import os

class Config:
    CSS_HOST = os.getenv("CSS_HOST","localhost")
    CSS_PORT = os.getenv("CSS_PORT",9200)
    CSS_USERNAME = os.getenv("CSS_USERNAME","admin")
    CSS_PASSWORD = os.getenv("CSS_PASSWORD","admin")
    DATA_FILE_PATH = os.getenv("DOC_PATH",'./data')
    CSS_CDP_TOKEN_KEY = os.getenv("CSS_CDP_TOKEN_KEY")
    CSS_CML_LLM_MODEL = os.getenv("CSS_CML_LLM_MODEL")
    CSS_CML_LLM_ENDPOINT = "https://"+os.getenv("CSS_CML_LLM_ENDPOINT")
    CSS_EMBEDDING_OPENAI_MODEL = os.getenv("CSS_EMBEDDING_OPENAI_MODEL")
    CSS_EMBEDDING_OPENAI_DIMENSION = os.getenv("CSS_EMBEDDING_DIMENSION")
    INDEX_NAME = "prod_docs_index"
    NS_PIPELINE = "neural-search-pipeline"
    NS_PIPE_LINE_BODY =  {
            "description": "Pipeline for generating embeddings with neural model couple with pre-processor for text chunking",
            "processors": [
                {
                    "text_chunking": {
                        "algorithm": {
                            "fixed_token_length": {
                                "token_limit": 500,
                                "overlap_rate": 0.2,
                                "tokenizer": "standard"
                            }
                        },
                        "field_map": {
                            "text": "text_chunks"
                        }
                    }
                },
                {
                    "text_embedding": {
                        "field_map": {
                            "text_chunks": "embeddings"
                        },
                        "batch_size": 1
                    }
                },
                {
                    "script": {
                        "source": """
                        if (ctx.text_chunks != null && ctx.embeddings != null) {
                            ctx.nested_chunks_embeddings = [];
                            for (int i = 0; i < ctx.text_chunks.length; i++) {
                                ctx.nested_chunks_embeddings.add(
                                    ['chunk': ctx.text_chunks[i], 'embedding': ctx.embeddings[i].knn]
                                );
                            }
                        }
                        ctx.remove('text_chunks');
                        ctx.remove('embeddings');
                        """
                    }
                }
            ]
    }
    CSS_ML_TOOL_NAME = "RAG app with CSS"
    CSS_EMBEDDING_MODEL = os.getenv("CSS_EMBEDDING_OPENAI_MODEL")
    CSS_INFERENCING_MODEL = "CSS RAG LLM"
    CSS_SSL = os.getenv("CSS_SSL","False")
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
                        "nested_chunks_embeddings": {
                            "type": "nested",
                            "properties" : {
                                "chunk": {"type": "text"},
                                "embedding": {
                                    "type": "knn_vector",  # Vector type field
                                    "dimension": int(CSS_EMBEDDING_OPENAI_DIMENSION),  # Number of dimensions from the embedding model
                                    "method": {
                                        "name": "hnsw",  # Method for the vector search
                                        "space_type": "l2",  # Euclidean distance for similarity
                                        "engine": "lucene"  # Use nmslib as the vector search engine
                                    }
                                }
                            }
                        }
                    }
                }
               
            }

    CSS_CONNECTOR_NAME_INFERECING = "CSS_RAG_LLM"
    CONNECTOR_FOR_INFERENCING_BODY = {
        "name":  CSS_CONNECTOR_NAME_INFERECING ,
        "description": "The connector for Cloudera AI Inferencing  LLM model service ",
        "version": 1,
        "protocol": "http",
        "parameters": {
            "endpoint": CSS_CML_LLM_ENDPOINT,
            "model": CSS_CML_LLM_MODEL,
            "skip_validating_missing_parameters": "true"
        },
        "credential": {
            "openAI_key": os.getenv("CSS_CDP_TOKEN_KEY","123456")
        },
        "actions": [
            {
                "action_type": "predict",
                "method": "POST",
                "url": "${parameters.endpoint}",
                "headers": {
                    "Authorization" : "Bearer ${credential.openAI_key}",
                    "Content-type": "application/json"
                },
                "request_body": "{ \"model\": \"${parameters.model}\", \"messages\": [ { \"role\":\"user\" , \"content\":  \" ${parameters.prompt} \" } ] }"
            }
        ]
    }
    CSS_ML_TOOL_BODY_TEMPLATE = """
        {{
            "name": "RAG app with CSS",
            "type": "conversational_flow",
            "description": "This is a conversational demo agent for RAG CSS Demo",
            "app_type": "rag",
            "memory": {{
                "type": "conversation_index"
            }},
            "tools": [
                {{
                    "type": "VectorDBTool",
                    "name": "prodct_kb",
                    "parameters": {{
                        "model_id": "{embedding_model_id}",
                        "index": "{index_name}",
                        "embedding_field": "nested_chunks_embeddings.embedding",
                        "source_field": ["nested_chunks_embeddings.chunk"],
                        "nested_path": "nested_chunks_embeddings",
                        "input": "${{parameters.question}}"
                    }}
                }},
                {{
                    "type": "MLModelTool",
                    "name": "Cloudera AI Inferencing model",
                    "description": "A general tool to answer any question",
                    "parameters": {{
                        "model_id": "{inferencing_model_id}",
                        "prompt": "Generate the response for this question : ${{parameters.question}} with context: ${{parameters.prodct_kb.output:-}} "
                    }} 
                }}
            ]
        }}
    """
