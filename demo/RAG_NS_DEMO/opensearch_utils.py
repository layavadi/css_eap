from opensearchpy import OpenSearch
from config import Config
import time
import json

class OpenSearchUtils:

    def __init__(self):
        try:
            # Connect to OpenSearch
            self.client = OpenSearch(
                    hosts=[{'host': Config.CSS_HOST, 'port': Config.CSS_PORT}],
                    http_auth=(Config.CSS_USERNAME, Config.CSS_PASSWORD),
                    use_ssl=True if Config.CSS_SSL == "True" else False, 
                    verify_certs=False, 
                    ssl_show_warn=False
                )
            print("Connected to OpenSearch!")
        except Exception as e:
            print(f"Error connecting to OpenSearch: {e}")
            self.clinet = ''
    def init_ml_settings(self):
        # This settings enable ML workloads to run with out any memory limit tripping.
        try:
            # Cluster settings payload
            settings_payload = {
                    "persistent": {
                        "plugins": {
                            "ml_commons": {
                                "native_memory_threshold": "100",
                                "jvm_heap_memory_threshold": "100"
                            }
                        }
                    }
                }
            response = self.client.cluster.put_settings(body=settings_payload)
            print("Cluster settings updated successfully!")
        except Exception as e:
             print(f"Error occurred: {e}")

    def model_exists_by_name(self, model_name):
        search_body = {
            "query": {
                "term": {
                    "name.keyword": {
                        "value": model_name  # Filter by the model name you want to check
                    }
                }
            },
            "size": 1  # Limit the results to just one match if it exists
        }
        try:
            # Search in the model registry
            response = self.client.search(index=".plugins-ml-model", body=search_body)

            # Check if there are any hits
            if response["hits"]["total"]["value"] > 0:
                model_id = response["hits"]["hits"][0]["_source"]["model_id"]
                print(f"Model '{model_name}' found with model_id: {model_id}")
                return model_id
            else:
                print(f"Model '{model_name}' does not exist.")
                return ""  # Return an empty string if the model does not exist
        except:
            return ""

    def register_and_deploy_model(self, model_body, model_name, poll_interval=5):
        """
        Registers a model, polls the task until it's completed, retrieves the model ID,
        deploys the model, and waits for deployment to complete.

        Args:
            client: OpenSearch client handle.
            model_body (dict): The JSON body for registering the model.
            poll_interval (int): Time in seconds to wait between status checks.

        Returns:
            dict: Final deployment details or error information.
        """
        try:
            # Step 1: Check if Model is already registered
            model_id = self.model_exists_by_name(model_name)

            if not model_id: 

                #  Register the model
                register_path = "/_plugins/_ml/models/_register"
                register_response = self.client.http.post(register_path, body=model_body)
                task_id = register_response.get("task_id")
                if not task_id:
                    return {"error": "Task ID not found in register response"}
                print(f"Model registration initiated. Task ID: {task_id}")

                #  Poll task status to get the model ID
                task_status_path = f"/_plugins/_ml/tasks/{task_id}"
                model_id = None
                while True:
                    task_response = self.client.http.get(task_status_path)
                    state = task_response.get("state")
                    print(f"Task state: {state}")
                    if state == "COMPLETED":
                        model_id = task_response.get("model_id")
                        if not model_id:
                            return {"error": "Model ID not found in task completion response"}
                        print(f"Model registration completed. Model ID: {model_id}")
                        break
                    elif state in {"FAILED", "ERROR"}:
                        return {"error": "Model registration failed", "details": "Unknown"}

                    time.sleep(poll_interval)

            response =  self.client.http.get(f'/_plugins/_ml/models/{model_id}')
            # Extract inference results
            results = response.get("model_state")
            if results == "REGISTERED": 
                # Step 3: Deploy the model
                deploy_path = f"/_plugins/_ml/models/{model_id}/_deploy"
                deploy_response = self.client.http.post(deploy_path)
                task_id = deploy_response.get("task_id")
                print(f"Deployment initiated for model ID: {model_id} with task {task_id}")

                # Step 4: Poll the deployment status
                model_status_path = f"/_plugins/_ml/models/{model_id}"
                while True:
                    status_response = self.client.http.get(model_status_path)
                    status = status_response.get("model_state")
                    print(f"Model state: {status}")
                    if status == "DEPLOYED":
                        print("Model successfully deployed.")
                        break
                    elif status in {"FAILED", "ERROR"}:
                        return {"error": "Model deployment failed", "details": {status}}

                    time.sleep(poll_interval)
        except Exception as e:
            print(f"Error occurred  and error is {e}")
            return {"error": "Model deployment failed"}
            
        # Return final model details
        return {"message": "Model successfully deployed", "model_id": model_id}

    # Register model for generating embedding
    
    def registerModel(self):

        # Regsigter and deploy embedding model 
        body = {
                    "name": Config.CSS_EMBEDDING_MODEL ,
                    "version": "1.0.1",
                    "model_format": "TORCH_SCRIPT"
                }
        response = self.register_and_deploy_model(body, Config.CSS_EMBEDDING_MODEL)
        if not "error" in response:
            self.model_id = response.get("model_id")
            print(f'Successfully registered embedding model with model_id: {self.model_id}')
        else:
            print(f'Failed to register embedding model with model_name: {Config.CSS_EMBEDDING_MODEL}')
            self.model_id = ''


    # Check if the neural pipeline exists 
    def pipeline_exists(self, pipeline_id):
        try:
            # Check if the pipeline exists by querying the pipeline endpoint
            response = self.client.ingest.get_pipeline(pipeline_id)
            print(f"Pipeline '{pipeline_id}' exists.")
            return True
        except Exception as e:
            print(f"Pipeline '{pipeline_id}' doesn't exists")
            return False
    
    # Create neural pipeline for ingesting vectors into the CSS
    def create_neural_pipeline(self):

        if ( not  self.pipeline_exists(Config.NS_PIPELINE)):
            pipeline_body = {
                "description": "Pipeline for generating embeddings with neural model",
                "processors": [
                    {
                        "text_embedding": {
                            "model_id": self.model_id,
                            "field_map": {
                                "text": "embedding"
                            }
                        }
                    }
                ]
            }
            self.client.ingest.put_pipeline(Config.NS_PIPELINE, body=pipeline_body)
            print(f"Pipeline {Config.NS_PIPELINE} created")
        else:
            print(f"Pipeline {Config.NS_PIPELINE} exists")

    # Create the index with neural pipleline doing the mapping between text and embeddings
    def create_index_with_vector_field(self):

        if self.client.indices.exists(index=Config.INDEX_NAME):
            print(f"Index '{Config.INDEX_NAME}' already exists.")
        else:
            index_body = Config.INDEX_SETTINGS
            self.client.indices.create(index=Config.INDEX_NAME, body=index_body)
            print(f"Index '{Config.INDEX_NAME}' created successfully.")

# Step 3: Insert Embeddings and Text into OpenSearch
    def insert_document(self, doc_id, text):

        document = {
            "text": text
        }
        response = self.client.index(index=Config.INDEX_NAME, id=doc_id, body=document)
        return response

    def search_by_neural(self, query, top_k=5):

        if not  hasattr(self.client, 'model_id'):
            model_id = self.model_exists_by_name(Config.CSS_EMBEDDING_MODEL)
            self.model_id = model_id if model_id else ""

        query_body = {
            "size": top_k,
            "query": {
                "neural": {
                    "embedding": {
                        "query_text": query,
                        "model_id": self.model_id,
                        "k": top_k
                    }
                }
            },
            "_source": ["text"]
        }
        response = self.client.search(index=Config.INDEX_NAME, body=query_body)
        # Print the number of hits
        number_of_hits = response['hits']['total']['value']
        print(f"Number of hits: {number_of_hits}")

        # Print the IDs and scores of the hits
        print("Hit IDs and Scores:")
        
        hits = response['hits']['hits']
        contexts = []
        for hit in hits:
            doc_id = hit['_id']  # Document ID containing name and chunk info
            doc_name, chunk = doc_id.split('_chunk_')  # Assuming ID is formatted as 'docname_chunkN'
            context = hit['_source'].get('text', 'No context available')
            score = hit['_score']
            print(f"ID: {doc_id}, chunk: {chunk} Score: {score}")
            
            contexts.append({
                'document': doc_name,
                'chunk': chunk,
                'context': context[:500],  # Snippet of the first 500 characters
                'score': score
            })
        return contexts
    
    def check_and_delete_index(self):
        """
        Check if an OpenSearch index exists and delete it if it exists.
        
        Args:
            client (OpenSearch): The OpenSearch client instance.
            index_name (str): The name of the index to check and delete.
            
        Returns:
            str: A message indicating whether the index was deleted or not.
        """
        try:
            # Check if the index exists
            if self.client.indices.exists(index=Config.INDEX_NAME):
                print(f"Index '{Config.INDEX_NAME}' exists. Deleting it...")
                # Delete the index
                self.client.indices.delete(index=Config.INDEX_NAME)
                return f"Index '{Config.INDEX_NAME}' deleted successfully."
            else:
                return f"Index '{Config.INDEX_NAME}' does not exist."
        except Exception as e:
            return f"An error occurred while deleting index: {str(e)}"

    def delete_neural_search_pipeline(self):
        """
        Delete a neural search pipeline in OpenSearch if it exists.
        
        Args:
            client (OpenSearch): The OpenSearch client instance.
            pipeline_name (str): The name of the pipeline to delete.
            
        Returns:
            str: A message indicating whether the pipeline was deleted or not.
        """
        try:
            # Check if the pipeline exists by retrieving its configuration
            response = self.client.ingest.get_pipeline(id=Config.NS_PIPELINE, ignore=404)
            if response and Config.NS_PIPELINE in response:
                print(f"Pipeline '{Config.NS_PIPELINE}' exists. Deleting it...")
                # Delete the pipeline
                self.client.ingest.delete_pipeline(id=Config.NS_PIPELINE)
                return f"Pipeline '{Config.NS_PIPELINE}' deleted successfully."
            else:
                return f"Pipeline '{Config.NS_PIPELINE}' does not exist."
        except Exception as e:
            return f"An error occurred while deleting pipeline: {str(e)}"
        
    def undeploy_and_delete_model(self):
        """
        Undeploy a model in OpenSearch if it is currently deployed.
        
        Args:
            client (OpenSearch): The OpenSearch client instance.
            model_id (str): The ID of the model to undeploy.
            
        Returns:
            str: A message indicating whether the model was undeployed or not.
        """
        
        try:
            if not  hasattr(self.client, 'model_id'):
                model_id = self.model_exists_by_name(Config.CSS_EMBEDDING_MODEL)
                self.model_id = model_id if model_id else ""
                
            response =  self.client.http.get(f'/_plugins/_ml/models/{self.model_id}')
            # Extract inference results
            results = response.get("model_state")
            if results == "DEPLOYED": 
                deploy_path = f"/_plugins/_ml/models/{self.model_id}/_undeploy"
                response = self.client.http.post(deploy_path)
                print(f"Model {self.model_id} Undeployed with")
            
            response = self.client.http.delete(f'/_plugins/_ml/models/{self.model_id}')
            print(f"Model {self.model_id} DELETED")
    
        except Exception as e :
                print(f"Error occurred while deploying model:{e}")
                

    def fetch_index_mapping(self,index_name: str) -> str:
        """Fetch index mapping from OpenSearch."""
        try:
            mapping = self.client.indices.get_mapping(index=index_name)
            settings = self.client.indices.get_settings(index=index_name)
            return json.dumps(mapping, indent=4), json.dumps(settings, indent=4)
        except Exception as e:
            return f"Error fetching index mapping and settings: {str(e)}"
    
    
    def fetch_pipeline_definition(self,pipeline_name: str) -> str:
        """Fetch pipeline definition from OpenSearch."""
        try:
            pipeline = self.client.ingest.get_pipeline(id=pipeline_name)
            return json.dumps(pipeline, indent=4)
        except Exception as e:
            return f"Error fetching pipeline definition: {str(e)}"
