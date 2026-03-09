# 📄 Mini Document Analyzer

A lightweight CLI tool that reads `.txt` files and produces a structured JSON report with word frequency statistics and document metadata.

---

## 🚀 Setup

### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation)

### Install dependencies
```bash
poetry install
```

---

## ▶️ Usage
```bash
# Auto-generate output filename (input.analysis.json)
python main.py input.txt

# Specify a custom output file
python main.py input.txt output.json
```

### Examples
```bash
python main.py documents/report.txt
# → saves to documents/report.analysis.json

python main.py notes.txt summary.json
# → saves to summary.json
```

---

## ❗ Error Handling

The CLI will print a clear message and exit (no traceback) for:

| Situation | Message |
|---|---|
| File not found | `Error: File 'x.txt' does not exist.` |
| Not a .txt file | `Error: 'x.pdf' is not a .txt file.` |
| Empty file | `Error: File 'x.txt' is empty.` |

---

## 📦 JSON Output Structure
```json
{
  "document": {
    "filename": "input.txt",
    "total_characters": 1024,
    "total_words": 180,
    "total_sentences": 12
  },
  "content": {
    "cleaned_text": "this is example text without punctuation",
    "tokens": ["this", "is", "example", "text"]
  },
  "statistics": {
    "word_frequencies": {
      "example": 5,
      "text": 4
    },
    "top_10_words": [
      ["example", 5],
      ["text", 4]
    ]
  }
}
```

---

## 🗂️ Project Structure
```
mini-document-analyzer/
│
├── analyzer/
│   ├── __init__.py
│   ├── text_reader.py    
│   ├── tokenizer.py       
│   └── statistics.py      
│
├── cli.py                
├── main.py                
├── pyproject.toml
└── README.md
```