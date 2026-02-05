# Document Processing Pipeline - Visual Flow

## High-Level Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                          INPUT: PDF                               │
│  • Emergency Procedures Manual                                   │
│  • Mixed: Text, Tables, Images, Diagrams                         │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                    DOCLING EXTRACTION                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Text Blocks  │  │ PDF Tables   │  │   Images     │          │
│  │  (Direct)    │  │  (Native)    │  │ (Pictures)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│        │                  │                  │                    │
│        │ Position         │ Structure        │ PIL Image         │
│        │ BBox             │ BBox             │ BBox              │
│        │ Page             │ Page             │ Page              │
└────────┼──────────────────┼──────────────────┼───────────────────┘
         ↓                  ↓                  ↓
┌────────┼──────────────────┼──────────────────┼───────────────────┐
│        │                  │                  │                    │
│        ↓                  ↓                  ↓                    │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐              │
│  │ MARKDOWN │      │MD → YAML │      │ CLASSIFY │              │
│  │ (Direct) │      │Converter │      │ (Vision) │              │
│  └──────────┘      └──────────┘      └──────────┘              │
│                                             │                    │
│                                             ↓                    │
│                                    ┌─────────────────┐          │
│                                    │  Classification  │          │
│                                    │  Result          │          │
│                                    └─────────────────┘          │
│                                    │  Type: table    │          │
│                                    │  Confidence:0.88│          │
│                                    └─────────────────┘          │
│                                             │                    │
│                          ┌──────────────────┼──────────────────┐│
│                          ↓                  ↓                  ↓ │
│                   ┌─────────────┐  ┌──────────────┐  ┌─────────┐│
│                   │Extract Text │  │Extract Table │  │Extract  ││
│                   │→ Markdown   │  │→ YAML        │  │Diagram  ││
│                   │(Vision OCR) │  │(Vision API)  │  │→Mermaid ││
│                   └─────────────┘  └──────────────┘  └─────────┘│
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                     ENTITY PROCESSING                             │
│  • Add metadata (ID, type, page, bbox, confidence)              │
│  • Format content according to type                              │
│  • Generate unique filename                                      │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                   INDIVIDUAL ENTITY FILES                         │
│  entities/                                                       │
│  ├── E001_text.md        ← Markdown with frontmatter            │
│  ├── E002_table.yaml     ← YAML with metadata comments          │
│  ├── E003_diagram.mmd    ← Mermaid with metadata                │
│  ├── E004_image_text.md  ← Extracted text from image            │
│  └── E005_table.yaml     ← Table from image                     │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                    DOCUMENT ASSEMBLY                              │
│  • Combine all entities in original order                       │
│  • Add entity markers (<!-- Entity: E001 | ... -->)             │
│  • Include document metadata header                              │
│  • Create processing manifest                                    │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                         FINAL OUTPUT                              │
│  output/                                                         │
│  ├── entities/           ← Individual standardized files        │
│  ├── final_document.md   ← Complete assembled document          │
│  └── manifest.yaml       ← Metadata, stats, confidence scores   │
└──────────────────────────────────────────────────────────────────┘
```

## Detailed Component Flow

### 1. Docling Extraction Phase

```
PDF File
   │
   ├─→ Docling Parser
   │     │
   │     ├─→ Text Extraction
   │     │     • Preserves structure
   │     │     • Maintains position
   │     │     • Records bounding box
   │     │
   │     ├─→ Table Recognition
   │     │     • Identifies grid structure
   │     │     • Extracts cell content
   │     │     • Exports as markdown
   │     │
   │     └─→ Image Detection
   │           • Extracts embedded images
   │           • Provides PIL Image objects
   │           • Records position data
   │
   └─→ Structured Document Object
```

### 2. Vision API Classification Phase

```
Image Input
   │
   ├─→ Preprocessing
   │     • Resize if > 2000px
   │     • Convert to JPEG
   │     • Base64 encode
   │
   ├─→ Classification API Call
   │     Prompt: "Classify this image: TEXT, TABLE, or DIAGRAM"
   │
   │     Response (JSON):
   │     {
   │       "type": "table",
   │       "confidence": 0.88,
   │       "description": "Contact information table",
   │       "has_text": true,
   │       "has_table": true,
   │       "has_diagram": false
   │     }
   │
   └─→ Classification Result
```

### 3. Vision API Extraction Phase

```
Classification Result
   │
   ├─→ If TYPE = "text"
   │     │
   │     └─→ Text Extraction API Call
   │           Prompt: "Extract all text as clean Markdown"
   │           Output: Markdown formatted text
   │
   ├─→ If TYPE = "table"
   │     │
   │     └─→ Table Extraction API Call
   │           Prompt: "Convert table to YAML with meaningful keys"
   │           Output: YAML structured data
   │
   └─→ If TYPE = "diagram"
         │
         └─→ Diagram Extraction API Call
               Prompt: "Convert diagram to Mermaid syntax"
               Output: Mermaid flowchart code
```

### 4. Entity Processing & Storage

```
Extracted Content
   │
   ├─→ Create Entity Metadata
   │     • Assign unique ID (E001, E002, ...)
   │     • Record type (text, table, diagram)
   │     • Store page number
   │     • Save bounding box
   │     • Include confidence score
   │     • Add processing notes
   │
   ├─→ Format Content
   │     │
   │     ├─→ If Markdown (.md)
   │     │     ---
   │     │     metadata in YAML frontmatter
   │     │     ---
   │     │     content here
   │     │
   │     ├─→ If YAML (.yaml)
   │     │     # Metadata
   │     │     # key: value
   │     │     yaml_content
   │     │
   │     └─→ If Mermaid (.mmd)
   │           %% Metadata
   │           %% key: value
   │           mermaid_code
   │
   └─→ Save Entity File
         entities/E{num}_{type}.{ext}
```

### 5. Document Assembly

```
All Entities (in order)
   │
   ├─→ Create Document Header
   │     ---
   │     document_title: "..."
   │     total_entities: 15
   │     processed_date: "..."
   │     ---
   │
   ├─→ For Each Entity (in order):
   │     │
   │     ├─→ Add Entity Marker
   │     │     <!-- Entity: E001 | Type: text | Page: 1 -->
   │     │
   │     ├─→ Add Content (with code blocks)
   │     │     ```yaml         (for tables)
   │     │     ```mermaid      (for diagrams)
   │     │     plain markdown  (for text)
   │     │
   │     └─→ Add Spacing
   │
   └─→ Write final_document.md
```

### 6. Manifest Creation

```
Processing Complete
   │
   └─→ Create Manifest
         │
         ├─→ Document Info
         │     • source_document
         │     • processed_date
         │     • total_entities
         │
         ├─→ Statistics
         │     • entity_type_counts
         │       - text: 8
         │       - table: 4
         │       - diagram: 2
         │
         └─→ Entity List
               • id, type, page, position
               • confidence score
               • file path
```

## Data Flow Example

### Input PDF Page:

```
┌────────────────────────────────┐
│ EMERGENCY REPORTING            │ ← Text Block
│                                │
│ Masters must report...         │ ← Text Block
│                                │
│ ┌──────────────────────────┐  │
│ │ Vessel  │ Flag │ Contact │  │ ← Table (native PDF)
│ │ SHIP A  │ MAL  │ +1234   │  │
│ └──────────────────────────┘  │
│                                │
│ [Image of flowchart]           │ ← Image (needs Vision)
└────────────────────────────────┘
```

### Processing:

```
Docling Extracts:
  ├─ Text: "EMERGENCY REPORTING"
  ├─ Text: "Masters must report..."
  ├─ Table: [native table structure]
  └─ Image: [PIL Image object]

Vision Processes Image:
  ├─ Classify: "diagram"
  └─ Extract: [Mermaid code]

Entities Created:
  ├─ E001_text.md      (heading)
  ├─ E002_text.md      (paragraph)
  ├─ E003_table.yaml   (contact table)
  └─ E004_diagram.mmd  (flowchart)
```

### Output Files:

```
output/
├── entities/
│   ├── E001_text.md
│   │   ---
│   │   entity_id: E001
│   │   type: text
│   │   ---
│   │   ## Emergency Reporting
│   │
│   ├── E002_text.md
│   │   ---
│   │   entity_id: E002
│   │   ---
│   │   Masters must report...
│   │
│   ├── E003_table.yaml
│   │   # entity_id: E003
│   │   # type: table
│   │   vessels:
│   │     - name: "SHIP A"
│   │       flag: "MAL"
│   │       contact: "+1234"
│   │
│   └── E004_diagram.mmd
│       %% entity_id: E004
│       %% type: diagram
│       graph TD
│         A[Start] --> B[End]
│
├── final_document.md
│   ---
│   document_title: "Emergency Manual"
│   total_entities: 4
│   ---
│
│   <!-- Entity: E001 | Type: text | Page: 1 -->
│   ## Emergency Reporting
│
│   <!-- Entity: E002 | Type: text | Page: 1 -->
│   Masters must report...
│
│   <!-- Entity: E003 | Type: table | Page: 1 -->
│   ```yaml
│   vessels:
│     - name: "SHIP A"
│   ```
│
│   <!-- Entity: E004 | Type: diagram | Page: 1 -->
│   ```mermaid
│   graph TD
│     A[Start] --> B[End]
│   ```
│
└── manifest.yaml
    source_document: "manual.pdf"
    total_entities: 4
    entity_type_counts:
      text: 2
      table: 1
      diagram: 1
    entities:
      - id: E001
        type: text
        page: 1
        confidence: 1.0
        file: "entities/E001_text.md"
      ...
```

## Performance Characteristics

```
Pipeline Stage          Time        API Calls    Cost
─────────────────────────────────────────────────────
Docling Extraction      Fast        0            $0
  └─ Per page          ~1-2 sec    -            -

Vision Classification   Medium      1 per image  Low
  └─ Per image          ~1-2 sec    1            ~$0.01

Vision Extraction       Medium      1 per image  Med
  └─ Per image          ~2-5 sec    1            ~$0.02-0.05

Entity Processing       Fast        0            $0
  └─ Per entity         <0.1 sec    -            -

Assembly                Fast        0            $0
  └─ Per document       <1 sec      -            -
─────────────────────────────────────────────────────
Total (10 images)       ~40-80 sec  20 calls     ~$0.30-0.60
Total (50 images)       ~200-400sec 100 calls    ~$1.50-3.00
```

## Error Handling Flow

```
API Call
   │
   ├─→ Success
   │     └─→ Continue
   │
   └─→ Failure
         │
         ├─→ Retry #1 (wait 4 sec)
         │     │
         │     ├─→ Success → Continue
         │     └─→ Fail → Next retry
         │
         ├─→ Retry #2 (wait 8 sec)
         │     │
         │     ├─→ Success → Continue
         │     └─→ Fail → Next retry
         │
         └─→ Retry #3 (wait 16 sec)
               │
               ├─→ Success → Continue
               └─→ Final Fail
                     │
                     ├─→ Log error
                     ├─→ Skip entity
                     └─→ Continue processing
```

---

This visual flow shows the complete journey from PDF input to standardized output files, with every step clearly documented.
