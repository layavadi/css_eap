from config import Config
from opensearch_utils import OpenSearchUtils


# Cleanup function
def cleanup():
    print("Cleaning up resources...")

    client = OpenSearchUtils()
    #Clenaup index
    client.check_and_delete_index()

if __name__ == "__main__":
    cleanup()
    print("Cleanup complected")
