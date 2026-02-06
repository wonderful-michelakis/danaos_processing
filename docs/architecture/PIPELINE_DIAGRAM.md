# Document Processing Pipeline - Mermaid Diagrams

## Complete End-to-End Pipeline

```mermaid
graph TB
    Start([PDF Document]) --> Extract[Step 1: Extract<br/>run_pipeline.py]

    Extract --> Entities[(entities/)]
    Extract --> FinalDoc[(final_document.md)]
    Extract --> Manifest[(manifest.yaml)]

    FinalDoc --> Judge[Step 2: Judge<br/>run_judge.py]
    Judge --> JudgeDoc[(final_document_judge.md)]

    JudgeDoc --> Convert[Step 3: Convert<br/>convert_to_friendly.py]
    FinalDoc -.->|alternative| Convert
    Convert --> HTML[(friendly.html)]

    Start --> Viewer[Step 4: Review<br/>compare_viewer.py]
    HTML --> Viewer
    Viewer --> Corrections[(corrections.yaml)]
    Viewer -->|regenerate| Convert

    classDef stepClass fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef fileClass fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef startClass fill:#e8f5e9,stroke:#1b5e20,stroke-width:3px

    class Extract,Judge,Convert,Viewer stepClass
    class Entities,FinalDoc,Manifest,JudgeDoc,HTML,Corrections fileClass
    class Start startClass
```

## Step 1: Extraction Detail

```mermaid
graph TB
    Start([PDF Document]) --> Docling[Docling Extraction]

    Docling --> TextBlock[Text Blocks]
    Docling --> Tables[PDF Tables]
    Docling --> Images[Embedded Images]

    %% Text processing path
    TextBlock --> ListCheck{Consecutive<br/>list items?}
    ListCheck -->|Yes| MergeList[Merge into<br/>single entity]
    ListCheck -->|No| TextMD[Convert to Markdown]
    MergeList --> TextMD
    TextMD --> SaveText[Save .md file]

    %% Table processing path with validation
    Tables --> TableMD[Export to Markdown]
    TableMD --> TableYAML[Convert to YAML]
    TableYAML --> Validate{Validate Quality}

    Validate -->|Valid| UseDocling[Use Docling Result<br/>confidence: 1.0]
    Validate -->|Invalid| ExtractRegion[PyMuPDF: Extract<br/>Table Region]
    ExtractRegion --> VisionTable[Vision API:<br/>Extract Table]
    VisionTable --> UseVision[Vision Result<br/>confidence: 0.85]

    UseDocling --> SaveYAML[Save .yaml file]
    UseVision --> SaveYAML

    %% Image processing path
    Images --> Classify[Vision API:<br/>Classify Image]
    Classify --> ClassResult{Type?}

    ClassResult -->|TEXT| ExtractText[Extract Text]
    ClassResult -->|TABLE| ExtractImgTable[Extract Table]
    ClassResult -->|DIAGRAM| ExtractDiagram[Extract Diagram]
    ClassResult -->|MIXED| ExtractMixed[Extract Mixed]

    ExtractText --> SaveImgText[Save .md file]
    ExtractImgTable --> SaveYAML
    ExtractDiagram --> SaveMermaid[Save .mmd file]
    ExtractMixed --> SaveMermaid

    %% Assembly
    SaveText --> Assemble[Assemble Document]
    SaveYAML --> Assemble
    SaveImgText --> Assemble
    SaveMermaid --> Assemble

    Assemble --> FinalDoc[final_document.md]
    Assemble --> ManifestFile[manifest.yaml]

    classDef doclingClass fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef visionClass fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef validationClass fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef entityClass fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef outputClass fill:#fff9c4,stroke:#f57f17,stroke-width:3px

    class Docling,TextBlock,Tables,Images doclingClass
    class Classify,ExtractText,ExtractImgTable,ExtractDiagram,ExtractMixed,VisionTable visionClass
    class Validate,ListCheck validationClass
    class SaveText,SaveYAML,SaveImgText,SaveMermaid entityClass
    class FinalDoc,ManifestFile outputClass
```

## Step 2: Judge Flow

```mermaid
graph TB
    Input([final_document.md]) --> Replace[Replace HTML markers<br/>with ENTITY tokens]
    Replace --> SendLLM[Send to LLM<br/>with judge_prompt.md]

    SendLLM --> Merge[Merge fragmented entities]
    SendLLM --> Format[Apply format specs]
    SendLLM --> Fix[Fix OCR artifacts]

    Merge --> Result[LLM Output]
    Format --> Result
    Fix --> Result

    Result --> RestoreMarkers[Convert tokens back<br/>to HTML markers]
    RestoreMarkers --> ValidateMarkers{Markers<br/>preserved?}

    ValidateMarkers -->|Yes| WriteJudge[Write final_document_judge.md]
    ValidateMarkers -->|No| Fallback[Fall back to<br/>original document]

    classDef processClass fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef checkClass fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef outputClass fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef failClass fill:#ffebee,stroke:#b71c1c,stroke-width:2px

    class Replace,SendLLM,Merge,Format,Fix,Result,RestoreMarkers processClass
    class ValidateMarkers checkClass
    class WriteJudge outputClass
    class Fallback failClass
```

## Step 3: HTML Conversion

```mermaid
graph TB
    Input([Markdown file]) --> Parse[Parse entity markers]
    Parse --> Loop[For each entity]

    Loop --> TypeCheck{Entity type?}

    TypeCheck -->|Text/Heading| RenderMD[Render Markdown to HTML]
    TypeCheck -->|YAML Table| ParseYAML[Parse YAML]
    TypeCheck -->|Mermaid| Sanitize[Sanitize Mermaid code]

    ParseYAML --> RenderTable[Render HTML table]
    Sanitize --> WrapMermaid[Wrap in mermaid pre tag]

    RenderMD --> AddBadge[Add entity badge]
    RenderTable --> AddBadge
    WrapMermaid --> AddBadge

    AddBadge --> Assemble[Assemble HTML page]
    Assemble --> AddCSS[Add CSS + mermaid.js]
    AddCSS --> WriteHTML[Write friendly.html]

    classDef processClass fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef checkClass fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef outputClass fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px

    class Parse,Loop,RenderMD,ParseYAML,Sanitize,RenderTable,WrapMermaid,AddBadge,Assemble,AddCSS processClass
    class TypeCheck checkClass
    class WriteHTML outputClass
```

## Step 4: Correction Flow

```mermaid
graph TB
    UserClick([User clicks<br/>entity badge]) --> FetchEntity[GET /api/entity/id]
    FetchEntity --> ShowModal[Show correction modal]

    ShowModal --> ChooseMethod{Method?}

    ChooseMethod -->|Manual| EditTextarea[Edit in textarea]
    ChooseMethod -->|AI-Assisted| DescribeIssue[Describe the issue]

    DescribeIssue --> AICall[POST /api/correct-with-ai]
    AICall --> ReviewAI[Review AI suggestion]

    EditTextarea --> Save[POST /api/save-correction]
    ReviewAI --> Save

    Save --> SaveYAML[Save to corrections.yaml]
    Save --> UpdateSource{Judge mode?}

    UpdateSource -->|Yes| EditJudgeMD[Edit entity in<br/>final_document_judge.md]
    UpdateSource -->|No| EditEntityFile[Edit entity file<br/>in entities/]
    EditEntityFile --> RebuildMD[Rebuild final_document.md]

    EditJudgeMD --> RegenHTML[Regenerate HTML]
    RebuildMD --> RegenHTML

    RegenHTML --> ReloadViewer[Reload HTML panel]
    ReloadViewer --> Highlight[Highlight corrected entity]

    classDef userClass fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef processClass fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef apiClass fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef checkClass fill:#f3e5f5,stroke:#4a148c,stroke-width:2px

    class UserClick,ShowModal,ChooseMethod userClass
    class EditTextarea,DescribeIssue,ReviewAI,SaveYAML,EditJudgeMD,EditEntityFile,RebuildMD,RegenHTML,ReloadViewer,Highlight processClass
    class FetchEntity,AICall,Save apiClass
    class UpdateSource checkClass
```

## Output File Structure

```mermaid
graph TB
    Root["outputs/name/"] --> Entities["entities/"]
    Root --> FinalDoc["final_document.md"]
    Root --> JudgeDoc["final_document_judge.md"]
    Root --> FriendlyHTML["final_document_friendly.html"]
    Root --> JudgeHTML["final_document_judge_friendly.html"]
    Root --> Manifest["manifest.yaml"]
    Root --> Corrections["corrections.yaml"]

    Entities --> Text["E001_EntityType.TEXT.md"]
    Entities --> Table["E002_EntityType.TABLE.yaml"]
    Entities --> Diagram["E003_EntityType.DIAGRAM.mmd"]
    Entities --> ImgText["E004_EntityType.IMAGE_TEXT.md"]

    FinalDoc -->|Step 1| Note1["All entities assembled<br/>with HTML markers"]
    JudgeDoc -->|Step 2| Note2["Merged and normalized<br/>entities"]
    JudgeHTML -->|Step 3| Note3["Styled HTML with<br/>clickable badges"]
    Corrections -->|Step 4| Note4["Audit trail of<br/>all corrections"]

    classDef dirClass fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef fileClass fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef noteClass fill:#f1f8e9,stroke:#558b2f,stroke-width:1px

    class Root,Entities dirClass
    class Text,Table,Diagram,ImgText,FinalDoc,JudgeDoc,FriendlyHTML,JudgeHTML,Manifest,Corrections fileClass
    class Note1,Note2,Note3,Note4 noteClass
```
