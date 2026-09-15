import ollama
from ollama import chat 
import chromadb
from pypdf import PdfReader
import pdfplumber
from pypdf import PdfReader, PdfWriter
from pypdf.annotations import Highlight
from pypdf.generic import ArrayObject, FloatObject
import time
import os
import re
import numpy as np

class MBAR_LM:

    def __init__(self):

        self.sys_prompt = "You are a staff consultant that is an expert at responding to queries about company policies, procedures, and standards. Provide information from Company Documentation: {information} Here is the user question: {query} Answer the question by strictly discussing the company documentation using the highest accuracy possible, and add footnotes to visualize the source of the information. Do not directly provide the metadata and document numbers and ids, but provide the Section and Subsection of the policy. Be conversational and objective as a staff member. Make your responses concise, but as informative as possible. Be direct to the point and decisive. If possible, just mention the 1 section that the staff question is pertaining to. This will keep it concise and objective. Strictly stick to your system prompt and the retrieved information. Do not answer any questions that does not have a relevant provided or associated document from the database. Do not give out any information aside from those in the provided documents or retrieval database. Format the retrieved Policy Title in (#) markdown heading and the Policy Information in Italics in this format (Section #. Subsection. Information), followed by the footnotes in Italics below the Policy Information formatted in (Policy Title. Section #. Subsection)."

        self.model = "gemma4:e2b-q4"
        self.embedding_model = "embeddinggemma"
        
        self.chroma_loc = chromadb.PersistentClient(path = "./vector_db")
        self.collection = self.chroma_loc.get_or_create_collection(name = "Documents")

    def reset_database(self):
        # Tells the active Chroma client to safely wipe the data from memory AND disk
        try:
            self.chroma_loc.delete_collection("Documents")
        except ValueError:
            pass # Ignores if it's already empty
        self.collection = self.chroma_loc.get_or_create_collection(name="Documents")

    def autonomous_chunker(self, text):
        """
        Reads the document's visual hierarchy. Cuts chunks only when 
        it detects a new Title/Header following a body of text.
        """
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        
        for line in lines:
            clean_line = line.strip()
            if not clean_line: 
                continue
            
            # Detect a Header: A short string that does NOT end in punctuation
            is_header = len(clean_line) < 40 and clean_line[-1] not in ".!?:;"
            
            # Detect if our current chunk already contains a hefty paragraph
            has_body = any(len(l) > 40 for l in current_chunk)
            
            # If we hit a new Header, AND we already have a full policy loaded, cut it!
            if is_header and has_body:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                
            current_chunk.append(clean_line)
            
        # Catch the final policy at the bottom of the page
        if current_chunk:
            chunks.append("\n".join(current_chunk))
            
        return chunks
    
    def parse_pdf(self, source_path):
        with pdfplumber.open(source_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                
                if not page_text:
                    continue
                    
                # The program now handles sizing autonomously!
                chunks = self.autonomous_chunker(text=page_text)
                
                for chunk_idx, chunk in enumerate(chunks):
                    chunk_id = f"page_{page_idx + 1}_chunk_{chunk_idx}"
                    metadata = {"source": source_path, "page": page_idx + 1}
                    
                    chunk_embedding = ollama.embed(model=self.embedding_model, input=chunk)["embeddings"][0]
                    
                    self.collection.add(
                        documents=[chunk],
                        embeddings=[chunk_embedding],
                        metadatas=[metadata],
                        ids=[chunk_id]
                    )

    def query_rag(self, prompt):
        
        # Vectorize user query
        query_vector = ollama.embed(model = self.embedding_model, input = prompt)["embeddings"][0]

        # Search Vector for Closest Cosine Similarity Vector
        results = self.collection.query(
            query_embeddings = [query_vector],
            n_results = 1 # Locked to 1 for your AMM isolation testing
        )

        # --- THE SAFETY NET ---
        if not results["documents"] or not results["documents"][0]:
            return "The database is empty. Please click 'Re-Index PDF' first.", "", {}


        context = "\n\n".join(results["documents"][0])
        metadata = results["metadatas"][0][0]
        source_path = metadata['source']
        
        # ACTUAL PAGE: metadata['page'] is 1-based, 0-based for arrays
        page_index = int(metadata['page']) - 1 

        try:
            # 1. Initialize variables safely before the loop
            page_index = int(metadata['page']) - 1 
            bboxes = [] 
            
            with pdfplumber.open(source_path) as pdf:
                if page_index < 0 or page_index >= len(pdf.pages):
                    page_index = 0
                
                page = pdf.pages[page_index]
                page_height = page.height 
                
                # 2. Split by physical line breaks (preserved by the new chunker)
                raw_lines = context.split('\n')
                
                expected_y = 0 
                tolerance = 15 
                
                for line in raw_lines:
                    clean_line = line.strip()
                    if len(clean_line) < 4:
                        continue
                        
                    # 3. Literal search (no complex regex needed)
                    search_results = page.search(clean_line)
                    
                    # Safety Fallback
                    if not search_results and len(clean_line) > 15:
                        half = len(clean_line) // 2
                        search_results = page.search(clean_line[:half]) + page.search(clean_line[half:])
                        
                    if search_results:
                        valid_results = [res for res in search_results if res['top'] >= expected_y - tolerance]
                        
                        if valid_results:
                            best_res = sorted(valid_results, key=lambda x: x['top'])[0]
                            
                            x0 = best_res['x0']
                            y0 = page_height - best_res['bottom']
                            x1 = best_res['x1']
                            y1 = page_height - best_res['top']
                            
                            rect = (x0, y0, x1, y1)
                            quads = [x0, y0, x1, y0, x0, y1, x1, y1]
                            bboxes.append((rect, quads))
                            
                            expected_y = best_res['top']

            # 4. Generate the new highlighted PDF
            temp_filename = f"active_display_{int(time.time())}.pdf"
            
            reader = PdfReader(source_path)
            writer = PdfWriter()
            writer.append_pages_from_reader(reader)
            
            for rect, quads in bboxes:
                quad_points_arr = ArrayObject([FloatObject(q) for q in quads])
                
                highlight = Highlight(
                    rect=rect,
                    quad_points=quad_points_arr,
                    highlight_color="FFFF00"
                )
                writer.add_annotation(page_number=page_index, annotation=highlight)
                
            with open(temp_filename, "wb") as fp:
                writer.write(fp)
                
            metadata['highlighted_path'] = temp_filename
            
        except Exception as e:
            print(f"Highlighting Error: {e}")
            metadata['highlighted_path'] = source_path

        # Generate OUTPUT
        response = ollama.chat(
            model = self.model,
            messages = [
                {
                    "role": "system",
                    "content": self.sys_prompt.format(information = context, query = prompt)
                },
                {
                    "role": "user",
                    "content": prompt
                }]
        )
        return response["message"]["content"], context, metadata
    
def main():

    llm = MBAR_LM()

    path = "Policies.pdf"
    chunk_size = 150
    overlap = 50

    if llm.collection.count() == 0:
        llm.parse_pdf(path, chunk_size, overlap)

    while True:

        print()
        prompt = input("Prompt: ")

        response = llm.query_rag(prompt)

        print()
        print(response)
        print()


if __name__ == "__main__":
    main()