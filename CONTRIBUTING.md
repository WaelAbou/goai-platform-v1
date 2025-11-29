# Contributing to GoAI Sovereign Platform

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Git
- (Optional) Tesseract OCR for local text extraction

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_ORG/goai-platform-v1.git
   cd goai-platform-v1
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your API keys
   ```

5. **Start the backend**
   ```bash
   uvicorn main:app --reload --port 8000
   ```

6. **Start the frontend** (in a new terminal)
   ```bash
   cd ui/console
   npm install
   npm run dev
   ```

7. **Access the platform**
   - UI: http://localhost:5173
   - API Docs: http://localhost:8000/docs

---

## Development Workflow

### Branch Naming

- `feature/` - New features (e.g., `feature/voice-assistant`)
- `fix/` - Bug fixes (e.g., `fix/ocr-timeout`)
- `docs/` - Documentation updates
- `refactor/` - Code refactoring

### Commit Messages

Follow conventional commits:
```
feat: add voice assistant module
fix: resolve OCR timeout for large images
docs: update API reference
refactor: optimize vector search
```

### Pull Requests

1. Create a feature branch from `main`
2. Make your changes
3. Run tests: `python -m pytest tests/`
4. Create PR with description
5. Request review from team

---

## Adding a New Use Case

Follow the **10-Step Development Cycle** (see `docs/DEVELOPMENT_CYCLE.md`):

```bash
# 1. Create use case directory
mkdir -p use_cases/my_use_case

# 2. Define intent
touch use_cases/my_use_case/intent.yaml

# 3. Create module
mkdir -p modules/my_use_case
touch modules/my_use_case/__init__.py
touch modules/my_use_case/engine.py
touch modules/my_use_case/models.py

# 4. Create API router
touch api/v1/my_use_case.py

# 5. Register in main.py
# 6. Create UI page (optional)
```

---

## Code Standards

### Python

- Use type hints
- Follow PEP 8
- Use Pydantic for models
- Async/await for I/O operations

### TypeScript/React

- Use TypeScript strict mode
- Functional components with hooks
- Tailwind CSS for styling

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_kyc.py -v

# Run with coverage
python -m pytest tests/ --cov=modules --cov-report=html
```

---

## Documentation

- Keep `README.md` updated
- Document new APIs in code
- Add use case docs to `use_cases/{name}/README.md`

---

## Questions?

Contact the platform team or open an issue.

