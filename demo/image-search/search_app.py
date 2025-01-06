
from opensearch_utils import OpenSearchUtils
import gradio as gr
from config import Config
import os
from PIL import Image


# Function to handle image upload

def upload_images(images):
    for file in images:
        image = Image.open(file)
        image_name = os.path.basename(file)
        save_path = os.path.join(Config.DATA_FILE_PATH, image_name)
        image.save(save_path)

    # Update ML settings in the cluster
    client.init_ml_settings()

    # # Create index for vector search with nmslib engine
    client.create_index_with_vector_field()

    client.insert_document()


# Function to display image based on query

def display_image(query):
    result = client.search_by_neural(query)
    if result:
        return Image.open(Config.DATA_FILE_PATH + "/" + result)
    else:
        return "No image found for the given query."

def create_gradio_ui():
    with gr.Blocks() as demo:
        gr.Markdown("### CSS demo to search image based on text query")
        # Image upload section
        image_input = gr.File(label="Upload Images", file_count="multiple", file_types=["image"])

        upload_button = gr.Button("Upload Images")
        # Text input for query
        query_input = gr.Textbox(label="Enter your query", placeholder="Type image name or keyword...")
        # Output image
        output = gr.Image(label="Output Image", height=300, width="100%")

        # Define actions for buttons
        upload_button.click(fn=upload_images, inputs=image_input)
        query_input.submit(fn=display_image, inputs=query_input, outputs=output)

    return demo

if __name__ == "__main__":
    
    # Connect to OpenSearch
    client = OpenSearchUtils()

    try:
        gradio_app = create_gradio_ui()
        gradio_app.launch(share=True)
    except Exception as e:
        print(f"Error occurred: {e}")
