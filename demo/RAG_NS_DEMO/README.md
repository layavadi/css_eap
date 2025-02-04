This program processes PDF documents in a specified location, stores them in an Cloudera Semantic Search(CSS) with vector embeddings, and enables users to query the data with a pre-trained language model, using CSS for search and retrieval and Azure OpenAI for generating responses based on the retrieved context. Embedding is generated with in CSS using Neural search pipeline feature. 

- **This demo needs nodes having following roles**
    - data
    - ingest
    - ml
Make sure to turn off the security check for system indices in opensearch.yml by setting
`plugins.security.system_indices.enabled: false`

## Requirements
- **Python 3.8+**
- **Cloudera Semantic Search  server with endpoints 
- **Azure OpenAI** credentials for query processing with the LLM

## Environment Variables
Set the following environment variables in your shell or `.env` file before running the program.

- **CSS Connection**  
  - `CSS_HOST`: Host address of the Cloudera Semantic Search server (default: `localhost`)
  - `CSS_PORT`: Port of the OpenSearch server (default: `9200`)
  - `CSS_USER`: Username for OpenSearch authentication
  - `CSS_PASSWORD`: Password for OpenSearch authentication
  - `DATA_FILE_PATH`: PDF files to load (default: `./data`)
  - `CSS_OPENAI_KEY`: Azure OpenAI key 
  - `CSS_OPENAI_VERSION` : OpenAI model version
  - `CSS_OPENAI_MODEL` : OpenAI model for LLM Chat
  - `CSS_OPENAI_ENDPOINT` : OpenAI model servicing Endpoint
  - `CSS_SSL`:  True if SSL is enabled for CSS connection
   - `CSS_INDEX_NAME` : Index name of vectors 
  - `CSS_NS_PIPELINE`:  Name of Neural pipeline
  

2. **Install Dependencies**:
   Install the necessary packages by running:
   ```bash
   pip3 install -r session-install-deps/requirements.txt
   ```

## Running the Program
1. **Start the OpenSearch Server**:
   Ensure your Cloudera Semantic search  server is running and accessible at the host and port specified in the environment variables.

2. **Run the Script**:
   Start the following job for loading the data:
   ```python
   python css_load.py 
   ```
   This will:
   - Connect to CSS
   - Process and store PDF documents from the specified directory. Currently there is one Cloudera Operationa Database document in the PDF format. One can add more to the same directory.

   Start the following Application for brining up the search UI:
   ```python
   python search_app.py 
   ```

    RUn  the following Application to do cleanup of index , neural pipeline and model:
   ```python
   python clenaup.py 
   ```
   This will:
   - Connect to CSS
   - Deletes index, neural pipeline, undeploys and deletes the embedding model.

## Usage
- **Querying the System**:
   - The Gradio UI provides an interface for users to enter a query. Upon submission, it:
     1. Converts the query into a vector and searches for similar document chunks in CSS through neural search feature of CSS.
     2. Feeds the retrieved context to Azure OpenAI to generate an answer.
     3. Displays the answer along with chunks  of  the original document chunks.
     4. Displays Index settings, mappings and neural pipeline definitions used.





