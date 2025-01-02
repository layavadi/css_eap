
import PyPDF2
import re
import os

class BatchLoader:
    def __init__(self, opensearch_utils):
        self.opensearch_utils = opensearch_utils


    # Function to read and chunk a PDF into text chunks
    def chunk_pdf(self, pdf_path, chunk_size=500):
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()

        text = re.sub(r'[\n\t\r]', ' ', text)  # Replace newlines, tabs, and carriage returns with a space
        text = re.sub(r' +', ' ', text)  # Replace multiple spaces with a single space

        # Split text into chunks of specified size (e.g., 500 characters)
        for i in range(0, len(text), chunk_size):
            yield text[i:i + chunk_size]


# Function to process all PDF files in a folder and insert into OpenSearch
    def load_data(self,folder_path):
        # Iterate over all PDF files in the folder
        for filename in os.listdir(folder_path):
            if filename.endswith(".pdf"):
                pdf_path = os.path.join(folder_path, filename)
                try:
                    # Iterate through chunks of the PDF
                    for i, chunk in enumerate(self.chunk_pdf(pdf_path)):

                        # Create a unique document ID using the file name and chunk index
                        doc_id = f"{filename}_chunk_{i+1}"

                        # Insert chunk and its embedding into OpenSearch
                        self.opensearch_utils.insert_document(doc_id, chunk)
                        print(f"Inserted chunk {i+1} of file {filename} ")
                except:
                    print("Exception during processing PDF")
