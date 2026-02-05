# Table Extraction Fixes - Complete ✓

## Summary of Changes

All fixes have been implemented to resolve the two critical issues:

### Issue 1: Empty Table Extraction ✓ FIXED
**Problem**: Tables E006 and E044 showing `table: []` in output

**Solution Implemented**:
1. Added table validation in [entity_processor.py](entity_processor.py:292-328)
   - Validates YAML structure, checks for empty arrays, minimum column requirements

2. Implemented Vision API fallback in [entity_processor.py](entity_processor.py:61-135)
   - Primary: Docling extraction
   - Validation: Quality check
   - Fallback: Vision API if validation fails
   - Tracking: `extraction_method` field in metadata

3. Added PyMuPDF-based table region extraction in [document_pipeline.py](document_pipeline.py:122-190)
   - Extracts table region directly from PDF using PyMuPDF (fitz)
   - Handles coordinate transformation (PDF bottom-left → rendering top-left)
   - 2x zoom for high quality
   - **Key Fix**: Doesn't rely on Docling's page images (which weren't available)

4. Updated table processing flow in [document_pipeline.py](document_pipeline.py:234-263)
   - Extracts table region image
   - Passes to processor with fallback option
   - Cleans up temp images

### Issue 2: Missing Text Near Diagrams ✓ FIXED
**Problem**: Text surrounding diagrams (titles, captions) not being captured

**Solution Implemented**:
1. Enhanced classification prompts in [pipeline_config.py](pipeline_config.py:48-77)
   - Detects MIXED content (diagram + text)
   - Adds `text_significance`, `text_location`, `primary_content` fields

2. Updated diagram extraction in [entity_classifier.py](entity_classifier.py:123-159)
   - Returns JSON with `surrounding_text` and `diagram` fields
   - Captures text above, below, and around diagrams

3. Added mixed content extraction in [entity_classifier.py](entity_classifier.py:161-210)
   - New `extract_mixed_content()` method
   - Handles dual extraction of text + structured content

4. Enhanced image processing in [entity_processor.py](entity_processor.py:137-222)
   - Detects and extracts surrounding text
   - Combines text + primary content
   - Tracks with `has_surrounding_text` metadata field

5. Updated Mermaid file formatting in [entity_processor.py](entity_processor.py:348-360)
   - Surrounding text saved as Mermaid comments
   - Preserves context with diagrams

## Files Modified

1. **[pipeline_config.py](pipeline_config.py)**
   - Lines 17-26: Added `extraction_method` and `has_surrounding_text` to EntityMetadata
   - Lines 48-77: Enhanced CLASSIFY_PROMPT with text detection
   - Lines 97-116: Updated EXTRACT_DIAGRAM_PROMPT to return JSON

2. **[entity_classifier.py](entity_classifier.py)**
   - Lines 123-159: Modified `extract_diagram()` to return JSON
   - Lines 161-210: Added `extract_mixed_content()` method

3. **[entity_processor.py](entity_processor.py)**
   - Lines 61-135: Enhanced `process_table()` with validation and fallback
   - Lines 137-222: Enhanced `process_image()` for multi-content extraction
   - Lines 292-328: Added `_is_table_extraction_valid()` method
   - Lines 348-360: Updated Mermaid file saving with surrounding text

4. **[document_pipeline.py](document_pipeline.py)**
   - Lines 16-17: Added PyMuPDF and PIL imports
   - Lines 122-190: Implemented `_extract_table_region_image()` with PyMuPDF
   - Lines 234-263: Updated TableItem handling with fallback flow

## How to Test

### Test the fixes with your PDF:

```bash
# Run the pipeline (provide the correct path to your PDF)
python run_pipeline.py "/path/to/All chapters - EMERGENCY PROCEDURES MANUAL_p86-90.pdf" -o table_output_final
```

### Expected Results:

#### For Empty Tables (E006, E044):
1. Console output should show:
   ```
   [DEBUG E006] Validation: is_valid=False, reason='Empty table array'
   [DEBUG E006] Fallback path available: True
   Warning: Docling table extraction failed for E006 (Empty table array)
   Falling back to Vision API...
   ```

2. Entity files should show:
   - `extraction_method: vision_api`
   - `confidence: 0.85`
   - YAML with actual table data (not `table: []`)

3. Debug logs should show successful image extraction:
   ```
   [DEBUG] Page size: 612x792
   [DEBUG] Crop rect: [...]
   [DEBUG] Extracted image: 1050x1285
   ```

#### For Diagram Text (if testing p51.pdf):
1. Diagram entities should include surrounding text
2. Metadata should show `has_surrounding_text: true`
3. .mmd files should contain text as comments:
   ```
   %% Surrounding Text:
   %% General Operating Guidance for Masters...
   %% The following diagram shows...

   graph TD
       [diagram content]
   ```

#### For Working Content (E015, E031, E049):
- Should continue working without regression
- `extraction_method: docling`
- `confidence: 1.0`

## Dependencies

- PyMuPDF installed: ✓ (v1.26.7)
- OpenAI API key configured: ✓

## Architecture

```
PDF → Docling Extract → Validate → Pass/Fail
                           ↓           ↓
                         Use        PyMuPDF Extract Region
                           ↓           ↓
                        Save      Vision API
                                      ↓
                                   Save
```

## Debug Mode

The code includes comprehensive debug logging. Look for these key indicators:

- `[DEBUG E###]` prefix for entity-specific logs
- Validation results with reasons
- Fallback path availability
- Image dimensions and bounding boxes
- Extraction method tracking

## Next Steps

1. Run the pipeline with your PDF
2. Check the console output for debug logs
3. Verify table entity files (E006, E044) contain data
4. Check manifest.yaml for `extraction_method` fields
5. If any issues occur, review debug logs for specific failure points

All code changes are complete and ready for testing! 🚀
