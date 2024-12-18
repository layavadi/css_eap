
from opensearchpy import OpenSearch
from opensearch_py_ml.ml_commons import MLCommonClient
import os
import PyPDF2
import gradio as gr
import re
from flask import Flask, send_file, abort
import time
import json
import argparse

embedding_model_id = ''
inferencing_model_id = ''
ml_agent_id = ''
connector_id = ''
# This is a pretrained model that is supported by CSS
embedding_model_name = "huggingface/sentence-transformers/all-mpnet-base-v2"
inferencing_model_name = "CSS_RAG_LLM"

# Location of all the documents to be inserted to CSS 
folder_path = os.getenv("DOC_PATH",'/Users/vbhatt/opensearch/Demo/TestDoc')

# Name of the index in CSS 
index_name = 'prod_docs_index'

#Name of the Connector 
connector_name = 'CSS_openAPI_connector'


# Step 3: Perform vector search in OpenSearch
def rag_execute(query, client,agent_id):
    
    body = {
        "parameters": {
            "question": query
        }
    }
    response_str = ""
    combined_response = ""
    try:
        response =  client.http.post(f'/_plugins/_ml/agents/{agent_id}/_execute', body=body)
    
       #response = {'inference_results': [{'output': [{'name': 'response', 'result': '{"choices":[{"content_filter_results":{"hate":{"filtered":false,"severity":"safe"},"self_harm":{"filtered":false,"severity":"safe"},"sexual":{"filtered":false,"severity":"safe"},"violence":{"filtered":false,"severity":"safe"}},"finish_reason":"stop","index":0.0,"message":{"content":"To ingest data in COD using SQLLine from COD, you can follow the below procedure:\\n\\n1. Click on \\"Databases\\" and select a specific database from the provided list.\\n2. Click on \\"Hue\\" to access the web-based interactive SQL editor.\\n3. Once you are in the Hue user interface, you can create and browse HBase tables.\\n4. In case you prefer using the REST API for data ingestion, you can follow these steps:\\n   a. Click on \\"Databases\\" and select a database from the list.\\n   b. Click on \\"Connect HBase REST\\".\\n   c. Copy the URL from the HBase REST Server URL field to connect to the desired database.\\n5. After connecting, you can utilize the HBase REST API to interact with HBase services, tables, and regions by using various HTTP endpoints.\\n6. This allows you to perform actions like creating tables, inserting or retrieving data, and managing the database using different programming languages.\\n\\nRemember to use the appropriate endpoints and HTTP methods provided by the HBase REST API based on your data ingestion requirements.","role":"assistant"}}],"created":1.732719506E9,"id":"chatcmpl-AYDmkIpLfONDfLRfXFA18Ghby7QHH","model":"gpt-35-turbo-16k","object":"chat.completion","prompt_filter_results":[{"prompt_index":0.0,"content_filter_results":{"hate":{"filtered":false,"severity":"safe"},"self_harm":{"filtered":false,"severity":"safe"},"sexual":{"filtered":false,"severity":"safe"},"violence":{"filtered":false,"severity":"safe"}}}],"usage":{"completion_tokens":221.0,"prompt_tokens":230.0,"total_tokens":451.0}}'}]}]}

        # Extract inference results
        inference_results = response.get("inference_results", [])
        #print(inference_results)
        for result in inference_results:
            outputs = result.get("output", [])
            for output in outputs:
                if output.get("name") == 'OpeAI Azure model':
                    # Parse the response string
                    result = json.loads(output.get("result"))
                    choices = result.get("choices",[])
                    for choice in choices:
                        response_str = choice.get("message").get("content","")
                        combined_response += response_str + " "
                    
    except Exception as e :
        print(f"Error occurred while making ML  TOOLAPI call:  {e}")
    
    return combined_response


def create_opensearch_client(host, port, user, password):
    try:
        # Connect to OpenSearch
        client = OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_auth=(user, password),
            use_ssl=False,
            verify_certs=False,
            ssl_show_warn=False,
            timeout=60
        )
        print("Connected to OpenSearch!")
        return client
    except Exception as e:
        print(f"Error connecting to OpenSearch: {e}")
        return None
    

def get_existing_connector(client, connector_name):
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
        response = client.search(index=".plugins-ml-connector",body=search_body)

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

def register_connector(client):
    """
    Registers a connector with OpenSearch and retrieves the connector_id.

    Args:
        client: OpenSearch client instance.
        connector_body (dict): The connector registration body.

    Returns:
        str: The connector_id if registration is successful.
        None: If registration fails.
    """

    connector_id = get_existing_connector(client, connector_name)
    if connector_id:
        return connector_id
    
    connector_body = {
        "name": connector_name,
        "description": "The connector OpenAI model service ",
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
    try:
        # Make the API call to register the connector
        response = client.http.post(
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
    

# Return model id if model is already registered, if not return empty    
def model_exists_by_name(client, model_name):
    search_body = {
        "query": {
            "term": {
                "name.keyword": {
                    "value": model_name
                }
            }
        },
        "size" : 1
    }
    
    try:
    # Search in the model registry
        response = client.search(index=".plugins-ml-model", body=search_body)

        # Check if there are any hits
        if response["hits"]["total"]["value"] > 0:
            if "model_id" in response["hits"]["hits"][0]["_source"]:
                model_id = response["hits"]["hits"][0]["_source"]["model_id"]
            else:
                model_id = response["hits"]["hits"][0]["_id"]
            print(f"Model '{model_name}' found with model_id: {model_id}")
            return model_id
        else:
            print(f"Model '{model_name}' does not exist.")
            return ""  # Return an empty string if the model does not exist
    except:
            return ""
    
def register_and_deploy_model(client, model_body, model_name, poll_interval=5):
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
        model_id = model_exists_by_name(client, model_name)

        if not model_id: 

            # Step 2: Register the model
            register_path = "/_plugins/_ml/models/_register"
            register_response = client.http.post(register_path, body=model_body)
            task_id = register_response.get("task_id")
            if not task_id:
                return {"error": "Task ID not found in register response"}
            print(f"Model registration initiated. Task ID: {task_id}")

            # Step 2: Poll task status to get the model ID
            task_status_path = f"/_plugins/_ml/tasks/{task_id}"
            model_id = None
            while True:
                task_response = client.http.get(task_status_path)
                state = task_response.get("state")
                print(f"Task state: {state}")
                if state == "COMPLETED":
                    model_id = task_response.get("model_id")
                    if not model_id:
                        return {"error": "Model ID not found in task completion response"}
                    print(f"Model registration completed. Model ID: {model_id}")
                    break
                elif state in {"FAILED", "ERROR"}:
                    return {"error": "Model registration failed", "details": "unkown"}

                time.sleep(poll_interval)

        response =  client.http.get(f'/_plugins/_ml/models/{model_id}')
        # Extract inference results
        results = response.get("model_state")
        if results == "REGISTERED" or results == "UNDEPLOYED": 
            # Step 3: Deploy the model
            deploy_path = f"/_plugins/_ml/models/{model_id}/_deploy"
            deploy_response = client.http.post(deploy_path)
            task_id = deploy_response.get("task_id")
            print(f"Deployment initiated for model ID: {model_id} with task {task_id}")

            # Step 4: Poll the deployment status
            model_status_path = f"/_plugins/_ml/models/{model_id}"
            while True:
                status_response = client.http.get(model_status_path)
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
       
def registerModel(client,connector_id):

    # Regsigter and deploy embedding model 
    body = {
                "name": embedding_model_name,
                "version": "1.0.1",
                "model_format": "TORCH_SCRIPT"
            }
    response = register_and_deploy_model(client,body, embedding_model_name )
    if not "error" in response:
        embedding_model_id = response.get("model_id")
        print(f'Successfully registered embedding model with model_id: {embedding_model_id}')
    else:
        print(f'Failed to register embedding model with model_name: {embedding_model_name}')
        embedding_model_id = ''
    

    body = {
            "name": inferencing_model_name,
            "function_name": "remote",
            "description": "CSS RAG LLM Model",
            "connector_id": connector_id
    }

    response = register_and_deploy_model(client,body, inferencing_model_name )
    if not "error" in response:
        inferencing_model_id = response.get("model_id")
        print(f'Successfully registered inferencing model with model_id: {inferencing_model_id}')
    else:
        print(f'Failed to register embedding model with model_name: {inferencing_model_id}')
        inferencing_model_id = ''

    return (inferencing_model_id, embedding_model_id)

# Check if the neural pipeline exists 
def pipeline_exists(client, pipeline_id):
    try:
        # Check if the pipeline exists by querying the pipeline endpoint
        response = client.ingest.get_pipeline(pipeline_id)
        print(f"Pipeline '{pipeline_id}' exists.")
        return True
    except Exception as e:
        print(f"An error occurred: {e}")
        return False
    
# Create neural pipeline for ingesting vectors into the CSS
def create_neural_pipeline(client, model_id):

    pipeline_id = "neural-search-pipeline"
    
    if ( not  pipeline_exists(client, pipeline_id)):
        pipeline_body = {
            "description": "Pipeline for generating embeddings with neural model",
            "processors": [
                {
                    "text_embedding": {
                        "model_id": model_id,
                        "field_map": {
                            "text": "embedding"
                        }
                    }
                }
            ]
        }
        client.ingest.put_pipeline(pipeline_id, body=pipeline_body)
    else:
        print(f"Pipeline {pipeline_id} exists")

# Return agent_id  agent is already registered, if not return empty    
def mltool_exists_by_name(client, mltool_name):
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
        response = client.search(index=".plugins-ml-agent", body=search_body)

        # Check if there are any hits
        if response["hits"]["total"]["value"] > 0:
            agent_id = response["hits"]["hits"][0]["_id"]
            print(f"ML tool '{mltool_name}' found with agent_id: {agent_id}")
            return agent_id
        else:
            print(f"ML tool '{mltool_name}' does not exist.")
            return ""  # Return an empty string if the model does not exist
    except Exception as e:
            print(f'Exception while searchiong Rag {e}')
            return ""

    
# Create Rag tool agent for ingesting and querying LLM
def create_mltool_agent(client, embedding_model_id, inferencing_model_id):

    tool_name = "RAG app with CSS"
    agent_id = mltool_exists_by_name(client, tool_name)
    if ( not agent_id ):
        # ragtool_body = {
        #     "name": tool_name,
        #     "type": "flow",
        #     "description": "This is a RAG flow agent for CSS Demo",
        #     "tools": [
        #         {
        #             "type": "RAGTool",
        #             "description": "RAG Tool for CSS Demo",
        #             "parameters": {
        #                 "embedding_model_id": embedding_model_id,
        #                 "inference_model_id": inferencing_model_id,
        #                 "index": index_name,
        #                 "embedding_field": "embedding",
        #                 "query_type": "neural",
        #                 "source_field": ["text"],
        #                 "input": "${parameters.question}",
        #                 "prompt": (
        #                     "\n\nHuman: You are a helpful Assistant. You will always answer questions based on the given context first. "
        #                     "If the answer is not directly shown in the context, you will analyze the data and find the answer. "
        #                     "If you don't know the answer, just say don't know.\n\n"
        #                     "Context:\n${parameters.combined_context}\n\nHuman:${parameters.question}\n\nAssistant:"
        #                 ),
        #                 "combined_context": {
        #                     "script": {
        #                         "source": """
        #                         def combine_results(params) {
        #                             def results = params.search_results; 
        #                             results.sort { -it._score };  // Sort in descending order
        #                             def combined = results.collect { it._source.text }.join(' ');
        #                             return combined.length() > 1000 ? combined.substring(0, 1000) : combined;
        #                         }
        #                         combine_results(params);
        #                         """,
        #                         "params": {
        #                             "search_results": "${search_results}"
        #                         }
        #                     }
        #                 }
        #             }
        #         }
        #     ]
        # }
        mltool_body = {
                "name": "RAG app with CSS",
                "type": "conversational_flow",
                "description": "This is a demo agent for RAG CSS Demo",
                "app_type": "rag",
                "memory": {
                     "type": "conversation_index"
                },
                "tools": [
                    {
                        "type": "VectorDBTool",
                        "name": "prodct_kb",
                        "parameters": {
                            "model_id": embedding_model_id,
                            "index": index_name,
                            "embedding_field": "embedding",
                            "source_field": ["text"],
                            "input": "${parameters.question}"
                        }
                    },
                    {
                        "type": "MLModelTool",
                        "name": "OpeAI Azure model",
                        "description": "A general tool to answer any question",
                        "parameters": {
                            "model_id": inferencing_model_id,
                            "prompt": "Generate the response for this question : ${parameters.question} with context: ${parameters.prodct_kb.output:-} "
                        } 
                    }
                ]
        }
        # mltool_body = {
        #     "name": "RAG app with CSS",
        #     "type": "conversational_flow",
        #     "description": "This is a demo agent for RAG CSS Demo",
        #     "app_type": "rag",
        #     "memory": {
        #         "type": "conversation_index"
        #     },
        #     "tools": [
        #         {
        #             "type": "VectorDBTool",
        #             "name": "prodct_kb",
        #             "parameters": {
        #                 "model_id": embedding_model_id,
        #                 "index": index_name,
        #                 "embedding_field": "embedding",
        #                 "source_field": ["text"],
        #                 "input": "${parameters.question}",
        #                 "output_processing": {
        #                     "combined_context": {
        #                         "script": {
        #                             "source": """
        #                             def combine_results(params) {
        #                                 def results = params.search_results; 
        #                                 results.sort { -it._score };  // Sort in descending order
        #                                 def combined = results.collect { it._source.text }.join(' ');
        #                                 return combined.length() > 1000 ? combined.substring(0, 1000) : combined;
        #                             }
        #                             combine_results(params);
        #                             """,
        #                             "params": {
        #                                 "search_results": "${parameters.prodct_kb.output:-}"
        #                             }
        #                         }
        #                     }
        #                 }
        #             }
        #         },
        #         {
        #             "type": "MLModelTool",
        #             "name": "OpeAI Azure model",
        #             "description": "A general tool to answer any question",
        #             "parameters": {
        #                 "model_id": inferencing_model_id,
        #                 "prompt": "Generate the response for this question : ${parameters.question} with context: ${parameters.prodct_kb.output:-} " 
        #             }
        #         }
        #     ]
        # }
        try:
            response =  client.http.post('/_plugins/_ml/agents/_register', body=mltool_body)
            if response:
                # Extract the agent_id
                agent_id = response.get("agent_id")  # Default to empty string if key doesn't exist
            
                # Print or use the agent_id
                print(f"ML Tool Agent ID: {agent_id}")
        except ValueError:
            print("ML Tool creation failed")
    else:
        print(f"ML Tool {agent_id} exists")
    
    return agent_id

# Create the index with neural pipleline doing the mapping between text and embeddings
def create_index_with_vector_field(client, index_name, dimensions):
    if client.indices.exists(index=index_name):
        print(f"Index '{index_name}' already exists.")
    else:
        index_body = {
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
                        "dimension": dimensions,  # Number of dimensions from the embedding model
                        "method": {
                            "name": "hnsw",  # Method for the vector search
                            "space_type": "l2",  # Euclidean distance for similarity
                            "engine": "lucene"  # Use nmslib as the vector search engine
                        }
                    }
                }
            }
        }
        client.indices.create(index=index_name, body=index_body)
        print(f"Index '{index_name}' created successfully.")

# Step 3: Insert Embeddings and Text into OpenSearch
def insert_document(client, index_name, doc_id, text):

    document = {
        "text": text
    }
    response = client.index(index=index_name, id=doc_id, body=document)
    return response

# Function to read and chunk a PDF into text chunks
def chunk_pdf(pdf_path, chunk_size=500):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()

    text = re.sub(r'[\n\t\r]', ' ', text)  # Replace newlines, tabs, and carriage returns with a space
    text = re.sub(r' +', ' ', text)  # Replace multiple spaces with a single space

    # Split text into chunks of specified size (e.g., 500 characters)
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]


# Function to process all PDF files in a folder and insert into OpenSearch
def process_pdf_folder_and_insert_to_opensearch(folder_path, client, index_name):
    # Iterate over all PDF files in the folder
    for filename in os.listdir(folder_path):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(folder_path, filename)

            # Iterate through chunks of the PDF
            for i, chunk in enumerate(chunk_pdf(pdf_path)):

                # Create a unique document ID using the file name and chunk index
                doc_id = f"{filename}_chunk_{i+1}"

                # Insert chunk and its embedding into OpenSearch
                insert_document(client, index_name, doc_id, chunk)
                print(f"Inserted chunk {i+1} of file {filename} into index {index_name}")

def handle_user_query(query, client, agent_id):
    # Call RAG agent to execute query
    #results = search_by_neural(query, client, index_name, embedding_model_id)
    results = ""

    answer = rag_execute(query, client, agent_id)


    return answer,results

def format_results(results):
    # HTML table structure
    table = """
    <table border="1" style="width:100%; text-align: left;">
      <tr>
        <th>Document Name</th>
        <th>Context</th>
        <th>Score</th>
      </tr>
    """
    # Add rows to the table for each result
    for result in results:
        # Extract document name and chunk from doc_id
        doc_name = result['document']
        chunk = result['chunk']
        doc_url = f"{host}/get-pdf/{doc_name}"
        
        # Add the table row for each document
        table += f"""
        <tr>
          <td>{doc_name} (Chunk: {chunk})</a></td>
          <td>{result['context']}</td>
          <td>{result['score']}</td>
        </tr>
        """
    table += "</table>"
    
    return table


# Gradio function to be triggered from the interface
def gradio_function(query):

    host = os.getenv('CSS_HOST','localhost')
    port = os.getenv('CSS_PORT',9200)
    username = os.getenv('CSS_USER','admin')
    password = os.getenv('CSS_PASSWORD','admin')
    
    # Connect to OpenSearch
    client = create_opensearch_client(host, port, username, password)

    # Process the user query and return the LLM answer
    answer, relevant_documents = handle_user_query(query, client, ml_agent_id)
    
    document_table = format_results(relevant_documents)
    return answer, document_table
   # return answer, document_table

def create_gradio_ui():
    with gr.Blocks() as demo:
        gr.Markdown("### Query Search with LLM")

        query_input = gr.Textbox(label="Enter your query ")
        output_text = gr.Textbox(label="LLM Response")
        context_output = gr.HTML(label="Relevant Documents and Contexts")

        query_button = gr.Button("Submit")

       # query_button.click(fn=gradio_function, inputs=query_input, outputs=output_text)
        query_button.click(
            fn=gradio_function,  # Function to call
            inputs=[query_input],  # Inputs to the function
            outputs=[output_text, context_output]  # Outputs to display
        )

    return demo 

app = Flask(__name__)

# Route to serve the PDF file securely
@app.route('/get-pdf/<doc_name>')
def get_pdf(doc_name):
    # Assuming your PDF files are stored in a secure directory on the server
    pdf_path = os.path.join(folder_path, doc_name)
    
    if os.path.exists(pdf_path):
        return send_file(pdf_path, as_attachment=False)  # Sends the PDF to the frontend
    else:
        abort(404)  # Return a 404 if the file is not found


if __name__ == "__main__":
    
    host = os.getenv('CSS_HOST','localhost')
    port = os.getenv('CSS_PORT',9200)
    username = os.getenv('CSS_USER','admin')
    password = os.getenv('CSS_PASSWORD','admin')

    parser = argparse.ArgumentParser(description="Run the application with optional data loading.")
    
    # Define the load_data argument
    parser.add_argument(
        "--load_data",
        action="store_true",
        help="Include this flag to load data; omit it to skip data loading.",
    )
    
    # Parse command-line arguments
    #args = parser.parse_args()
    args, unknown = parser.parse_known_args()
    
    dimensions = 768  # Based on your embedding model

    # Connect to OpenSearch
    client = create_opensearch_client(host, port, username, password)

    #Register the connection 
    connector_id = register_connector(client)

    #register the embedding and inferencing model 
    inferencing_model_id, embedding_model_id = registerModel(client,connector_id)

    #create neural pipeline
    create_neural_pipeline(client, embedding_model_id)

    #register RAG Tool agent 
    ml_agent_id = create_mltool_agent(client, embedding_model_id, inferencing_model_id)

    # Create index for vector search with nmslib engine
    create_index_with_vector_field(client, index_name, dimensions)

    if (args.load_data):
    # Call the function and time its execution
        start_time = time.time()
        # Process folder and insert documents into OpenSearch
    
        process_pdf_folder_and_insert_to_opensearch(folder_path, client, index_name)
        end_time = time.time()

        # Calculate and print the duration
        execution_time = end_time - start_time
        print(f"The function took {execution_time:.2f} seconds to complete.")

    # Convert user query to vector and search in OpenSearch
    query = "What is the procedure to ingest data in COD ?"

    # Run the RAG agent with the query
    answer = rag_execute(query, client,ml_agent_id)

    # answer = query_llm(query,context)
    #answer = "Some Garbage"
    print("Answer:", answer)

    gradio_app = create_gradio_ui()
    gradio_app.launch()