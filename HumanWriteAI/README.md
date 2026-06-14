# HumanWriteAI

AI-powered academic writing analysis platform that detects whether a given text is human-written or AI-generated.

---

## Current Architecture

### Project Structure

```
HumanWriteAI/
├── app.py                              # Flask application entry point
├── config.py                           # App configuration (DB URI, secret key)
├── requirements.txt                    # Python dependencies
├── README.md                           # This file
│
├── ai_engine/                          # AI / ML components
│   ├── dataset/
│   │   ├── ai_generated/               # Placeholder — store AI-generated text datasets
│   │   └── human/                      # Placeholder — store human-written text datasets
│   ├── inference/
│   │   └── predict.py                  # Prediction stub — returns "not trained"
│   ├── models/
│   │   └── detector.py                 # Loads DistilBERT base model (classification head TBD)
│   ├── preprocessing/
│   │   └── cleaner.py                  # Whitespace normalization utility
│   └── training/
│       └── train.py                    # Training pipeline shell (not implemented)
│
├── backend/                            # Flask backend layer
│   ├── models/
│   │   └── user.py                     # SQLAlchemy User model (not wired into app)
│   ├── routes/
│   │   ├── auth.py                     # /api/auth/test — placeholder endpoint
│   │   ├── analysis.py                 # /api/predict — calls predict_text()
│   │   └── documents.py                # /api/documents/upload — file upload handler
│   └── services/                       # Placeholder — business logic layer (empty)
│
├── documents/                          # Document parsing utilities
│   └── extractor.py                    # .docx text extraction via python-docx
│
├── frontend/                           # Static frontend
│   ├── index.html                      # Upload form + result display
│   ├── css/style.css                   # Minimal styling
│   ├── js/app.js                       # Client-side upload logic
│   └── images/                         # Static images (empty)
│
└── uploads/                            # Uploaded file storage (empty)
```

### Stack

| Layer       | Technology                                      |
|-------------|-------------------------------------------------|
| Backend     | Python 3.14 + Flask 3.0                         |
| Frontend    | HTML, CSS, Vanilla JavaScript                   |
| AI Engine   | PyTorch + Hugging Face Transformers (DistilBERT)|
| Database    | SQLite (via SQLAlchemy 2.0)                     |
| Auth        | Flask-Login + Flask-Bcrypt (installed, unused)  |

---

## Issues Found

### Broken or Fragile Imports

| File | Line | Import | Issue |
|------|------|--------|-------|
| `backend/routes/documents.py` | 3 | `from documents.extractor import extract_text` | Fragile — requires running from project root |
| `backend/routes/analysis.py` | 3 | `from ai_engine.inference.predict import predict_text` | Fragile — requires running from project root |
| `backend/models/user.py` | 2 | `from flask_sqlalchemy import SQLAlchemy` | `db` instance never initialized in `app.py` |
| `ai_engine/models/detector.py` | 3 | `AutoModelForSequenceClassification.from_pretrained("distilbert-base-uncased")` | Base model used as classifier — no classification head |

**Global issue:** No `__init__.py` files in any subdirectory. None of the packages are proper Python packages.

### Missing Initialization

- `config.py` is **never imported** in `app.py` — `SECRET_KEY` and `SQLALCHEMY_DATABASE_URI` are unused
- `backend/models/user.py` creates a `db` object but `app.py` never calls `db.init_app(app)` or `db.create_all()`
- Alembic is installed but no migration configuration exists
- python-dotenv is installed but no `.env` file or `load_dotenv()` call

### Missing Features

| Feature | Status |
|---------|--------|
| User authentication (register/login/logout) | ❌ Only `/api/auth/test` exists |
| Database integration | ❌ Model exists but not wired |
| AI training pipeline | ❌ Empty shell |
| AI prediction | ❌ Returns stub |
| Model tokenizer | ❌ Not loaded |
| Dataset loading | ❌ Empty directories |
| PDF file extraction | ❌ Only DOCX supported |
| Input validation | ❌ No error handling anywhere |
| Logging | ❌ Not configured |
| File type/size checks | ❌ Missing |
| Tests | ❌ No `tests/` directory |
| Environment config | ❌ `.env` not used |
| Model persistence | ❌ No save/load path |

---

## Development Roadmap

### Phase 1 — Foundation (High Priority)

- [ ] Add `__init__.py` to all Python subdirectories to make them proper packages
- [ ] Wire `config.py` into `app.py` — load `SECRET_KEY` and `SQLALCHEMY_DATABASE_URI`
- [ ] Initialize SQLAlchemy in `app.py` with `db.init_app(app)` and `app.app_context().push()`
- [ ] Add `db.create_all()` on first run or use Flask-Migrate (Alembic)
- [ ] Add `.env` support via `python-dotenv` with a `.env.example` template
- [ ] Remove duplicate `requirements.txt` from project root — keep only `HumanWriteAI/requirements.txt`
- [ ] Trim `requirements.txt` — strip unused packages (Jupyter, LangChain, Streamlit, etc.)

### Phase 2 — Authentication

- [ ] Implement registration endpoint (`POST /api/auth/register`)
- [ ] Implement login endpoint (`POST /api/auth/login`) with Flask-Login sessions
- [ ] Implement logout (`POST /api/auth/logout`)
- [ ] Hash passwords with Flask-Bcrypt
- [ ] Add session-based auth decorator for protected routes
- [ ] Add login/registration UI to the frontend

### Phase 3 — AI Engine

- [ ] Implement tokenizer loading in `detector.py` (use `AutoTokenizer.from_pretrained`)
- [ ] Build dataset loader for `ai_engine/dataset/human/` and `ai_engine/dataset/ai_generated/`
- [ ] Implement training pipeline in `train.py`:
  - Tokenize datasets
  - Configure `Trainer`/`TrainingArguments` from Transformers
  - Train DistilBERT classifier
  - Save model to a `models/` checkpoint directory
- [ ] Update `predict.py` to load trained model and return inference results
- [ ] Add confidence scores and per-token analysis

### Phase 4 — Document Handling

- [ ] Add PDF extraction support (via `PyMuPDF` or `pdfplumber`)
- [ ] Add plain text file support (`.txt`)
- [ ] Add file type validation and size limits
- [ ] Store uploaded files with unique IDs in `uploads/`
- [ ] Add document management endpoints (list, delete, re-analyze)

### Phase 5 — Frontend & UX

- [ ] Build proper dashboard layout
- [ ] Display analysis results with visual indicators (progress bars, charts)
- [ ] Add drag-and-drop file upload
- [ ] Add user profile page (upload history, past analyses)
- [ ] Responsive design with better CSS framework (or Tailwind)

### Phase 6 — Production Readiness

- [ ] Add comprehensive error handling (try/except, JSON error responses)
- [ ] Add logging (Python `logging` module + file handler)
- [ ] Add unit tests and integration tests (`pytest`)
- [ ] Add CI/CD configuration
- [ ] Add Dockerfile and docker-compose.yml
- [ ] Add API documentation (Swagger/OpenAPI)
- [ ] Switch from SQLite to PostgreSQL for production

---

## Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r HumanWriteAI/requirements.txt

# Run the app
cd HumanWriteAI
python app.py
```

The server starts at `http://127.0.0.1:5000`.

---

## Current File Inventory

```
HumanWriteAI/app.py
HumanWriteAI/config.py
HumanWriteAI/requirements.txt
HumanWriteAI/README.md
HumanWriteAI/ai_engine/inference/predict.py
HumanWriteAI/ai_engine/models/detector.py
HumanWriteAI/ai_engine/preprocessing/cleaner.py
HumanWriteAI/ai_engine/training/train.py
HumanWriteAI/backend/models/user.py
HumanWriteAI/backend/routes/analysis.py
HumanWriteAI/backend/routes/auth.py
HumanWriteAI/backend/routes/documents.py
HumanWriteAI/documents/extractor.py
HumanWriteAI/frontend/index.html
HumanWriteAI/frontend/css/style.css
HumanWriteAI/frontend/js/app.js
```

**Empty placeholder directories**: `uploads/`, `frontend/images/`, `backend/services/`, `ai_engine/dataset/ai_generated/`, `ai_engine/dataset/human/`