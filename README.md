# DocuMind — Document Q&A Assistant

DocuMind is a document question-answering application that lets users upload PDF and TXT files, ask questions about their content, and view relevant source passages with page references.

The application uses keyword-based retrieval to find relevant document excerpts. With an Anthropic API key, Claude generates answers using the retrieved passages. Without an API key, the application runs in demo mode without making AI API calls.

Built as a learning and portfolio project using Python, FastAPI, SQLite, and HTML, CSS, and JavaScript.

## Features

- Upload PDF and TXT documents through a web interface.
- Extract text from PDFs with page references.
- Split documents into overlapping text chunks.
- Retrieve relevant passages using keyword-based ranking.
- Generate answers using Claude when configured.
- Run in demo mode without an API key.
- Display source excerpts and page references alongside answers.
- Validate file types, file sizes, empty files, and unreadable documents.
- Detect duplicate uploads.
- Delete individual documents or clear all stored documents.
- Provide REST API endpoints with validation and readable error responses.
- Run automated tests using pytest without making paid API calls.

## Tech Stack

- **Language:** Python 3.11+
- **Backend:** FastAPI, Pydantic
- **AI Integration:** Anthropic API
- **Document Processing:** pypdf
- **Database:** SQLite
- **Frontend:** HTML, CSS, JavaScript
- **Testing:** pytest

## Architecture

The application follows a modular structure that separates API routes, document processing, retrieval, answer generation, and storage.

### Request Flow

1. The user uploads a PDF or TXT document.
2. The backend validates the file and extracts its text.
3. The extracted text is divided into overlapping chunks.
4. The chunks and document metadata are stored in SQLite.
5. When a question is submitted, the retriever ranks relevant chunks using keyword matching.
6. The answerer returns a demo response or uses Claude to generate an answer from the retrieved excerpts.
7. The response includes the answer and its source passages.

## Project Structure

```text
documind/
├── app/
│   ├── application.py
│   ├── main.py
│   ├── config.py
│   ├── errors.py
│   ├── schemas.py
│   ├── routes.py
│   ├── extraction.py
│   ├── chunking.py
│   ├── retrieval.py
│   ├── llm.py
│   └── storage.py
├── static/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── sample_data/
│   └── synthetic_company_handbook.txt
├── tests/
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.txt
├── LICENSE
├── README.md
├── SETUP_GUIDE.md
└── PROJECT_CHECKLIST.md
```

## Getting Started

### Prerequisites

- Python 3.11 or newer
- Visual Studio Code (recommended)
- Git (optional, for cloning the repository)

### Installation on Windows

**1. Clone the repository**

```powershell
git clone https://github.com/pratikyadav0/documind.git
cd documind
```


Alternatively, download the repository ZIP and extract it.

**2. Create a virtual environment**

```powershell
python -m venv .venv
```

**3. Activate the virtual environment**

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, refer to `SETUP_GUIDE.md` for troubleshooting.

**4. Install dependencies**

```powershell
python -m pip install -r requirements.txt
```

**5. Configure environment variables**

```powershell
Copy-Item .env.example .env
```

Demo mode works without a real API key. To enable Claude mode, open `.env` and configure your Anthropic API key.


**6. Start the application**

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**7. Open the application**

Visit [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

Interactive API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) while the server is running.

For detailed Windows and VS Code instructions, see `SETUP_GUIDE.md`.

## Configuration

The application reads configuration from environment variables, with optional values loaded from `.env`.

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Enables Claude mode when configured with a valid key |
| `ANTHROPIC_MODEL` | Specifies the Anthropic model identifier |
| `ANTHROPIC_TIMEOUT_SECONDS` | Sets the AI request timeout |
| `DEMO_MODE` | Forces demo mode when set to `true` |
| `MAX_UPLOAD_MB` | Sets the maximum upload size |
| `CHUNK_SIZE` | Sets the maximum chunk size |
| `CHUNK_OVERLAP` | Sets the overlap between chunks |
| `TOP_K` | Sets the number of retrieved passages |
| `DATABASE_PATH` | Specifies the SQLite database location |
| `LOG_LEVEL` | Configures application logging |

Default values are defined in the application configuration. See `.env.example` for the available settings.

## Demo Mode and Claude Mode

**Demo mode**
- Works without an API key.
- Does not make calls to Anthropic.
- Returns a relevant retrieved passage with a demo-mode label.
- Is useful for testing the application locally.

**Claude mode**
- Requires a valid Anthropic API key.
- Uses Claude to generate answers from retrieved document excerpts.
- Returns source passages alongside the answer.
- Reports AI service errors rather than silently substituting demo responses.

Demo mode is intended to demonstrate retrieval functionality; it does not provide full AI-generated answers.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Check application status and mode |
| POST | `/api/documents` | Upload a PDF or TXT document |
| GET | `/api/documents` | List stored document metadata |
| DELETE | `/api/documents/{document_id}` | Delete a specific document |
| DELETE | `/api/documents` | Delete all stored documents |
| POST | `/api/ask` | Ask a question about uploaded documents |

FastAPI's interactive documentation at `/docs` allows you to explore and test these endpoints.

## Testing

Run the automated test suite from the project root:

```powershell
python -m pytest
```

The tests cover configuration, file validation, text extraction, chunking, retrieval, API endpoints, storage behaviour, duplicate detection, deletion, and mocked AI service interactions.

Tests use fake Claude clients and temporary databases, so they do not require paid Anthropic API calls.

For the exact verification status, see `PROJECT_CHECKLIST.md`.

## Retrieval Approach and Limitations

DocuMind currently uses keyword-based retrieval rather than semantic search.

- Query terms are matched against document chunks.
- Less common words receive greater weight.
- Retrieved passages are used to generate or demonstrate answers.
- PDF page references are retained for source attribution.

Current limitations include:

- No embedding-based semantic search or vector database.
- Synonyms and paraphrased questions may not retrieve the expected passages.
- Scanned PDFs without extractable text are not supported because OCR is not implemented.
- Complex PDF layouts, tables, and multi-column pages may be extracted imperfectly.
- Large document collections may require a more efficient retrieval index.

## Security and Privacy

- API keys are read on the backend and are not intentionally exposed to browser code.
- Uploaded filenames are sanitized before being used as display names.
- Document text is inserted into the interface as text rather than HTML.
- Retrieved document content is treated as untrusted input when passed to the language model.
- Uploaded file bytes are processed in memory during upload; extracted text and document metadata are stored in SQLite.

**Important:** This project is designed for local, single-user use. It does not currently include authentication, user-specific access controls, rate limiting, or production-grade deployment security. Do not expose the development server to the public internet or use confidential documents without appropriate security controls.

## Future Improvements

Potential improvements include:

- Semantic search using embeddings and a vector database.
- OCR support for scanned PDFs.
- Improved PDF table and layout extraction.
- Authentication and access control.
- More efficient indexing for larger document collections.
- Production deployment with HTTPS and additional security controls.

## Troubleshooting

If you encounter installation, dependency, environment configuration, or startup issues, refer to `SETUP_GUIDE.md`.

For information about tested functionality and outstanding limitations, see `PROJECT_CHECKLIST.md`.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
