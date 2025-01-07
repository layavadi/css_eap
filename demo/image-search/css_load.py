from config import Config
from opensearch_utils import OpenSearchUtils
import time


if __name__ == "__main__":
    
    # Connect to OpenSearch
    client = OpenSearchUtils()

    # Update ML settings in the cluster
    client.init_ml_settings()

    # # Create index for vector search with nmslib engine
    client.create_index_with_vector_field()

    # Call the function and time its execution
    start_time = time.time()

    client.insert_document()

    end_time = time.time()

    execution_time = end_time - start_time
    print(f"The function took {execution_time:.2f} seconds to complete the load.")

    # Convert user query to vector and search in OpenSearch
    query = "sunset"
    results = client.search_by_neural(query)

    print("Answer:", results)