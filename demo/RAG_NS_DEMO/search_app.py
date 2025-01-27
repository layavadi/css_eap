
from opensearch_utils import OpenSearchUtils
import gradio as gr
import query_llm
from config import Config
import os


def handle_user_query(query, client):
    #query_vector = text_to_embedding(query)
    contexts = client.search_by_neural(query)

    index_mapping,index_settings = client.fetch_index_mapping(Config.INDEX_NAME)
    pipeline_definition = client.fetch_pipeline_definition(Config.NS_PIPELINE)

    if not contexts:
        return "No relevant information found."

    # Combine the text from the retrieved results
    context_text = " ".join([ctx['context'] for ctx in contexts])  # Join the retrieved contexts
    context_text = context_text[:1000]
    answer = query_llm.query_llm(query, context_text)


    return answer,contexts,index_mapping,index_settings,pipeline_definition

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

        
        # Add the table row for each document
        table += f"""
        <tr>
          <td>{doc_name} (Chunk: {chunk})</td>
          <td>{result['context']}</td>
          <td>{result['score']}</td>
        </tr>
        """
    table += "</table>"
    
    return table


# Gradio function to be triggered from the interface
def gradio_function(query):


    # Connect to OpenSearch
    client = OpenSearchUtils()

    # Process the user query and return the LLM answer
    answer, relevant_documents,index_mapping,index_settings, piepline_definition = handle_user_query(query, client)
    
    document_table = format_results(relevant_documents)


    # Format outputs as HTML
    mapping_str = f"<pre style='white-space: pre; overflow-x: auto; max-width: 100%; border: 1px solid #ddd; padding: 10px;'>{index_mapping}</pre>"
    settings_str = f"<pre style='white-space: pre; overflow-x: auto; max-width: 100%; border: 1px solid #ddd; padding: 10px;'>{index_settings}</pre>"
    pipeline_str = f"<pre style='white-space: pre; overflow-x: auto; max-width: 100%; border: 1px solid #ddd; padding: 10px;'>{piepline_definition}</pre>"


    return answer, document_table,mapping_str,settings_str, pipeline_str

   # return answer, document_table

def create_gradio_ui():
    with gr.Blocks() as demo:
        gr.Markdown("### CSS Neural Query Search RAG  DEMO  with LLM")

        query_input = gr.Textbox(label="Enter your query ")
     
        gr.Markdown("### CSS Index Details")

        with gr.Row():
            col1 = gr.Markdown("**Index Mapping**")
            col2 = gr.Markdown("**Index Settings**")
            col3 = gr.Markdown("**Neural Search Pipeline**")

        with gr.Row():
            index_mapping_output = gr.HTML()
            index_settings_output = gr.HTML()
            pipeline_output = gr.HTML()

        output_text = gr.Textbox(label="LLM Response")
        context_output = gr.HTML(label="Relevant Documents and Contexts")

        query_button = gr.Button("Submit")

       # query_button.click(fn=gradio_function, inputs=query_input, outputs=output_text)
        query_button.click(
            fn=gradio_function,  # Function to call
            inputs=[query_input],  # Inputs to the function
            outputs=[output_text, context_output,index_mapping_output,index_settings_output,pipeline_output]  # Outputs to display
        )

    return demo 



if __name__ == "__main__":
    
    # Connect to OpenSearch
    client = OpenSearchUtils()


    try:
        gradio_app = create_gradio_ui()
        gradio_app.launch(server_port=int(os.getenv("CDSW_APP_PORT","7860")),share=True)
    except Exception as e:
        print(f"Error occurred: {e}")
