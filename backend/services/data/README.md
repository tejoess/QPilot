# QPilot Data Storage

This folder stores all generated data organized by session ID.

## Folder Structure

```
data/
├── {session_id}/
│   ├── syllabus_raw.txt              # Raw extracted syllabus text
│   ├── syllabus.json                 # Parsed and structured syllabus
│   ├── pyqs_raw.txt                  # Raw extracted PYQ text
│   ├── pyqs.json                     # Parsed and structured PYQs
│   ├── blueprint.json                # Generated question paper blueprint
│   ├── blueprint_verification.json   # Blueprint verification results
│   ├── draft_paper.json              # Selected questions for the paper
│   ├── paper_verification.json       # Paper verification results
│   ├── final_paper.json              # Final approved question paper
│   ├── final_question_paper.pdf      # Final PDF (TODO)
│   └── session_summary.json          # Session metadata and summary
```

## File Descriptions

### Input Files
- **syllabus_raw.txt**: Raw text extracted from the uploaded syllabus PDF
- **pyqs_raw.txt**: Raw text extracted from the PYQ PDF

### Processed Data
- **syllabus.json**: Structured syllabus with modules, topics, and subtopics
- **pyqs.json**: Structured PYQ database with questions categorized by topic

### Generation Pipeline
- **blueprint.json**: Question paper structure with topic distribution and marks
- **blueprint_verification.json**: Verification results for the blueprint
- **draft_paper.json**: Selected questions mapped to blueprint slots
- **paper_verification.json**: Quality checks and verification results

### Output
- **final_paper.json**: The approved final question paper in JSON format
- **final_question_paper.pdf**: The rendered PDF (coming soon)
- **session_summary.json**: Metadata about the generation session

## Session Summary Format

```json
{
  "session_id": "uuid-string",
  "timestamp": "2026-02-22T10:30:00",
  "status": "completed",
  "total_marks": 80,
  "total_questions": 10,
  "verdict": "ACCEPTED",
  "rating": 8.5,
  "files_generated": { ... }
}
```

## Usage

Each session generates a unique folder identified by a UUID. All intermediate and final results are automatically saved during the pipeline execution.

You can access any session's data by navigating to: `data/{session_id}/`
