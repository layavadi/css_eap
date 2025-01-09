from opensearchpy import OpenSearch
from config import Config
from opensearchpy.helpers import bulk

import os
import clip
import torch
from PIL import Image


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
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model, self.preprocess = clip.load(Config.CSS_EMBEDDING_MODEL, device=self.device)
        except Exception as e:
            print(f"Error connecting to OpenSearch: {e}")
            self.clinet = ''

    def init_ml_settings(self):
        # This settings enable ML workloads to run without any memory limit tripping.
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

    # Create the index doing the mapping between text and embeddings
    def create_index_with_vector_field(self):

        if self.client.indices.exists(index=Config.INDEX_NAME):
            print(f"Index '{Config.INDEX_NAME}' already exists.")
        else:
            index_body = Config.INDEX_SETTINGS
            self.client.indices.create(index=Config.INDEX_NAME, body=index_body)
            print(f"Index '{Config.INDEX_NAME}' created successfully.")

    # Step 3: Insert Embeddings and Text into OpenSearch
    def insert_document(self, image_paths):
        batch_size = 100
        data = []
        # Process images in batches
        for i in range(0, len(image_paths), batch_size):
            batch_file_paths = image_paths[i:i + batch_size]

            # Compute embeddings for the batch of images
            batch_embeddings = self.compute_clip_features(batch_file_paths)

            # Create data dictionary for indexing
            for file_path, embedding in zip(batch_file_paths, batch_embeddings):
                data.append({'image_path': file_path, 'embedding': embedding})

            # Check if we have enough data to index
            if len(data) >= batch_size:
                self.index_embeddings_to_opensearch(data)
                data = []

        # Index any remaining data
        if len(data) > 0:
            self.index_embeddings_to_opensearch(data)

        print("All embeddings indexed successfully.")

    def search_by_neural(self, query, top_k=1):
        vector = self.get_single_embedding(query)

        body = {
            "query": {
                "knn": {
                    "embedding": {
                        "vector": vector.tolist(),  # Convert to list
                        "k": top_k  # Number of nearest neighbors to retrieve
                    }
                }
            }
        }

        # Perform search
        result = self.client.search(index=Config.INDEX_NAME, body=body)
        # Check if hits are present in the result
        if 'hits' in result and 'hits' in result['hits']:
            hits = result['hits']['hits']
            # Extract image_path from the first hit
            if hits:
                image_path = hits[0]['_source']['image_path']
                print(os.path.basename(image_path) + " score: " + str(hits[0]['_score']))
                # Display the image
                return image_path
            else:
                print("No hits found in the result.")
        else:
            print("Invalid result format or no hits found.")

    def index_embeddings_to_opensearch(self, data):
        actions = []
        i=1
        for d in data:
            action = {
                "id": i,
                "_index": Config.INDEX_NAME,  # Update with your index name
                "_source": {
                    "image_path": d['image_path'],
                    "embedding": d['embedding'].tolist()
                }
            }
            i+=1
            actions.append(action)
        success, _ = bulk(self.client, actions, index=Config.INDEX_NAME)
        print(f"Indexed {success} embeddings to OpenSearch")

    def compute_clip_features(self, photos_batch):
        # Load all the photos from the files
        photos = [Image.open(photo_file) for photo_file in photos_batch]

        # Preprocess all photos
        photos_preprocessed = torch.stack([self.preprocess(photo) for photo in photos]).to(self.device)

        with torch.no_grad():
            # Encode the photos batch to compute the feature vectors and normalize them
            photos_features = self.model.encode_image(photos_preprocessed)
            photos_features /= photos_features.norm(dim=-1, keepdim=True)

        # Transfer the feature vectors back to the CPU and convert to numpy
        return photos_features.cpu().numpy()

    def get_single_embedding(self, text):
        with torch.no_grad():
            # Encode the text to compute the feature vector and normalize it
            text_input = clip.tokenize([text]).to(self.device)
            text_features = self.model.encode_text(text_input)
            text_features /= text_features.norm(dim=-1, keepdim=True)

        # Return the feature vector
        return text_features.cpu().numpy()[0]

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