This program processes images in a specified location, stores them in an Cloudera Semantic Search(CSS) with vector embeddings, and enables to search the images as per user's query.

- **This demo needs nodes having following roles**
    - data
    - ingest
    - ml


## Requirements
- **Python 3.8+**
- **Cloudera Semantic Search  server with endpoints

## Environment Variables
Set the following environment variables in your shell or `.env` file before running the program.

- **CSS Connection**  
  - `CSS_HOST`: Host address of the Cloudera Semantic Search server (default: `localhost`)
  - `CSS_PORT`: Port of the OpenSearch server (default: `9200`)
  - `CSS_USER`: Username for OpenSearch authentication
  - `CSS_PASSWORD`: Password for OpenSearch authentication
  - `DATA_FILE_PATH`: PDF files to load (default: `./data`)
  - `CSS_SSL`:  True if SSL is enabled for CSS connection
  

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
   - Process and store images from the specified directory. Currently there is one only one image in the directory. One can add more to the same directory.

   Start the following Application for brining up the search UI:
   ```python
   python search_app.py 
   ```

    Run  the following Application to do cleanup of index:
   ```python
   python clenaup.py 
   ```
   This will:
   - Connect to CSS
   - Deletes index.

## Usage
- **Querying the System**:
   - The Gradio UI provides an interface for users to upload images. Upon submission, it:
     1. Creates the index in opensearch if not exists.
     2. Generate the embeddings of images uploaded and add them as document to opensearch.
     3. Whenever user enters the query to search the image, embeddings are generated for that text and performs neural search with the embeddings of image.
     4. Displays the search result as image in the UI.





