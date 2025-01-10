from config import Config
from opensearch_utils import OpenSearchUtils
from data_loader import BatchLoader
import time


if __name__ == "__main__":
    
    # Connect to OpenSearch
    client = OpenSearchUtils()

    # Update ML settings in the clustger 
    client.init_ml_settings()
    
    #register the Embedding model  which is deployed in CSS
    client.register_embedding_model()

    #register connector for embedding model
    inferencing_connector_id = client.register_connector(Config.CSS_CONNECTOR_NAME_INFERECING, Config.CONNECTOR_FOR_INFERENCING_BODY)

    #register the Inferencing model 
    client.register_LLM_model(inferencing_connector_id)

    #create neural pipeline
    client.create_neural_pipeline()

    #register RAG Tool agent 
    ml_agent_id = client.create_mltool_agent(client.embedding_model_id, client.inferencing_model_id)

    # Create index for vector search with nmslib engine
    client.create_index_with_vector_field()

    batch_loader = BatchLoader(client)
    
    # Call the function and time its execution
    start_time = time.time()
    # Process folder and insert documents into OpenSearch
    batch_loader.load_data(Config.DATA_FILE_PATH)
    end_time = time.time()

    # Calculate and print the duration
    execution_time = end_time - start_time
    print(f"The function took {execution_time:.2f} seconds to complete the load.")

    # Execute the RAG inside opensearch buy sending the query
    query = "What is the procedure to ingest data in COD ?"
    answer = client.rag_execute(query,ml_agent_id)

    print("Answer:", answer)

    query = "While ingesting data to  COD what care need to be taken ?"
    answer = client.rag_execute(query,ml_agent_id)

    print("Answer:", answer)