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
    CSS_ML_TOOL_NAME = "RAG app with CSS"
    CSS_EMBEDDING_MODEL = "CML_embedding_model"
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
    CSS_CONNECTOR_NAME_EMBEDDING = 'CSS_CML_connector'
    CONNECTOR_FOR_EMBEDDING_BODY =  {
            "name": CSS_CONNECTOR_NAME_EMBEDDING,
            "description": "The connector CML Embedding model service ",
            "version": 1,
            "protocol": "http",
            "parameters": {
                "endpoint": CSS_EMBEDDING_OPENAI_ENDPOINT,
                "model": CSS_EMBEDDING_OPENAI_MODEL,
                "api_version": CSS_EMBEDDING_OPENAI_VERSION
            },
            "credential": {
                "openAI_key": CSS_EMBEDDING_OPENAI_KEY
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
                    "request_body": "{ \"model\": \"${parameters.model}\", \"input\": ${parameters.input}, \"input_type\": \"query\" }",
                    "pre_process_function": "connector.pre_process.openai.embedding",
                    "post_process_function": "connector.post_process.openai.embedding"
                }
            ]
        }
    CSS_CONNECTOR_NAME_INFERECING = "CSS_RAG_LLM"
    CONNECTOR_FOR_INFERENCING_BODY = {
        "name":  CSS_CONNECTOR_NAME_INFERECING ,
        "description": "The connector OpenAI LLM model service ",
        "version": 1,
        "protocol": "http",
        "parameters": {
            "endpoint": os.getenv("CSS_OPENAI_ENDPOINT",'api.openapi.com'),
            "model": os.getenv("CSS_OPENAI_MODEL","gpt-3.5-turbo"),
            "api_version": os.getenv("CSS_OPENAI_VERSION",'1.0.1'),
            "skip_validating_missing_parameters": "true"
        },
        "credential": {
            "openAI_key": os.getenv("CSS_OPENAI_KEY","123456")
        },
        "actions": [
            {
                "action_type": "predict",
                "method": "POST",
                "url": "https://${parameters.endpoint}/openai/deployments/${parameters.model}/chat/completions?api-version=${parameters.api_version}",
                "headers": {
                    "api-key": "${credential.openAI_key}",
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
            "description": "This is a demo agent for RAG CSS Demo",
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
                        "embedding_field": "embedding",
                        "source_field": ["text"],
                        "input": "${{parameters.question}}"
                    }}
                }},
                {{
                    "type": "MLModelTool",
                    "name": "OpeAI Azure model",
                    "description": "A general tool to answer any question",
                    "parameters": {{
                        "model_id": "{inferencing_model_id}",
                        "prompt": "Generate the response for this question : ${{parameters.question}} with context: ${{parameters.prodct_kb.output:-}} "
                    }} 
                }}
            ]
        }}
    """
