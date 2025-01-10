
import PyPDF2
import re
import os

class BatchLoader:
    def __init__(self, opensearch_utils):
        self.opensearch_utils = opensearch_utils


    # Function to read and chunk a PDF into text chunks
    def get_text_from_pdf(self, pdf_path, chunk_size=500):
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()

        text = re.sub(r'[\n\t\r]', ' ', text)  # Replace newlines, tabs, and carriage returns with a space
        text = re.sub(r' +', ' ', text)  # Replace multiple spaces with a single space
        # Replace consecutive periods with a single period
        text = re.sub(r'\.{2,}', '.', text)  # Match two or more consecutive periods and replace with a single period

        return text


# Function to process all PDF files in a folder and insert into OpenSearch
    def load_data(self,folder_path):
        # Iterate over all PDF files in the folder
        total_text_bytes = 0  # Initialize total text bytes counter
        for filename in os.listdir(folder_path):
            if filename.endswith(".pdf"):
                pdf_path = os.path.join(folder_path, filename)
                try:
                    # Get the text from the PDF
                    text = self.get_text_from_pdf(pdf_path)

                    # Create a unique document ID using the file name and chunk index
                    doc_id = filename

                     # Insert chunk and its embedding into OpenSearch
                    self.opensearch_utils.insert_document(doc_id, text)
                    text_size = len(text.encode('utf-8'))
                    total_text_bytes += text_size  # Update the total text bytes counter
                    print(f"Inserted data for  file {filename} ")
                except:
                    print("Exception during processing PDF")
        print (f"Total bytes inserted : {total_text_bytes/ (1024 ** 2)} MB")
