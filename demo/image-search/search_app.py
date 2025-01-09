from opensearch_utils import OpenSearchUtils
import gradio as gr
from PIL import Image

def upload_images(images):
    image_paths = []

    for file in images:
        image_paths.append(file.name)

    # Update ML settings in the cluster
    client.init_ml_settings()

    # Create index for vector search with nmslib engine
    client.create_index_with_vector_field()

    client.insert_document(image_paths)
    loading_text = "Images indexed successfully, you can search them now"

    return loading_text


# Function to display image based on query

def display_image(query):
    result = client.search_by_neural(query)
    if result:
        return Image.open(result)
    else:
        return "No image found for the given query."

def create_gradio_ui():
    with gr.Blocks() as demo:
        gr.Markdown("### CSS demo to search image based on text query")
        # Image upload section
        image_input = gr.File(label="Upload Images", file_count="multiple", file_types=["image"])

        upload_button = gr.Button("Upload Images")

        loading_label = gr.Label("")
        # Text input for query
        query_input = gr.Textbox(label="Enter your query", placeholder="Input the text and then press Enter.")
        # Output image
        output = gr.Image(label="Output Image", height=300, width="100%")

        # Define actions for buttons
        upload_button.click(fn=upload_images, inputs=image_input, outputs=[loading_label])
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
