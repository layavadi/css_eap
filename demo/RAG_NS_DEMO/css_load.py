from config import Config
from opensearch_utils import OpenSearchUtils
from data_loader import BatchLoader
import time
import query_llm


if __name__ == "__main__":
    
    # Connect to OpenSearch
    client = OpenSearchUtils()

    # Update ML settings in the clustger 
    client.init_ml_settings()
    
    #register the model 
    client.registerModel()

    #create neural pipeline
    client.create_neural_pipeline()

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

    # Convert user query to vector and search in OpenSearch
    query = "What is the procedure to ingest data in COD ?"
    results = client.search_by_neural(query)

    # # Combine retrieved text and send to LLM
    context = " ".join([ctx['context'] for ctx in results])
    context = context[:1000]
    answer = query_llm.query_llm(query,context)
    print("Answer:", answer)