# DocuMind Project Checklist

Each item below is marked only when it has been checked. Three labels show how it was checked:

- **[auto]**: an automated check you can run yourself with pytest or a command.
- **[http]**: checked by starting the real server and sending requests.
- **[manual]**: checked by a person using the browser or a real account.
- **[key]**: needs a real Anthropic API key. Not run in this review.

`[x]` = done and verified. `[ ]` = not done, or not verifiable here. The notes say what was run.

---

## 1. Code syntax and style

- [x] **[auto]** Python compiles with no syntax errors: `python -m compileall -q app tests`
- [x] **[auto]** JavaScript parses with no syntax errors: `node --check static/app.js`
- [x] **[auto]** Lint finds no unused imports or undefined names: `python -m pyflakes app tests`

## 2. Dependencies

- [x] **[auto]** `requirements.txt` installs into a brand-new virtual environment, and the full test suite passes there.
- [x] **[auto]** `.env` is optional: the app starts and runs in demo mode with no `.env` file (covered by `test_config.py`).

## 3. Automated tests

- [x] **[auto]** Full suite passes: `python -m pytest`. Last run result is recorded in the final report.
- [x] **[auto]** Configuration with and without a key, placeholder key, invalid numbers, model name matches `.env.example`.
- [x] **[auto]** Upload validation: unsupported type, empty, oversized, fake PDF, binary TXT, non-UTF-8 TXT, damaged PDF.
- [x] **[auto]** Text extraction (TXT and a generated PDF with page numbers) and chunking (size, overlap, page boundaries).
- [x] **[auto]** Keyword ranking, top-k, ties, and no-match results.
- [x] **[auto]** Claude API success, timeout (504), rate limit (429), connection error (502), bad key (502), model not found (502), bad request (502), malformed reply (502), all with mocked errors.
- [x] **[auto]** Prompt injection: document text stays inside the excerpt tags; the system prompt is not changed by it.
- [x] **[auto]** API key never appears in responses, health output, or the messages sent to Claude.
- [x] **[auto]** Duplicate upload returns 409; file name with `../` or `..\` is stored as a plain name.
- [x] **[auto]** Document deletion removes the chunk rows from the database file, and clear-all removes everything.
- [x] **[auto]** Database survives an app restart; an older database file without the new column is upgraded.
- [x] **[auto]** Frontend calls only routes that exist on the backend, and the browser code never assigns to `innerHTML`.

## 4. Demo mode and the live server

- [x] **[http]** Server starts in demo mode (`python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`) and logs `Starting in DEMO mode`.
- [x] **[http]** `GET /api/health` returns `mode: demo`, the upload limit, and `model: null`.
- [x] **[http]** Uploading the synthetic TXT sample returns 201 and 3 chunks (default settings).
- [x] **[http]** Asking about vacation days returns a `DEMO MODE` answer with source `[S1]`.
- [x] **[http]** Asking an unrelated question returns the insufficient-evidence message with no sources.
- [x] **[http]** Uploading the same file again returns 409.
- [x] **[http]** Unsupported file type returns 415; a question shorter than 3 characters returns 422.
- [x] **[http]** A file named `..\..\evil.txt` is stored as `evil.txt`, and no file is written outside the project.
- [x] **[http]** `GET /docs` returns 200 and `GET /app.js` is served.
- [ ] **[http]** Live PDF upload through the running server. *Covered by an automated test instead; not repeated over HTTP.*
- [ ] **[http]** Live document deletion and restart persistence through the running server. *Covered by automated tests instead.*

## 5. Browser and visual checks

- [ ] **[manual]** Page loads and the mode badge reads correctly in a real browser. *Not done: no browser was driven during this review.*
- [ ] **[manual]** Upload, list, delete, ask, answer, and source display work by clicking through the page. *Not done.*
- [ ] **[manual]** Layout is usable at laptop width and at phone width. *Not done: the CSS was written with a mobile breakpoint, but no screen size was tested.*
- [ ] **[manual]** Keyboard and screen-reader use. *Not done. Labels were added to the file input and the question box, but this was not tested with assistive technology.*

## 6. Claude API mode

- [ ] **[key]** Claude answers with a real key. *Not run: no API key was used in this project, and none is stored in the repository.*
- [x] **[auto]** The model ID `claude-haiku-5-5` was checked against Anthropic's model documentation (platform.claude.com, Claude Haiku 5.5 page). This is a documentation check, not an API call.
- [ ] **[key]** A wrong key shows the "rejected the API key" message in the browser. *Covered by a mocked test only.*

## 7. Secrets and Git safety

- [x] **[auto]** Scan for key-like text in the repository found no real credential. One made-up test value that looked like a real key prefix was renamed.
- [x] **[auto]** `.gitignore` excludes `.env`, `.venv/`, `data/`, `__pycache__/`, and `*.db`; `.env.example` is kept.
- [x] **[auto]** `.env.example` contains only placeholders.
- [ ] **[manual]** `git status` on your own machine shows no `.env` or `data/` before the first commit. *Not run here: the project is not a Git repository yet.*
- [ ] **[manual]** Check Git history for secrets after your first commit. *Not applicable until a commit exists.*

## 8. Documentation review

- [x] README reviewed against the code: model ID, endpoints, status codes, and limitations.
- [x] SETUP_GUIDE reviewed against the code: commands, file names, port, and error messages.
- [ ] Documentation reviewed by a second person. *Not done.*

## 9. GitHub publication

- [ ] Repository created on GitHub. *Not done. Nothing has been pushed.*
- [ ] Push verified by opening the repository page. *Not done.*

---

## Summary

- Verified by automated tests and by running the server in demo mode.
- Not verified: browser behaviour, mobile layout, real Claude calls, and GitHub publishing.
- Before public deployment, see the security limits in the README. Nothing here makes the app ready for public internet use.
