from opensearchpy import OpenSearch
from config import Config
import time
import json
from urllib.parse import urlparse
import re

class OpenSearchUtils:

    def __init__(self):
    
        try:
            # Connect to OpenSearch
            self.client = OpenSearch(
                    hosts=[{'host': Config.CSS_HOST, 'port': Config.CSS_PORT}],
                    http_auth=(Config.CSS_USERNAME, Config.CSS_PASSWORD),
                    use_ssl=True if Config.CSS_SSL == "True" else False, 
                    verify_certs=False, 
                    ssl_show_warn=False,
                    timeout=60
                )
            print("Connected to OpenSearch!")
        except Exception as e:
            print(f"Error connecting to OpenSearch: {e}")
            self.client = ''
    def init_ml_settings(self):
        # This settings enable ML workloads to run with out any memory limit tripping.
        try:
            # Cluster settings payload
            inferencing_base_domain =  urlparse(Config.CSS_CML_LLM_ENDPOINT).netloc
            inferencing_escaped_url = re.sub(r'\.', r'\\.', inferencing_base_domain)
            settings_payload = {
                    "persistent": {
                        "plugins": {
                            "ml_commons": {
                                "native_memory_threshold": "100",
                                "jvm_heap_memory_threshold": "100",
                                "connector.private_ip_enabled": "true",
                                "model_access_control_enabled": "false",
                                "trusted_connector_endpoints_regex": [
                                    f"^https://{inferencing_escaped_url}/.*$"
                                ]
                            }
                        }
                    }
                }
            response = self.client.cluster.put_settings(body=settings_payload)
            print("Cluster settings updated successfully!")
        except Exception as e:
             print(f"Error occurred: {e}")

    def get_existing_connector(self, connector_name):
        """
        Checks if a connector with the given name already exists.

        Args:
            client: OpenSearch client instance.
            connector_name (str): Name of the connector to search for.

        Returns:
            dict: Connector details if found, otherwise None.
        """
        try:
            # Search for connectors with the given name
            search_body = {
                "query": {
                    "term" : {
                        "name.keyword" : {
                            "value": connector_name
                        }
                    }
                },
                "size" : 1
            }
            response = self.client.search(index=".plugins-ml-connector",body=search_body)

            # If connectors exist, return the first match
            if response["hits"]["total"]["value"] > 0:  
                connector_id = response["hits"]["hits"][0]["_id"]
                print(f"Connector '{connector_name}' found with model_id: {connector_id}")
                return connector_id
            else:
                return None

        except Exception as e:
            print(f"Exception occurred while checking connector: {str(e)}")
            return None

    def register_connector(self, connector_name, connector_body):
        """
        Registers a connector with OpenSearch and retrieves the connector_id.

        Args:
            client: OpenSearch client instance.
            connector_body (dict): The connector registration body.

        Returns:
            str: The connector_id if registration is successful.
            None: If registration fails.
        """
    
        connector_id = self.get_existing_connector(connector_name)
        if connector_id:
            return connector_id
        
        try:
            # Make the API call to register the connector
            response = self.client.http.post(
                "/_plugins/_ml/connectors/_create",
                body=connector_body
            )
            # Retrieve the connector_id
            connector_id = response.get("connector_id")
            if connector_id:
                print(f"Connector registered successfully with ID: {connector_id}")
            else:
                print("Connector registered but no connector_id returned.")
            
            return connector_id

        except Exception as e:
            print(f"Exception occurred while registering connector: {str(e)}")
            return None
        

    def model_exists_by_name(self, model_name):
        search_body = {
            "query": {
                "term": {
                    "name.keyword": {
                        "value": model_name  # Filter by the model name you want to check
                    }
                }
            },
            "_source": ["_id", "model_state"],
            "size": 100  # Limit the results to just one match if it exists
        }
        try:
            # Search in the model registry
            response = self.client.search(index=".plugins-ml-model", body=search_body)

            # Check if there are any hits
            if response["hits"]["total"]["value"] > 0:
                for hit in response["hits"]["hits"]:
                    if "model_state" in  hit["_source"]:
                        model_id = hit["_id"]
                        break             
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
    
    def register_embedding_model(self):

        body = {
                "name": Config.CSS_EMBEDDING_MODEL ,
                "version": "1.0.1",
                "model_format": "TORCH_SCRIPT"
        }
        response = self.register_and_deploy_model(body, Config.CSS_EMBEDDING_MODEL)
        if not "error" in response:
            self.embedding_model_id = response.get("model_id")
            print(f'Successfully registered embedding model with model_id: {self.embedding_model_id}')
        else:
            print(f'Failed to register embedding model with model_name: {Config.CSS_EMBEDDING_MODEL}')
            self.embedding_model_id = ''

    def register_LLM_model(self, connector_id):

        # Regsigter and deploy embedding model 
        body = {
            "name": Config.CSS_INFERENCING_MODEL,
            "function_name": "remote",
            "description": "CSS RAG LLM Model",
            "connector_id": connector_id
         }
        inferencing_model_name = Config.CSS_INFERENCING_MODEL
        response = self.register_and_deploy_model(body, inferencing_model_name )
        if not "error" in response:
            self.inferencing_model_id = response.get("model_id")
            print(f'Successfully registered inferencing model with model_id: {self.inferencing_model_id}')
        else:
            print(f'Failed to register embedding model with model_name: {inferencing_model_name}')
            self.inferencing_model_id = ''

    # Return agent_id  agent is already registered, if not return empty    
    def mltool_exists_by_name(self, mltool_name):
        search_body = {
            "query": {
                "term": {
                    "name.keyword": {
                        "value": mltool_name
                    }
                }
            },
            "size": 1  
        }
        try:
            # Search in the model registry
            response = self.client.search(index=".plugins-ml-agent", body=search_body)

            # Check if there are any hits
            if response["hits"]["total"]["value"] > 0:
                agent_id = response["hits"]["hits"][0]["_id"]
                print(f"ML tool '{mltool_name}' found with agent_id: {agent_id}")
                return agent_id
            else:
                print(f"ML tool '{mltool_name}' does not exist.")
                return ""  # Return an empty string if the model does not exist
        except Exception as e:
                print(f'Exception while searchiong ML Tool {e}')
                return ""
    
    def create_mltool_agent(self, embedding_model_id, inferencing_model_id):

        tool_name = Config.CSS_ML_TOOL_NAME
        agent_id = self.mltool_exists_by_name(tool_name)
        if ( not agent_id ):
            
            # Fill in the variables using str.format
            filled_template = Config.CSS_ML_TOOL_BODY_TEMPLATE.format(
                css_ml_tool_name = tool_name,
                inferencing_model_id=inferencing_model_id,
                embedding_model_id=embedding_model_id,
                index_name=Config.INDEX_NAME
            )

            # Convert the resulting string back to a JSON object (optional)
            mltool_body = json.loads(filled_template)

            try:
                response =  self.client.http.post('/_plugins/_ml/agents/_register', body=mltool_body)
                if response:
                    # Extract the agent_id
                    agent_id = response.get("agent_id")  # Default to empty string if key doesn't exist
                    self.client.ml_tool_id = agent_id
                
                    # Print or use the agent_id
                    print(f"ML Tool Agent ID: {agent_id}")
            except ValueError:
                print("ML Tool creation failed")
                return ""
        else:
            print(f"ML Tool {agent_id} exists")
        
        return agent_id

    # Execute the RAG tool in CSS and return the result
    def rag_execute(self, query,agent_id):
    
        body = {
            "parameters": {
                "question": query
            }
        }

        if  hasattr(self, 'memory_id'):
             body["parameters"]["memory_id"] = self.memory_id
             body["parameters"]["message_history_limit"] = 5
            
        response_str = ""
        combined_response = ""
    
        try:
            response =  self.client.http.post(f'/_plugins/_ml/agents/{agent_id}/_execute', body=body)

            # Extract inference results
            inference_results = response.get("inference_results", [])
            # print(inference_results)
            for result in inference_results:
                outputs = result.get("output", [])
                for output in outputs:
                    if output.get("name") == "memory_id" and not hasattr(self, 'memory_id'):
                        self.memory_id = output.get("result")
                    if output.get("name") == 'Cloudera AI Inferencing model':
                        # Parse the response string
                        result = json.loads(output.get("result"))
                        choices = result.get("choices",[])
                        for choice in choices:
                            response_str = choice.get("message").get("content","")
                            combined_response += response_str + " "
                        
        except Exception as e :
            print(f"Error occurred while making ML  TOOLAPI call:  {e}")
        
        return combined_response
    

    # Check if the neural pipeline exists 
    def pipeline_exists(self, pipeline_id):
        try:
            # Check if the pipeline exists by querying the pipeline endpoint
            response = self.client.ingest.get_pipeline(pipeline_id)
            print(f"Pipeline '{pipeline_id}' exists.")
            return True
        except Exception as e:
            print("Pipeline '{pipeline_id}' doesn't exists")
            return False
    
    # Create neural pipeline for ingesting vectors into the CSS
    def create_neural_pipeline(self):

        if ( not  self.pipeline_exists(Config.NS_PIPELINE)):
            pipeline_body = Config.NS_PIPE_LINE_BODY
            # Add the model_id to the text_embedding dictionary in the pipeline body
            for processor in pipeline_body["processors"]:
                if "text_embedding" in processor:
                    processor["text_embedding"]["model_id"] = self.embedding_model_id 
                    break
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
        try:
            response = self.client.index(index=Config.INDEX_NAME, id=doc_id, body=document)
        except Exception as e :
            print(f"Error while inserting document to CSS {e}")
            return ""
        return response


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
            #Undeply and delete Embedding Model 
            if not  hasattr(self.client, 'embedding_model_id'):
                model_id = self.model_exists_by_name(Config.CSS_EMBEDDING_MODEL)
                self.embedding_model_id = model_id if model_id else ""
            if(model_id):
                response =  self.client.http.get(f'/_plugins/_ml/models/{self.embedding_model_id}')
                # Extract  results
                results = response.get("model_state")
                if results == "DEPLOYED": 
                    deploy_path = f"/_plugins/_ml/models/{self.embedding_model_id}/_undeploy"
                    response = self.client.http.post(deploy_path)
                    print(f"Embedding Model {self.embedding_model_id} Undeployed ")
                response = self.client.http.delete(f'/_plugins/_ml/models/{self.embedding_model_id}')
                print(f"Embedding Model {self.embedding_model_id} DELETED")
        except Exception as e :
                    print(f"Error occurred while deploying model:{e}")
        try:
                          
            #Undeply and delete Inferencing Model 
            if not  hasattr(self.client, 'inferencing_model_id'):
                model_id = self.model_exists_by_name(Config.CSS_INFERENCING_MODEL)
                self.inferencing_model_id = model_id if model_id else ""
            if model_id:
                response =  self.client.http.get(f'/_plugins/_ml/models/{self.inferencing_model_id}')
                # Extract  results
                results = response.get("model_state")
                if results == "DEPLOYED": 
                    deploy_path = f"/_plugins/_ml/models/{self.inferencing_model_id}/_undeploy"
                    response = self.client.http.post(deploy_path)
                    print(f"Inferencing Model {self.inferencing_model_id} Undeployed with")
                
                response = self.client.http.delete(f'/_plugins/_ml/models/{self.inferencing_model_id}')
                print(f"Inferencing Model {self.inferencing_model_id} DELETED")
    
        except Exception as e :
                print(f"Error occurred while deploying model:{e}")

    def delete_mltool(self):
        """
        delete the MLTool registered for RAG use case

        Args: client (Opensearch)

        Returns: 
             Nothing: Prints message if it is deleted or not.
        """
        tool_name = Config.CSS_ML_TOOL_NAME
        agent_id = self.mltool_exists_by_name(tool_name)
        if ( agent_id ):
            try:
                response =  self.client.http.delete(f'/_plugins/_ml/agents/{agent_id}')
                print(f"ML Tool Agent : {agent_id} Deleted")
            except ValueError:
                print("ML Tool Deleyte failed")

    def delete_connector(self):
        """
        UndDelete the connectors  in OpenSearch if it is currently deployed.
        
        Args:
            client (OpenSearch): The OpenSearch client instance..
            
        Returns:
            str: A message indicating whether the model was undeployed or not.
        """
        
        try:

            connector_id = self.get_existing_connector(Config.CSS_CONNECTOR_NAME_INFERECING)
            if connector_id:
                response = self.client.http.delete(f'/_plugins/_ml/connectors/{connector_id}')
                print(f"Connector for Inferencing {connector_id} DELETED")
    
        except Exception as e :
                print(f"Error occurred while deleting connector:{e}")


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
        
    def fetch_mltool_definition(self, ml_tool_id: str) -> str:
        """Fetch ML Tool definition"""
        if ml_tool_id:
            try:
                response = self.client.http.get(f'/_plugins/_ml/agents/{ml_tool_id}')
                return  json.dumps(response, indent=4)
            except ValueError:
                print("ML Tool Fetch failed")
                return None  # Explicitly return None in case of an error
        else:
            print("ML Tool ID is required")
            return None  # Return None if ml_tool_id is not provided
        
    def fetch_model_definition(self, model_name: str) -> str:
        """ Fetch the model details for display"""

        model_id = self.model_exists_by_name(model_name)
        if model_id:
            try:
                response =  self.client.http.get(f'/_plugins/_ml/models/{model_id}')
                response['model_id'] = model_id  # Add model_id to the response
                return  json.dumps(response, indent=4)
            except ValueError:
                print("ML Model  Fetch failed")
                return None  # Explicitly return None in case of an error
        else:
            print("ML Model ID is required")
            return None  # Return None if ml_tool_id is not provided
        
    def fetch_connector_definition(self, connector_name: str) -> str:
        """ Fetch the Connector details for display"""

        connector_id = self.get_existing_connector(connector_name)
        if connector_id:
            try:
                response =  self.client.http.get(f'/_plugins/_ml/connectors/{connector_id}')
                response['connector_id'] = connector_id  # Add model_id to the response
                return  json.dumps(response, indent=4)
            except ValueError:
                print("ML Model  Fetch failed")
                return None  # Explicitly return None in case of an error
        else:
            print("ML Model ID is required")
            return None  # Return None if ml_tool_id is not provided