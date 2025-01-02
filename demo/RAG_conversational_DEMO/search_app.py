
from opensearch_utils import OpenSearchUtils
import gradio as gr
from config import Config


# Connect to OpenSearch
client = OpenSearchUtils()

def handle_user_query(query):

    global client
    index_mapping,index_settings = client.fetch_index_mapping(Config.INDEX_NAME)
    pipeline_definition = client.fetch_pipeline_definition(Config.NS_PIPELINE)

    ml_tool_id = client.mltool_exists_by_name(Config.CSS_ML_TOOL_NAME)
    ml_tool_definition = client.fetch_mltool_definition(ml_tool_id)

    ml_embedding_model_definition = client.fetch_model_definition(Config.CSS_EMBEDDING_MODEL)
    ml_inference_model_definition = client.fetch_model_definition(Config.CSS_INFERENCING_MODEL)

    ml_embedding_connector_definition = client.fetch_connector_definition(Config.CSS_CONNECTOR_NAME_EMBEDDING)
    ml_inferencing_connector_definition = client.fetch_connector_definition(Config.CSS_CONNECTOR_NAME_INFERECING)
    answer = client.rag_execute(query, ml_tool_id)


    return answer,ml_tool_definition,index_mapping,index_settings,pipeline_definition, ml_embedding_model_definition,ml_inference_model_definition,ml_embedding_connector_definition,ml_inferencing_connector_definition



# Gradio function to be triggered from the interface
def gradio_function(query):


    # Connect to OpenSearch
    global client

    # Process the user query and return the LLM answer
    answer, mltool_definition,index_mapping,index_settings, piepline_definition,embdding_model,inferencing_model, embedding_connector, inferencing_connector = handle_user_query(query)
    


    # Format outputs as HTML
    mapping_str = f"<pre style='white-space: pre; overflow-x: auto; max-width: 100%; border: 1px solid #ddd; padding: 10px;'>{index_mapping}</pre>"
    settings_str = f"<pre style='white-space: pre; overflow-x: auto; max-width: 100%; border: 1px solid #ddd; padding: 10px;'>{index_settings}</pre>"
    pipeline_str = f"<pre style='white-space: pre; overflow-x: auto; max-width: 100%; border: 1px solid #ddd; padding: 10px;'>{piepline_definition}</pre>"
    mltool_definition_str = f"<pre style='white-space: pre; overflow-x: auto; max-width: 100%; border: 1px solid #ddd; padding: 10px;'>{mltool_definition}</pre>"
    
    embed_model_definition_str = f"<pre style='white-space: pre; overflow-x: auto; max-width: 100%; border: 1px solid #ddd; padding: 10px;'>{embdding_model}</pre>"
    inferencing_model_str  = f"<pre style='white-space: pre; overflow-x: auto; max-width: 100%; border: 1px solid #ddd; padding: 10px;'>{inferencing_model}</pre>"
    embedding_connector_str = f"<pre style='white-space: pre; overflow-x: auto; max-width: 100%; border: 1px solid #ddd; padding: 10px;'>{embedding_connector}</pre>"
    inferencing_connector_str = f"<pre style='white-space: pre; overflow-x: auto; max-width: 100%; border: 1px solid #ddd; padding: 10px;'>{inferencing_connector}</pre>"

    memory_id_str = f"<pre style='white-space: pre; overflow-x: auto; max-width: 100%; border: 1px solid #ddd; padding: 10px;'>{client.memory_id}</pre>"

    return answer, mltool_definition_str,mapping_str,settings_str, pipeline_str, embed_model_definition_str, inferencing_model_str, embedding_connector_str, inferencing_connector_str, memory_id_str

   # return answer, document_table

def create_gradio_ui():
    with gr.Blocks() as demo:
        gr.Markdown("### CSS  RAG  DEMO  with external  Embedding and LLM Models running through ML Tool ###")

        query_input = gr.Textbox(label="Enter your query ")
        output_text = gr.Textbox(label="LLM Response")
        query_button = gr.Button("Submit")

        gr.Markdown("### CSS Index Details")

        with gr.Row():
            col1 = gr.Markdown("**Index Mapping**")
            col2 = gr.Markdown("**Index Settings**")
            col3 = gr.Markdown("**Neural Search Pipeline**")

        with gr.Row():
            index_mapping_output = gr.HTML()
            index_settings_output = gr.HTML()
            pipeline_output = gr.HTML()


        with gr.Row():
            col1 = gr.Markdown("**ML Embedding model Connector Definition**")
            col2 = gr.Markdown("**ML Inferencing Model Connector Definition**")
        with gr.Row():
            embed_connector = gr.HTML()
            infer_connector = gr.HTML()

        with gr.Row():
            col1 = gr.Markdown("**ML Embedding model Definition**")
            col2 = gr.Markdown("**ML Inferencing Model  Definition**")
        with gr.Row():
            embed_model = gr.HTML()
            inference_model = gr.HTML()

        with gr.Row():
            col1 = gr.Markdown("**ML Tool Definition**")

        with gr.Row():
            ml_tool_output = gr.HTML()

        with gr.Row():
            col1 = gr.Markdown("**ML Conversational Memory ID**")

        with gr.Row():
            memory_id = gr.HTML()

       # query_button.click(fn=gradio_function, inputs=query_input, outputs=output_text)
        query_button.click(
            fn=gradio_function,  # Function to call
            inputs=[query_input],  # Inputs to the function
            outputs=[output_text, ml_tool_output,index_mapping_output,index_settings_output,pipeline_output, embed_model,inference_model, embed_connector, infer_connector,memory_id]  # Outputs to display
        )

    return demo 



if __name__ == "__main__":
  
    try:
        gradio_app = create_gradio_ui()
        gradio_app.launch(share=True)
    except Exception as e:
        print(f"Error occurred: {e}")
