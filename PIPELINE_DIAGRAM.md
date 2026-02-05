# Document Processing Pipeline - Mermaid Flow Diagram

## Complete System Architecture

```mermaid
graph TB
    Start([PDF Document]) --> Docling[Docling Extraction]

    Docling --> TextBlock[Text Blocks]
    Docling --> Tables[PDF Tables]
    Docling --> Images[Embedded Images]

    %% Text processing path
    TextBlock --> TextMD[Convert to Markdown]
    TextMD --> TextEntity[Create Text Entity]
    TextEntity --> SaveText[Save .md file]

    %% Table processing path with validation
    Tables --> TableMD[Export to Markdown]
    TableMD --> TableYAML[Convert to YAML]
    TableYAML --> Validate{Validate Quality}

    Validate -->|Valid: Has 2+ cols<br/>Has data rows<br/>Valid YAML| UseDocling[Use Docling Result]
    Validate -->|Invalid: Empty/Bad| ExtractRegion[PyMuPDF: Extract<br/>Table Region Image]

    UseDocling --> TableEntity1[Create Table Entity<br/>method: docling<br/>confidence: 1.0]
    ExtractRegion --> VisionTable[Vision API:<br/>Extract Table]
    VisionTable --> TableEntity2[Create Table Entity<br/>method: vision_api<br/>confidence: 0.85]

    TableEntity1 --> SaveYAML[Save .yaml file]
    TableEntity2 --> SaveYAML

    %% Image processing path
    Images --> Classify[Vision API:<br/>Classify Image]
    Classify --> ClassResult{Classification<br/>Result}

    ClassResult -->|TEXT| ExtractText[Vision: Extract<br/>Text → Markdown]
    ClassResult -->|TABLE| ExtractImgTable[Vision: Extract<br/>Table → YAML]
    ClassResult -->|DIAGRAM| CheckText{Has Surrounding<br/>Text?}
    ClassResult -->|MIXED| ExtractMixed[Vision: Extract<br/>Mixed Content]

    CheckText -->|Yes<br/>text_significance<br/>high/medium| ExtractMixed
    CheckText -->|No| ExtractDiagram[Vision: Extract<br/>Diagram → Mermaid]

    ExtractText --> ImageTextEntity[Create Image Text Entity]
    ExtractImgTable --> ImageTableEntity[Create Table Entity]
    ExtractDiagram --> DiagramEntity1[Create Diagram Entity<br/>has_surrounding_text: false]
    ExtractMixed --> DiagramEntity2[Create Diagram Entity<br/>has_surrounding_text: true]

    ImageTextEntity --> SaveImageText[Save .md file]
    ImageTableEntity --> SaveYAML
    DiagramEntity1 --> SaveMermaid[Save .mmd file]
    DiagramEntity2 --> SaveMermaid

    %% Final assembly
    SaveText --> Assemble[Assemble All Entities]
    SaveYAML --> Assemble
    SaveImageText --> Assemble
    SaveMermaid --> Assemble

    Assemble --> FinalDoc[Create Final Document<br/>with Entity Markers]
    Assemble --> Manifest[Create Manifest<br/>with Metadata]

    FinalDoc --> Output[Output Files]
    Manifest --> Output

    Output --> End([Complete!])

    %% Styling
    classDef doclingClass fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef visionClass fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef validationClass fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef entityClass fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef outputClass fill:#fff9c4,stroke:#f57f17,stroke-width:3px

    class Docling,TextBlock,Tables,Images doclingClass
    class Classify,ExtractText,ExtractImgTable,ExtractDiagram,ExtractMixed,VisionTable visionClass
    class Validate,CheckText validationClass
    class TextEntity,TableEntity1,TableEntity2,ImageTextEntity,ImageTableEntity,DiagramEntity1,DiagramEntity2 entityClass
    class Output,End outputClass
```

## Table Fallback System (Detailed)

```mermaid
graph TB
    TableDetected([Table Detected<br/>by Docling]) --> Export[Export to Markdown]
    Export --> Convert[Convert MD → YAML]
    Convert --> Val1{Check 1:<br/>Non-empty<br/>markdown?}

    Val1 -->|No| Fail1[Fail: Empty output]
    Val1 -->|Yes| Val2{Check 2:<br/>Valid YAML<br/>structure?}

    Val2 -->|No| Fail2[Fail: Invalid YAML]
    Val2 -->|Yes| Val3{Check 3:<br/>Has data<br/>rows?}

    Val3 -->|No| Fail3[Fail: No rows]
    Val3 -->|Yes| Val4{Check 4:<br/>2+ columns?}

    Val4 -->|No| Fail4[Fail: Insufficient cols]
    Val4 -->|Yes| Success[✓ Validation Passed]

    Success --> UseDocling[Use Docling Extraction<br/>confidence: 1.0<br/>method: docling]

    Fail1 --> Fallback[Initiate Fallback]
    Fail2 --> Fallback
    Fail3 --> Fallback
    Fail4 --> Fallback

    Fallback --> PyMuPDF[PyMuPDF: Open PDF]
    PyMuPDF --> GetPage[Get Page<br/>Convert 1-based → 0-based]
    GetPage --> Transform[Transform Coordinates<br/>PDF coords → Render coords<br/>y' = page_height - y]
    Transform --> Crop[Create Rect from BBox<br/>Render at 2x resolution]
    Crop --> SaveTemp[Save Temp PNG]
    SaveTemp --> VisionCall[Vision API Call:<br/>Extract Table]

    VisionCall --> VisionSuccess{Vision API<br/>Success?}

    VisionSuccess -->|Yes| UseVision[Use Vision Result<br/>confidence: 0.85<br/>method: vision_api]
    VisionSuccess -->|No| BothFailed[Create Error YAML<br/>confidence: 0.0<br/>method: failed]

    UseDocling --> Cleanup1[Save Entity]
    UseVision --> Cleanup2[Delete Temp Image<br/>Save Entity]
    BothFailed --> Cleanup3[Delete Temp Image<br/>Save Error Entity]

    Cleanup1 --> Done([Entity Saved])
    Cleanup2 --> Done
    Cleanup3 --> Done

    %% Styling
    classDef validationClass fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef successClass fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef failClass fill:#ffebee,stroke:#b71c1c,stroke-width:2px
    classDef fallbackClass fill:#fff3e0,stroke:#e65100,stroke-width:2px

    class Val1,Val2,Val3,Val4 validationClass
    class Success,UseDocling,UseVision successClass
    class Fail1,Fail2,Fail3,Fail4,BothFailed failClass
    class Fallback,PyMuPDF,GetPage,Transform,Crop,SaveTemp,VisionCall fallbackClass
```

## Mixed Content Extraction Flow

```mermaid
graph TB
    ImageInput([Image from PDF]) --> Classify[Vision API: Classify]

    Classify --> ClassJSON{Classification<br/>Response}

    ClassJSON --> CheckType{Check type +<br/>text_significance}

    CheckType -->|type: MIXED| Mixed[Use Mixed Content<br/>Extraction]
    CheckType -->|type: DIAGRAM<br/>+ text_sig: high/med| Mixed
    CheckType -->|type: TABLE<br/>+ text_sig: high/med| Mixed
    CheckType -->|type: DIAGRAM<br/>+ text_sig: low/none| StandardDiagram[Standard Diagram<br/>Extraction]
    CheckType -->|type: TABLE<br/>+ text_sig: low/none| StandardTable[Standard Table<br/>Extraction]
    CheckType -->|type: TEXT| StandardText[Standard Text<br/>Extraction]

    Mixed --> MixedPrompt[Vision API with<br/>Enhanced Prompt:<br/>Extract surrounding text<br/>+ primary content]

    MixedPrompt --> MixedResult{Response<br/>Format}

    MixedResult --> ParseJSON[Parse JSON Response]
    ParseJSON --> ExtractSurround[Extract:<br/>surrounding_text field]
    ParseJSON --> ExtractPrimary[Extract:<br/>primary_content field]

    ExtractSurround --> Combine[Combine Both Parts]
    ExtractPrimary --> Combine

    Combine --> CreateEntity[Create Entity with:<br/>has_surrounding_text: true<br/>Content: text + primary]

    StandardDiagram --> StandardResult1[Create Entity:<br/>has_surrounding_text: false]
    StandardTable --> StandardResult2[Create Entity:<br/>has_surrounding_text: false]
    StandardText --> StandardResult3[Create Entity:<br/>type: image_text]

    CreateEntity --> SaveFile[Save Entity File]
    StandardResult1 --> SaveFile
    StandardResult2 --> SaveFile
    StandardResult3 --> SaveFile

    SaveFile --> End([Entity Complete])

    %% Styling
    classDef classifyClass fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef mixedClass fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef standardClass fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef entityClass fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px

    class Classify,ClassJSON,CheckType classifyClass
    class Mixed,MixedPrompt,MixedResult,ParseJSON,ExtractSurround,ExtractPrimary,Combine mixedClass
    class StandardDiagram,StandardTable,StandardText,StandardResult1,StandardResult2,StandardResult3 standardClass
    class CreateEntity,SaveFile entityClass
```

## Entity Metadata Structure

```mermaid
graph LR
    Entity[Entity] --> Meta[Metadata]
    Entity --> Content[Content]
    Entity --> FileExt[File Extension]

    Meta --> ID[entity_id: E001]
    Meta --> Type[type: table/diagram/text]
    Meta --> Page[source_page: 1]
    Meta --> Pos[position: 6]
    Meta --> BBox[original_bbox: coordinates]
    Meta --> Conf[confidence: 0.0-1.0]
    Meta --> Notes[processing_notes: details]
    Meta --> Method[extraction_method:<br/>docling/vision_api/failed]
    Meta --> HasText[has_surrounding_text:<br/>true/false]

    Content --> ContentType{Content Type}
    ContentType --> TableYAML[YAML for tables]
    ContentType --> Mermaid[Mermaid for diagrams]
    ContentType --> Markdown[Markdown for text]

    FileExt --> ExtType{Extension Type}
    ExtType --> YAMLExt[.yaml with # comments]
    ExtType --> MermaidExt[.mmd with %% comments]
    ExtType --> MDExt[.md with --- frontmatter]

    %% Styling
    classDef metaClass fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef contentClass fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef newFieldClass fill:#e8f5e9,stroke:#1b5e20,stroke-width:3px

    class Meta,ID,Type,Page,Pos,BBox,Conf,Notes metaClass
    class Method,HasText newFieldClass
    class Content,ContentType,TableYAML,Mermaid,Markdown contentClass
```

## Output File Structure

```mermaid
graph TB
    Root[output/] --> Entities[entities/]
    Root --> Final[final_document.md]
    Root --> Manifest[manifest.yaml]

    Entities --> Text[E001_EntityType.TEXT.md]
    Entities --> Table1[E002_EntityType.TABLE.yaml<br/>method: docling]
    Entities --> Table2[E003_EntityType.TABLE.yaml<br/>method: vision_api]
    Entities --> Diagram[E004_EntityType.DIAGRAM.mmd<br/>has_surrounding_text: true]
    Entities --> ImgText[E005_EntityType.IMAGE_TEXT.md]

    Text --> TextContent[---<br/>entity_id: E001<br/>type: text<br/>confidence: 1.0<br/>---<br/>## Heading<br/>content...]

    Table1 --> Table1Content[# Metadata<br/># extraction_method: docling<br/># confidence: 1.0<br/>table:<br/>  - col1: val1]

    Table2 --> Table2Content[# Metadata<br/># extraction_method: vision_api<br/># confidence: 0.85<br/>table:<br/>  - col1: val1]

    Diagram --> DiagramContent[%% Metadata<br/>%% has_surrounding_text: true<br/>%%<br/>%% Surrounding Text:<br/>%% Instructions here...<br/>graph TD<br/>  A --> B]

    Final --> FinalContent[---<br/>document_title: doc<br/>total_entities: 5<br/>---<br/><br/>Entity markers<br/>+ content...]

    Manifest --> ManifestContent[source_document: file.pdf<br/>total_entities: 5<br/>entity_type_counts:<br/>  text: 2<br/>  table: 2<br/>entities list...]

    %% Styling
    classDef dirClass fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef fileClass fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef contentClass fill:#f1f8e9,stroke:#558b2f,stroke-width:1px

    class Root,Entities dirClass
    class Text,Table1,Table2,Diagram,ImgText,Final,Manifest fileClass
    class TextContent,Table1Content,Table2Content,DiagramContent,FinalContent,ManifestContent contentClass
```

---

## Key Features Highlighted

### ✓ Smart Table Fallback
- Validates Docling extraction quality
- Automatically falls back to Vision API for failed tables
- Tracks extraction method and confidence in metadata

### ✓ Mixed Content Detection
- Detects text surrounding diagrams/tables
- Extracts both components separately
- Preserves context with structured content

### ✓ Quality Tracking
- Every entity has `extraction_method` field
- Confidence scores reflect extraction quality
- Processing notes explain failures

### ✓ Cost Optimization
- Free Docling extraction used whenever possible
- Vision API only called when needed
- Failed validations trigger fallback, not blind API calls

### ✓ Comprehensive Metadata
- Full provenance tracking (page, bbox, position)
- Extraction method transparency
- Surrounding text indicators
- Quality confidence scores
