# Hierarchical Deterministic Search

A local PDF question-answering experiment. It splits policy text using heading heuristics, retrieves a matching chunk from Chroma, and asks Gemma to answer with the source context. The Streamlit interface also shows the source PDF and highlights retrieved text.

**Instructions:**

1. Install Python and [Ollama](https://ollama.com/download), then clone the repository:

```sh
git clone https://github.com/estradagenreid-ph/hierarchical_deterministic_search.git
cd hierarchical_deterministic_search
python -m venv .venv
```

2. Install the Python dependencies using the virtual environment.

Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

macOS/Linux:

```sh
./.venv/bin/python -m pip install -r requirements.txt
```

3. Start Ollama. Open its desktop app, or run `ollama serve` in a separate terminal if the service is not already running. Download the two models used in `main.py`:

```sh
ollama pull gemma4:e2b-q4
ollama pull embeddinggemma
ollama list
```

The model names must match `self.model` and `self.embedding_model` in `main.py`. If a tag is unavailable, use an available compatible model and update the corresponding setting. Changing the embedding model requires rebuilding the index.

4. Keep `Policies.pdf` in the repository root and launch the interface from that folder.

Windows:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

macOS/Linux:

```sh
./.venv/bin/python -m streamlit run app.py
```

5. Open the local address printed by Streamlit, click **Re-Index PDF**, then ask a question about the document. Re-indexing replaces the current Documents collection. Use a text-based PDF; there is no OCR step.

**FILES:**

| File | What it does |
| --- | --- |
| `app.py` | Streamlit chat, re-index action, source viewer, and enlarged PDF dialog. |
| `main.py` | `MBAR_LM` backend: heading-based chunking, Ollama embeddings, Chroma retrieval, PDF highlighting, and Gemma responses. |
| `Modelfile` | Optional Ollama model configuration. The app does not load it automatically. Its base tag and GPU/context settings may need adjusting for your machine. |
| `Policies.pdf` | Source document read by the app. Replace it only with material you have permission to use. |
| `Policies.docx` | Companion source document; the app reads the PDF rather than this file. |
| `requirements.txt` | Python packages needed by the interface and backend. |
| `vector_db/` | Local Chroma database generated during indexing. |
| `active_display_*.pdf` | Generated copies of the source PDF with retrieval highlights. |

**OLLAMA & AI TOOLS:**

Ollama must be installed and running separately; installing its Python package alone does not start the model service. Gemma generates answers, and EmbeddingGemma produces the document and query embeddings. This local path does not require a cloud API key. Downloading models requires internet access.

Ollama is [open-source software](https://github.com/ollama/ollama/blob/main/LICENSE). The models have their own terms and hardware requirements.

Gemini, ChatGPT, and Codex helped me develop this project. The source code calls Ollama at runtime; it does not call the Gemini or ChatGPT APIs. Codex also helped with this README and repository cleanup.

**CURRENT LIMITS:**

The chunk-size and overlap controls are displayed but are not passed to the current heading-based parser. Retrieval currently selects one chunk. Run `app.py` through Streamlit: the standalone `main.py` command-line path still calls `parse_pdf` with an outdated argument list and needs a separate fix.

**LOCAL DATA:**

`.gitignore` covers new generated indexes, highlighted PDFs, caches, and secrets. The existing `vector_db/` is intentionally retained and remains tracked, so Git can still commit changes to those files. An index can contain document text. Review it before publishing; ignore rules do not remove tracked files or erase earlier commits.

**Useful links:**

- [Ollama CLI](https://docs.ollama.com/cli)
- [Chroma documentation](https://docs.trychroma.com/)
- [Streamlit documentation](https://docs.streamlit.io/)
- [pdfplumber](https://github.com/jsvine/pdfplumber)
- [pypdf documentation](https://pypdf.readthedocs.io/)
- [Streamlit PDF Viewer](https://github.com/lfoppiano/streamlit-pdf-viewer)
