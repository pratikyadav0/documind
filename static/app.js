// DocuMind front end: plain JavaScript with no framework and no build step.
// The browser only calls our own /api routes. It never sees the Anthropic API key.

const API_BASE = "/api";
const ALLOWED_EXTENSIONS = [".pdf", ".txt"];
// The real limit comes from the server (MAX_UPLOAD_MB). We fill this in from /api/health at startup.
let maxUploadBytes = null;

const el = {
  modeBadge: document.getElementById("mode-badge"),
  uploadForm: document.getElementById("upload-form"),
  fileInput: document.getElementById("file-input"),
  uploadButton: document.getElementById("upload-button"),
  uploadStatus: document.getElementById("upload-status"),
  documentList: document.getElementById("document-list"),
  clearButton: document.getElementById("clear-button"),
  askForm: document.getElementById("ask-form"),
  questionInput: document.getElementById("question-input"),
  askButton: document.getElementById("ask-button"),
  askStatus: document.getElementById("ask-status"),
  answerPanel: document.getElementById("answer-panel"),
  answerMode: document.getElementById("answer-mode"),
  answerText: document.getElementById("answer-text"),
  sourceList: document.getElementById("source-list"),
};

// Single helper for every API call. It turns server error responses into JavaScript errors.
async function callApi(path, options = {}) {
  const response = await fetch(API_BASE + path, options);
  let body = null;
  if (response.status !== 204) {
    // If the body is not JSON, body stays null. The fallback message below covers that case.
    body = await response.json().catch(() => null);
  }
  if (!response.ok) {
    const detail = body && body.detail;
    const message = typeof detail === "string" ? detail : `Request failed with status ${response.status}.`;
    throw new Error(message);
  }
  return body;
}

function setStatus(element, message, isError = false) {
  element.textContent = message;
  element.classList.toggle("error", isError);
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

async function loadHealth() {
  try {
    const health = await callApi("/health");
    maxUploadBytes = health.max_upload_mb * 1024 * 1024;
    if (health.mode === "demo") {
      el.modeBadge.textContent = "Demo mode (no AI calls)";
      el.modeBadge.classList.add("demo");
    } else {
      el.modeBadge.textContent = `Claude API mode (${health.model})`;
      el.modeBadge.classList.add("live");
    }
  } catch (error) {
    el.modeBadge.textContent = "Server unavailable";
    el.modeBadge.classList.add("error");
  }
}

async function loadDocuments() {
  const result = await callApi("/documents");
  renderDocuments(result.documents);
}

function renderDocuments(documents) {
  el.documentList.replaceChildren();
  if (documents.length === 0) {
    const empty = document.createElement("li");
    empty.className = "muted";
    empty.textContent = "No documents yet.";
    el.documentList.appendChild(empty);
    return;
  }

  for (const doc of documents) {
    const item = document.createElement("li");
    item.className = "document-item";

    const info = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = doc.filename;
    const meta = document.createElement("div");
    meta.className = "muted small";
    const pageText = doc.readable_pages ? ` | ${doc.readable_pages} pages` : "";
    meta.textContent = `${doc.file_type.toUpperCase()} | ${formatBytes(doc.size_bytes)} | ${doc.chunk_count} chunks${pageText}`;
    info.append(name, meta);

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "secondary small";
    deleteButton.textContent = "Delete";
    deleteButton.addEventListener("click", () => deleteDocument(doc.id));

    item.append(info, deleteButton);
    el.documentList.appendChild(item);
  }
}

async function handleUpload(event) {
  event.preventDefault();
  const file = el.fileInput.files[0];
  if (!file) {
    setStatus(el.uploadStatus, "Choose a file first.", true);
    return;
  }

  // These quick checks only save a round trip. The server repeats them, because the browser can be bypassed.
  const lowerName = file.name.toLowerCase();
  if (!ALLOWED_EXTENSIONS.some((ext) => lowerName.endsWith(ext))) {
    setStatus(el.uploadStatus, "Only .pdf and .txt files are supported.", true);
    return;
  }
  if (maxUploadBytes !== null && file.size > maxUploadBytes) {
    const limitMb = (maxUploadBytes / (1024 * 1024)).toFixed(1);
    setStatus(el.uploadStatus, `That file is larger than the ${limitMb} MB limit.`, true);
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  el.uploadButton.disabled = true;
  setStatus(el.uploadStatus, "Uploading and reading the document...");
  try {
    const stored = await callApi("/documents", { method: "POST", body: formData });
    setStatus(el.uploadStatus, `Stored "${stored.filename}" as ${stored.chunk_count} searchable chunks.`);
    el.fileInput.value = "";
    await loadDocuments();
  } catch (error) {
    setStatus(el.uploadStatus, error.message, true);
  } finally {
    el.uploadButton.disabled = false;
  }
}

async function deleteDocument(documentId) {
  try {
    await callApi(`/documents/${documentId}`, { method: "DELETE" });
    setStatus(el.uploadStatus, "Document deleted.");
    await loadDocuments();
  } catch (error) {
    setStatus(el.uploadStatus, error.message, true);
  }
}

async function clearAllDocuments() {
  if (!window.confirm("Delete every stored document? This cannot be undone.")) {
    return;
  }
  try {
    const result = await callApi("/documents", { method: "DELETE" });
    setStatus(el.uploadStatus, `Deleted ${result.deleted_documents} document(s).`);
    await loadDocuments();
  } catch (error) {
    setStatus(el.uploadStatus, error.message, true);
  }
}

async function handleAsk(event) {
  event.preventDefault();
  const question = el.questionInput.value.trim();
  if (question.length < 3) {
    setStatus(el.askStatus, "Please type a longer question.", true);
    return;
  }

  el.askButton.disabled = true;
  el.answerPanel.classList.add("hidden");
  setStatus(el.askStatus, "Searching the documents...");
  try {
    const result = await callApi("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    setStatus(el.askStatus, "");
    renderAnswer(result);
  } catch (error) {
    setStatus(el.askStatus, error.message, true);
  } finally {
    el.askButton.disabled = false;
  }
}

// Every value is set with textContent, never innerHTML. A document cannot inject HTML into the page this way.
function renderAnswer(result) {
  el.answerPanel.classList.remove("hidden");
  el.answerMode.textContent =
    result.mode === "demo"
      ? "DEMO MODE: this answer was generated locally, without Claude."
      : "Generated by Claude from the source excerpts below.";
  el.answerText.textContent = result.answer;

  el.sourceList.replaceChildren();
  if (result.sources.length === 0) {
    const none = document.createElement("li");
    none.className = "muted";
    none.textContent = "No matching passages were found.";
    el.sourceList.appendChild(none);
    return;
  }

  for (const source of result.sources) {
    const item = document.createElement("li");
    const heading = document.createElement("strong");
    const pageText = source.page_number ? `, page ${source.page_number}` : "";
    heading.textContent = `[${source.label}] ${source.filename}${pageText}`;
    const excerpt = document.createElement("p");
    excerpt.className = "excerpt";
    excerpt.textContent = source.excerpt;
    item.append(heading, excerpt);
    el.sourceList.appendChild(item);
  }
}

el.uploadForm.addEventListener("submit", handleUpload);
el.clearButton.addEventListener("click", clearAllDocuments);
el.askForm.addEventListener("submit", handleAsk);

loadHealth();
loadDocuments().catch((error) => setStatus(el.uploadStatus, error.message, true));
