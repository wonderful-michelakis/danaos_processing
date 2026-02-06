# Document Processing Pipeline - Visual Flow

## End-to-End Pipeline

```
┌──────────────────────────────────────────────────────────────────┐
│                          INPUT: PDF                               │
│  Mixed content: Text, Tables, Images, Diagrams                    │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  STEP 1: EXTRACT (run_pipeline.py)                                │
│                                                                   │
│  Docling parses PDF → entities (text, tables, images)            │
│  Vision API classifies and extracts image content                │
│  List items detected and grouped                                  │
│                                                                   │
│  Output: entities/ + final_document.md + manifest.yaml            │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  STEP 2: JUDGE (run_judge.py)                                     │
│                                                                   │
│  LLM reads final_document.md                                     │
│  Merges fragmented entities (split lists, headers, etc.)         │
│  Combines repeating page headers into single entities            │
│  Fixes OCR artifacts and formatting issues                       │
│                                                                   │
│  Output: final_document_judge.md                                  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  STEP 3: CONVERT TO HTML (convert_to_friendly.py)                 │
│                                                                   │
│  Markdown → styled HTML                                           │
│  YAML tables → HTML tables                                        │
│  Mermaid diagrams → rendered via mermaid.js                       │
│  Entity markers → clickable badges                                │
│                                                                   │
│  Output: final_document_judge_friendly.html                       │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  STEP 4: REVIEW & CORRECT (compare_viewer.py)                     │
│                                                                   │
│  Side-by-side: original PDF ↔ processed HTML                     │
│  Click entity badges to edit (manual or AI-assisted)             │
│  Document-wide AI corrections                                     │
│  Changes auto-regenerate HTML                                     │
│                                                                   │
│  Output: corrections.yaml (audit trail)                           │
└──────────────────────────────────────────────────────────────────┘

Output directory structure:
┌──────────────────────────────────────────────────────────────────┐
│  outputs/<name>/                                                  │
│  ├── entities/                     ← Individual entity files     │
│  ├── final_document.md             ← Assembled from entities     │
│  ├── final_document_judge.md       ← Judge-normalized version    │
│  ├── final_document_friendly.html  ← HTML from pipeline          │
│  ├── final_document_judge_friendly.html ← HTML from judge        │
│  ├── manifest.yaml                 ← Processing metadata         │
│  └── corrections.yaml             ← Correction audit trail       │
└──────────────────────────────────────────────────────────────────┘
```

---

## Step 1: Extraction — Detailed Flow

### Docling Extraction Phase

```
PDF File
   │
   ├─→ Docling Parser
   │     │
   │     ├─→ Text Extraction
   │     │     • Preserves structure
   │     │     • Maintains position
   │     │     • Records bounding box
   │     │     • confidence: 1.0
   │     │
   │     ├─→ Table Recognition (Smart Fallback)
   │     │     • Identifies grid structure
   │     │     • Exports as markdown → validates → YAML
   │     │     │
   │     │     ├─→ If VALID: Use Docling extraction (free)
   │     │     │
   │     │     └─→ If INVALID: Fallback system
   │     │           ├─→ Extract table region with PyMuPDF
   │     │           └─→ Send to Vision API for extraction
   │     │
   │     └─→ Image Detection
   │           • Extracts embedded images
   │           • Provides PIL Image objects
   │           • Records position data
   │
   │
   ├─→ List Detection & Grouping
   │     • Consecutive list items merged into single entities
   │     • Detects bullets (-, *, •), numbered (1., 2.)
   │     • Groups by indentation and vertical proximity
   │
   └─→ Structured Document Object
```

### Vision API Classification Phase

```
Image Input
   │
   ├─→ Classification API Call
   │     Response: {type, confidence, has_diagram, has_table, has_text, ...}
   │
   └─→ Route by type:
         │
         ├─→ TEXT      → Extract as Markdown
         ├─→ TABLE     → Extract as YAML
         ├─→ DIAGRAM   → Extract as Mermaid
         └─→ MIXED     → Extract surrounding text + primary content
```

### Table Fallback System

```
TableItem Detected
   │
   ├─→ Docling export_to_markdown()
   ├─→ Convert to YAML
   ├─→ Validate: non-empty? valid YAML? has rows? 2+ columns?
   │
   ├─→ VALID: Use Docling result (confidence: 1.0, cost: $0)
   │
   └─→ INVALID: Fallback
         ├─→ PyMuPDF: extract table region image at 2x resolution
         ├─→ Vision API: extract table as YAML
         │
         ├─→ Success: Use Vision result (confidence: 0.85)
         └─→ Failure: Create error entity (confidence: 0.0)
```

### Document Assembly

```
All Entities (in order)
   │
   ├─→ Create document header (YAML frontmatter)
   ├─→ For each entity:
   │     ├─→ Add marker: <!-- Entity: E001 | Type: ... | Page: 1 -->
   │     └─→ Add content (with code blocks for yaml/mermaid)
   ├─→ Write final_document.md
   └─→ Write manifest.yaml
```

---

## Step 2: Judge — Detailed Flow

```
final_document.md
   │
   ├─→ Replace HTML comment markers with [ENTITY:EXXX] tokens
   │     (prevents LLM from stripping HTML comments)
   │
   ├─→ Send to LLM with judge_prompt.md system instructions
   │     Model: GPT-4o (default) or GPT-4o-mini
   │
   ├─→ LLM processes document:
   │     ├─→ Identify entities to merge (lists, headers, page headers)
   │     ├─→ Apply format specifications (YAML tables, Mermaid, bullets)
   │     └─→ Fix obvious errors (OCR artifacts, broken words)
   │
   ├─→ Convert [ENTITY:EXXX] tokens back to HTML comment markers
   │
   ├─→ Validate: Ensure entity markers preserved
   │     └─→ If all markers stripped → fall back to original document
   │
   └─→ Write final_document_judge.md
```

---

## Step 3: HTML Conversion — Detailed Flow

```
Markdown file (final_document.md or final_document_judge.md)
   │
   ├─→ Parse entity markers → extract entity metadata
   │
   ├─→ For each entity:
   │     │
   │     ├─→ Text/Heading → render Markdown to HTML
   │     │
   │     ├─→ YAML table → parse YAML → render as HTML <table>
   │     │     • Handles nested dicts, lists of dicts
   │     │     • Renders scalar values as key-value pairs
   │     │
   │     ├─→ Mermaid diagram → sanitize + wrap in <pre class="mermaid">
   │     │     • Clean empty edge labels
   │     │     • Quote special characters in labels
   │     │     • Separate preamble text from graph definition
   │     │
   │     └─→ Wrap in entity section with badge (page, type, ID)
   │
   ├─→ Assemble HTML page with:
   │     • CSS styling
   │     • mermaid.js for diagram rendering
   │     • Entity badges and page markers
   │
   └─→ Write *_friendly.html
```

---

## Step 4: Comparison Viewer — Detailed Flow

```
Flask Server (compare_viewer.py)
   │
   ├─→ Serve original PDF (left panel)
   ├─→ Serve processed HTML (right panel)
   ├─→ Sync page navigation
   │
   └─→ Correction API:
         │
         ├─→ GET /api/entity/<id>
         │     • Read entity content from active markdown
         │     • Supports judge mode (merged content)
         │
         ├─→ POST /api/correct-with-ai
         │     • Send entity + user prompt to OpenAI
         │     • Return corrected content
         │
         ├─→ POST /api/save-correction
         │     │
         │     ├─→ Judge mode:
         │     │     • Edit entity in final_document_judge.md in-place
         │     │     • Regenerate judge HTML
         │     │
         │     └─→ Regular mode:
         │           • Edit entity file in entities/
         │           • Rebuild final_document.md
         │           • Regenerate HTML
         │     │
         │     └─→ Save to corrections.yaml (audit trail)
         │
         └─→ POST /api/document-wide-correction
               • Analyze all entities against user instruction
               • Propose batch corrections
               • Apply selected corrections
```

---

## Performance Characteristics

```
Pipeline Stage              API Calls    Cost
──────────────────────────────────────────────────────────
Step 1: Extraction
  Text blocks               0            $0
  PDF tables (valid)        0            $0
  PDF tables (fallback)     1 per fail   ~$0.03 each
  Image classification      1 per image  ~$0.01 each
  Image extraction          1 per image  ~$0.03 each

Step 2: Judge
  Document normalization    1            ~$0.05-0.30

Step 3: HTML Conversion
  Markdown → HTML           0            $0

Step 4: Corrections
  AI-assisted correction    1 per fix    ~$0.03-0.06 each
  Document-wide analysis    1            ~$0.10-0.30
──────────────────────────────────────────────────────────

Example: 20-page document, 8 images, 5 tables (1 fails)

  Extraction:  16 API calls  ~$0.35
  Judge:        1 API call   ~$0.10
  HTML:         0 API calls  $0
  Corrections:  varies       ~$0.03 each
  ──────────────────────────────────
  Total:       ~17 API calls ~$0.45
```

---

## Error Handling

```
API Call
   │
   ├─→ Success → Continue
   │
   └─→ Failure
         ├─→ Retry #1 (wait 4 sec)
         ├─→ Retry #2 (wait 8 sec)
         └─→ Retry #3 (wait 16 sec)
               │
               ├─→ Success → Continue
               └─→ Final Fail → Log error, skip entity, continue
```

Judge fallback:
- If all entity markers stripped → use original document
- If API error → skip judge step, use `final_document.md` directly
