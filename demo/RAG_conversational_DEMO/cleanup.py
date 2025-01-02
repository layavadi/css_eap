from config import Config
from opensearch_utils import OpenSearchUtils


# Cleanup function
def cleanup():
    print("Cleaning up resources...")

    client = OpenSearchUtils()
    #Clenaup index
    client.check_and_delete_index()

    #Cleanup pipeline
    client.delete_neural_search_pipeline()

    #undeploy model if depkloyed
    
    client.undeploy_and_delete_model()

    client.delete_connector()

    client.delete_mltool()

if __name__ == "__main__":
    cleanup()
    print("Cleanup complected")
