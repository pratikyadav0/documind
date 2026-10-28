# DocuMind Setup Guide (Windows 10/11, VS Code, PowerShell)

This guide is for someone who may be new to running a Python project. Follow the steps in order.
Every command is typed into the **VS Code terminal** while the **project folder** is the current folder.

---

## What DocuMind does

You upload a PDF or TXT file. You then ask a question about it, for example "How many vacation days do employees get?"
DocuMind finds the passages that best match your question and shows them as sources, with page numbers for PDFs.

- **Demo mode (default):** no API key needed. Answers are generated locally, and the page says so clearly.
- **Claude mode (optional):** with your own Anthropic API key, Claude writes the answer using only the passages.

---

## STEP 1: Install the required software

You need **Python 3.11 or newer** and **Git**. You also need **VS Code**.

### Check Python

Open PowerShell (press the Windows key, type `PowerShell`, press Enter) and run:

```powershell
python --version
```

Expected: `Python 3.11.x` or higher (for example `Python 3.12.4`).

If you see "Python was not found", or the Microsoft Store opens:

1. Download Python 3.12 from <https://www.python.org/downloads/windows/>.
2. Run the installer and tick **Add python.exe to PATH** on the first screen.
3. Click **Install Now**, then close and reopen PowerShell and VS Code.
4. Run `python --version` again.

### Check Git

```powershell
git --version
```

Expected: `git version 2.x.x`. If it is missing, install Git from <https://git-scm.com/download/win>, keep the default options, then reopen VS Code.

### VS Code

Download VS Code from <https://code.visualstudio.com>. The Microsoft **Python** extension is optional but helpful.

---

## STEP 2: Extract the ZIP and open the project folder

1. Find the file `documind.zip` in your Downloads folder.
2. Right-click it and choose **Extract All...**, then click **Extract**.
   This creates a folder called `documind`. Choose a location you will remember, for example `C:\Users\<YourName>\Projects`.
3. Open VS Code and choose **File > Open Folder...**.
4. Select the **`documind`** folder itself (the one that directly contains `app`, `static`, `tests`, and `requirements.txt`).
   Do **not** select a folder above it, and do not select `app` or `tests`.
5. If VS Code asks whether you trust the authors of the files, choose **Yes, I trust the authors**.

The Explorer panel should look like this (some items appear only after you create them in later steps):

```text
documind/
├── app/                      Python code for the server
├── static/                   the web page (HTML, CSS, JavaScript)
├── sample_data/              a synthetic sample document to try
├── tests/                    automated tests
├── .env.example              template for your settings (copy it to .env)
├── .gitignore                tells Git which files to skip
├── LICENSE
├── PROJECT_CHECKLIST.md
├── README.md
├── SETUP_GUIDE.md            this file
├── pytest.ini
└── requirements.txt          the list of Python packages
```

---

## STEP 3: Open the terminal in the project folder

1. In VS Code choose **Terminal > New Terminal** (or press `` Ctrl+` ``).
2. The terminal panel opens at the bottom. Its name should be `powershell` or `pwsh`.
   If it says `cmd` or `bash`, click the **+** arrow and choose **PowerShell**.
3. Check the folder with:

```powershell
Get-Location
```

The output should end in `\documind`. If it does not, move there, replacing the path with yours:

```powershell
cd C:\Users\<YourName>\Projects\documind
```

Every command in the rest of this guide must be run from this folder.

---

## STEP 4: Create and activate a virtual environment

A **virtual environment** (`.venv`) is a private set of packages for this project only.

### Create it

```powershell
python -m venv .venv
```

This creates a `.venv` folder. It takes a few seconds and is excluded from Git.

### Activate it

```powershell
.\.venv\Scripts\Activate.ps1
```

### Verify it is active

Your prompt now starts with `(.venv)`:

```text
(.venv) PS C:\Users\<YourName>\Projects\documind>
```

### If PowerShell blocks activation

You may see: *"...cannot be loaded because running scripts is disabled on this system."*

Use the **process-only** setting below. It applies to this terminal window only and is reset when you close it.
It does not change anything for your computer or your user account:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

**Another option without changing any setting:** skip activation and call the venv's Python directly.
Replace every `python` in this guide with `.\.venv\Scripts\python.exe`. For example:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## STEP 5: Install the dependencies

With `(.venv)` showing in the prompt, run:

```powershell
python -m pip install -r requirements.txt
```

Wait for the line that starts with `Successfully installed`. This is the list of libraries the project uses.

| Problem | What to do |
|---|---|
| `No matching distribution found` | Your Python is older than 3.11. Check `python --version`. Delete the `.venv` folder, then repeat Step 4 with Python 3.12. |
| Network or proxy error | Your network may block downloads. Try another network, or ask whoever manages your internet access. |
| Something failed in the middle | Run the same command again. pip skips what is already installed. |

---

## STEP 6: Create your settings file

Copy the template:

```powershell
Copy-Item .env.example .env
```

A file named `.env` appears. Open it in VS Code. It contains these settings:

| Setting | Required? | What to do |
|---|---|---|
| `ANTHROPIC_API_KEY` | **Only for Claude mode** | Leave the placeholder for demo mode. For Claude mode, replace it with your own key. |
| `ANTHROPIC_MODEL` | No | Default `claude-haiku-5-5`, which is listed in Anthropic's model documentation. Leave it unless you need another model. |
| `DEMO_MODE` | No | `false` by default. Set `true` to force demo mode even with a key. |
| The other settings | No | Leave the defaults for your first run. |

**Demo mode:** do nothing else. Keep the placeholder `your-anthropic-api-key-here`. The app runs in demo mode with no cost and no network calls.

**Claude mode (optional):**

1. Create a key at the Anthropic Console (<https://console.anthropic.com>). Keys are shown only once, so copy it immediately.
2. In `.env`, replace the placeholder with your key:
   `ANTHROPIC_API_KEY=<paste your key here>`
3. Save the file. Restart the server (Step 7) so it reads the new value.

**Keep the key secret:**

- Never paste it into `.env.example`, the code, a screenshot, or a chat.
- `.env` is listed in `.gitignore`, so Git ignores it. Do not remove that line.
- If a key is ever exposed, revoke it in the Anthropic Console and create a new one.

---

## STEP 7: Run the application

With `(.venv)` active and the project folder as the current folder, run:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`app.main:app` means: in the file `app\main.py`, use the variable named `app`.

### What a successful start looks like

The terminal shows lines like these (timestamps will differ):

```text
... INFO app.llm: Starting in DEMO mode: no API calls will be made
INFO:     Will watch for changes in these directories: [...]
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

With a real key the second-to-last line of the first block says `Starting in Claude mode with model claude-haiku-5-5`.

### Open the app

| What | Address |
|---|---|
| Web page | <http://127.0.0.1:8000> |
| Health check (JSON) | <http://127.0.0.1:8000/api/health> |
| API documentation | <http://127.0.0.1:8000/docs> |

Leave this terminal open while you use the app. Stop the server with **Ctrl+C** in that terminal.

---

## STEP 8: Try the app manually

Keep the server running and open <http://127.0.0.1:8000>.

**Check the mode badge.** In demo mode it says **Demo mode (no AI calls)**. In Claude mode it shows the model name.

### Scenario 1: Upload the sample

1. Click **Choose File** and select `sample_data\synthetic_company_handbook.txt`.
2. Click **Upload**.

**Expected:** the status line says `Stored "synthetic_company_handbook.txt" as 3 searchable chunks.`
The file appears under **Stored documents**. The chunk count can change if you change `CHUNK_SIZE`.

### Scenario 2: Ask a question the document answers

1. Type `How many vacation days do employees get?` and click **Ask**.

**Expected in demo mode:** an answer that starts with `DEMO MODE:` and quotes the passage with "18 paid vacation days".
**Sources** lists `[S1] synthetic_company_handbook.txt` with an excerpt.

**Expected in Claude mode:** a sentence that says 18 days, citing `[S1]`. The label says the answer was generated by Claude.

### Scenario 3: Ask something the document does not cover

1. Type `What is the capital of Mongolia?` and click **Ask**.

**Expected:** the answer is `The documents do not contain enough evidence to answer this question.` and **Sources** is empty.

### Scenario 4: Upload the same file twice

1. Upload the sample a second time.

**Expected:** a red message says the file is already stored as document 1. The list still shows one copy.

### Scenario 5: Delete a document

1. Click **Delete** next to the sample.

**Expected:** the status says `Document deleted.` and the list is empty. The stored text is removed from the database, not just hidden.

---

## STEP 9: Run the automated tests

With `(.venv)` active, from the project folder:

```powershell
python -m pytest
```

### Reading the result

- The last line looks like `98 passed in 1.02s`. The number is how many tests passed. It changes as the tests change.
- **`N passed` with no `failed`** means every test passed.
- **`F`** or **`FAILED`** means a test found a problem. The `FAILURES` section above shows the expected and actual values.
- **`ERROR`** means a test could not start, usually a missing package. Run Step 5 again.

For one line per test, run `python -m pytest -v`.

The tests never call Claude and need no API key. They use temporary databases, so your real `data\` folder is untouched.

To run one test file, for example the API tests:

```powershell
python -m pytest tests\test_api.py
```

---

## STEP 10: Understand the code

### What each file does

| File | Job |
|---|---|
| `app\main.py` | Entry point. Creates the app so `uvicorn` can run it. |
| `app\application.py` | Startup. Creates the database, retriever, and answerer, and connects the routes and the web page. |
| `app\config.py` | Reads settings from environment variables and `.env`. Treats the placeholder key as "no key". |
| `app\errors.py` | Error types that carry an HTTP status code and a safe message. |
| `app\schemas.py` | Pydantic models for the JSON going in and out. |
| `app\routes.py` | The HTTP endpoints. Receives requests and calls the other modules. |
| `app\extraction.py` | Cleans file names, validates uploads, and extracts text from TXT and PDF. |
| `app\chunking.py` | Splits text into overlapping chunks and keeps page numbers. |
| `app\retrieval.py` | Ranks chunks by shared keywords. This is where embeddings would be added later. |
| `app\llm.py` | Builds the prompt, calls Claude or returns the demo answer, and maps API errors to safe messages. |
| `app\storage.py` | Saves, looks up, and deletes documents and chunks in SQLite. |
| `static\index.html` | The page layout and labels. |
| `static\app.js` | Browser logic. Calls `/api` only and displays results with `textContent`. |
| `static\styles.css` | Styling, including the mobile layout. |
| `tests\` | Automated tests. `fakes.py` contains a fake Claude client. `conftest.py` holds shared fixtures. |

### One request from start to finish: asking a question

1. **Browser (`static\app.js`):** `handleAsk` trims the question, checks it has at least 3 characters, and sends `POST /api/ask` with a JSON body.
2. **Validation (`app\schemas.py`):** FastAPI turns the JSON into an `AskRequest`. Bad input gets a 422 error before any of our code runs.
3. **Route (`app\routes.py`):** `ask_question` checks that at least one document exists. If you named document IDs, it checks that they exist.
4. **Storage (`app\storage.py`):** `load_candidates` reads the chunks, with their file names and page numbers.
5. **Retrieval (`app\retrieval.py`):** `KeywordRetriever.rank` removes stopwords, counts shared words, and keeps the best `TOP_K` chunks.
6. **Answer (`app\llm.py`):**
   - If nothing matched, the route returns the "not enough evidence" message. Claude is not called.
   - Claude mode: `ClaudeAnswerer` sends the system prompt and one message containing the tagged excerpts and the question.
   - Demo mode: `DemoAnswerer` returns the top passage with a `DEMO MODE` label.
7. **Response:** the route returns JSON with the answer, `mode`, `insufficient_evidence`, and the `sources`.
8. **Browser:** `renderAnswer` shows the answer and the sources. It uses `textContent`, so document text is never run as HTML.

### Words you will hear

- **API:** a set of web addresses a program can call. `/api/ask` is one.
- **REST:** a style where addresses name things (documents, questions) and HTTP methods say what to do (`GET` reads, `POST` creates, `DELETE` removes).
- **HTTP status code:** a number that describes the result. 200 OK, 201 created, 204 done with no body, 404 not found, 409 conflict, 413 too large, 415 unsupported type, 422 invalid input, 429 too many requests, 502 bad upstream response, 504 timeout.
- **JSON:** text-based data such as `{"key": "value"}`.
- **FastAPI:** a Python framework that builds APIs from function signatures and type hints.
- **Uvicorn:** the server that runs the app and listens for requests.
- **Pydantic:** checks data against a model class. Wrong types produce clear errors.
- **Asynchronous (`async def`, `await`):** lets the server handle other requests while one waits, for example for an upload to finish.
- **Thread pool (`run_in_threadpool`):** runs slow CPU work, such as PDF parsing, on a separate thread so the server stays responsive.
- **Dependency (`Depends`):** FastAPI hands each route the objects it needs, such as the settings or the store.
- **SQLite:** a database stored in one file (`data\documind.db`). It needs no separate server.
- **Chunk:** a piece of document text of a few hundred characters.
- **Overlap:** characters repeated between neighbouring chunks, so a sentence cut at a boundary still appears whole somewhere.
- **Keyword retrieval:** matching the words of the question with the words of each chunk. It is fast and simple, but does not understand meaning.
- **Embedding:** a list of numbers that represents meaning. DocuMind does **not** use embeddings.
- **Prompt:** the text sent to an AI model. The system prompt sets the rules. The user message holds the excerpts and the question.
- **Prompt injection:** an attempt by text inside a document to override the instructions. DocuMind tells the model to ignore such text, and the sample contains a test line for this.
- **Grounding:** keeping the answer tied to the supplied sources.
- **Environment variable:** a named setting kept outside the code, such as `ANTHROPIC_API_KEY`.
- **Virtual environment:** a private set of packages for one project.
- **Fake / mock:** a stand-in for an outside service, used in tests so they cost nothing and do not depend on the network.

### Interview questions based on this code

1. **What does the app do?** It answers questions about an uploaded PDF or TXT file. It finds relevant passages and, with a key, asks Claude to answer from them with citations.
2. **Why chunk the text?** Short passages make the search precise and keep what is sent to the model small. Overlap prevents losing an idea at a boundary. Chunks never cross PDF pages, so page numbers stay correct.
3. **Does retrieval use embeddings?** No. It is keyword ranking with a TF-IDF-style score in `retrieval.py`. A new class with the same `rank` method could add embeddings later.
4. **How do you handle prompt injection?** The excerpts are wrapped in tags, and the system prompt says they are untrusted and must not be obeyed. This reduces the risk but is not a guarantee, and the README says so.
5. **How is the API key protected?** It is read from the environment on the server, never sent to the browser, and never returned or logged. A test checks that a failure response does not contain it.
6. **How are API errors handled?** `ClaudeAnswerer` catches each error type separately: timeout, rate limit, connection, bad key, not-found model, bad request, and other status errors. Each becomes a safe message with a suitable status code. Raw error text is not shown.
7. **Why two modes?** Demo mode runs without a key and without cost. It is labeled, so it cannot be mistaken for a Claude answer.
8. **How are uploads validated?** In order: file type, empty file, size, PDF signature or binary check, UTF-8 decoding, duplicate check, and then whether any text was extracted.
9. **What is stored?** Metadata, a SHA-256 fingerprint, and text chunks in SQLite. The original file is not kept. Deleting runs `VACUUM` so the removed text is not left in the file.
10. **What would you change to scale it?** Add embeddings and a vector index, use PostgreSQL, add user accounts and per-user data, add rate limiting, and deploy behind HTTPS.

---

## STEP 11: Verify your Git status before committing

Git records changes to your project. Before you commit anything, check what Git will include.

```powershell
git status
```

Check that the list does **not** include:

- `.env`
- `.venv/`
- `data/`
- `__pycache__/` or `.pytest_cache/`
- any file that contains a real API key

These are excluded by `.gitignore`. If `.env` appears, stop and check that `.gitignore` still contains the line `.env`.

To search every tracked file for key-like text, run this (it prints nothing when the search finds no matches):

```powershell
git grep -n "sk-ant-"
```

If it prints a line, do **not** commit. Remove the value from the file, and revoke the key in the Anthropic Console.

---

## STEP 12: Publish to GitHub

Nothing runs automatically. You run every command yourself.

### 12a. Create an empty repository on GitHub

1. Sign in at <https://github.com>.
2. Click **+** at the top right, then **New repository**.
3. Enter a name, for example `documind`. Choose **Public**.
4. **Do not** tick "Add a README file", "Add .gitignore", or "Choose a license". The project already has these.
5. Click **Create repository** and copy the address, which looks like `https://github.com/<your-github-username>/documind.git`.

### 12b. Initialize Git and make the first commit

Run these in the project folder, replacing nothing yet:

```powershell
git init
git status
git add .
git status
git commit -m "Initial commit: DocuMind document Q&A assistant"
```

Read the second `git status` carefully. It must not include `.env`, `.venv/`, or `data/`.

If Git asks who you are, set your name and email once:

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Then repeat the `git commit` command.

### 12c. Name the branch and connect it to GitHub

Replace `<your-github-username>` with your own username:

```powershell
git branch -M main
git remote add origin https://github.com/<your-github-username>/documind.git
git remote -v
```

`git remote -v` should show your URL twice, once for fetch and once for push.

### 12d. Push the project

```powershell
git push -u origin main
```

GitHub may open a sign-in window. Sign in there. GitHub does not accept account passwords for Git. If it asks for a password, create a **Personal Access Token** in GitHub under **Settings > Developer settings** and use it instead.

### Verify the upload

Open `https://github.com/<your-github-username>/documind` in your browser. You should see `README.md`, `app`, `static`, and `tests`. `.env` must **not** be listed.

---

## Common errors and verified fixes

The fixes below were checked against the running code. Items marked *(tested)* are covered by an automated test.
Items marked *(manual)* were checked by running the server during development.

| What you see | Meaning | Fix |
|---|---|---|
| `python` is not recognized | Python is not installed, or not on PATH. | Install Python 3.11+ with **Add python.exe to PATH** ticked, then reopen VS Code. |
| `Activate.ps1 cannot be loaded because running scripts is disabled` | PowerShell policy blocks scripts. | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again (Step 4). |
| `No module named 'app'` | You started from the wrong folder. | Run `Get-Location` and move to the `documind` folder (Step 3). |
| Badge says **Server unavailable** | The server is not running, or is on another port. | Start it again (Step 7) and check the terminal. |
| `Only .pdf and .txt files are supported` | The file type is not allowed. *(manual)* | Choose a `.pdf` or `.txt` file. |
| `The file name ends in .pdf, but the content is not a PDF.` *(tested)* | The file was renamed. | Use the real PDF, or export the document again as PDF. |
| `The file is larger than the 5.00 MB limit.` *(tested)* | The file is too big. | Use a smaller file, or raise `MAX_UPLOAD_MB` in `.env` and restart. |
| `This file is already stored as document N.` *(manual)* | The same file was uploaded before. | Nothing is wrong. Delete the old copy first if you want it stored again. |
| `No readable text was found in this document.` *(tested)* | A scanned PDF has no text layer. | Use a PDF with real text, or save the document as TXT. OCR is not included. |
| `No documents uploaded yet` *(tested)* | You asked a question before uploading. | Upload a document first. |
| `Document(s) not found` *(tested)* | A document ID in the request does not exist. | Refresh the list and use an ID that is shown there. |
| `The AI service rejected the API key` *(tested)* | The key is wrong or was revoked. | Check `ANTHROPIC_API_KEY` in `.env` and restart the server. |
| `The configured model was not found` *(tested)* | `ANTHROPIC_MODEL` does not name a model that exists. | Check the spelling in `.env`. The default is `claude-haiku-5-5`. |
| `The AI service took too long to respond` *(tested)* | The request timed out. | Ask again, or raise `ANTHROPIC_TIMEOUT_SECONDS` in `.env` and restart. |
| `The AI service is busy` *(tested)* | Rate limit reached. | Wait a minute and try again. |
| `Could not connect to the AI service` *(tested)* | No internet, or a proxy or firewall is blocking the request. | Check your connection. |
| `CHUNK_SIZE must be a number` *(tested)* | A setting in `.env` is not a number. | Fix the value shown in the message, then restart. |
| The badge says Demo mode after you added a key | `.env` still contains the placeholder, or `DEMO_MODE=true`. | Put the real key in `.env`, set `DEMO_MODE=false`, and restart. |
| Changes to `.env` have no effect | The server reads `.env` only when it starts. | Press **Ctrl+C**, then start the server again. |
| Git says `remote origin already exists` | A remote is already set. | Run `git remote remove origin`, then add it again (Step 12c). |
| `src refspec main does not match any` | Nothing has been committed yet. | Run the commit steps in Step 12b, then push again. |
| `Authentication failed` on push | GitHub does not accept your account password. | Use a Personal Access Token, or sign in through the browser window Git opens. |
| `rejected ... fetch first` on push | The GitHub repository already contains files. | Create a new empty repository (Step 12a), or pull first and resolve any conflicts. |
| `.env` appears in `git status` | Git would commit your secret. | Do not commit. Check that `.gitignore` contains `.env`. If it was committed before, run `git rm --cached .env`, commit, and revoke the key in the Anthropic Console. |

---

## STEP 13: Stop the app and start it again next time

**To stop:** click the terminal running uvicorn and press **Ctrl+C**.

**To start again later:**

1. Open VS Code and choose **File > Open Folder...**, then select `documind` (Step 2). VS Code remembers recent folders.
2. Open a terminal (Step 3) and check that you are in the project folder.
3. Activate the environment (Step 4). If it is blocked, use the `Process` setting again.
4. Start the server (Step 7).

Your uploaded documents stay in `data\documind.db` between restarts. Use **Clear all documents** in the page, or delete the `data` folder, to remove them.

---

## Final checklist

Use the file [PROJECT_CHECKLIST.md](PROJECT_CHECKLIST.md). It separates the checks that run automatically from the manual checks, and it shows which ones were actually completed.

---

## Interview practice

For more interview questions, see the list in Step 10. Answer them using the code, not from memory: open `app\llm.py`, `app\retrieval.py`, or `app\routes.py` and point to the line that does the thing you describe.
