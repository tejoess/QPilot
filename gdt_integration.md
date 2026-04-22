Current state after code walkthrough

The current GDT code is not production-ready and is not wired into runtime flows.
It is a notebook-style script with shell magics and Colab-specific calls in gdt_module.py:10, gdt_module.py:365, gdt_module.py:370.
It uses eval on edge label keys in gdt_module.py:71, which is unsafe.
Question generation/rephrasing currently returns only question text.
Rephrase and generation functions in question_service.py:370 and question_service.py:454 output plain text only.
Draft question payload contains text + metadata only at question_service.py:774.
There is already a partial KG-enrichment feature in question service, but pipeline does not pass KG into select_questions.
question_service supports knowledge_graph input at question_service.py:606.
pipeline currently calls select_questions without knowledge_graph in pipeline.py:562.
Repair/reselection path will drop any future GDT fields unless explicitly preserved.
Reselected question objects are rebuilt with fixed keys in paper_fix.py:235 and do not carry custom media fields.
PDF and DOCX template rendering are text-only.
PDF rendering only writes Paragraph question text in paper_pdf_gen.py:94, paper_pdf_gen.py:102.
DOCX template renderer maps placeholders to plain text only in renderer.py:57, renderer.py:238.
Frontend rendering is text-only; no LaTeX or media rendering support exists.
Generated paper view prints question_text directly in GeneratedPaperView.tsx:144.
Result page also maps to plain text in frontend/src/app/qpilot/[projectId]/resultqp/page.tsx.
No KaTeX/MathJax deps in package.json.
High-impact files that should change

Backend generation and data flow

gdt_module.py
question_service.py
pipeline.py
paper_fix.py
verify_paper.py
Backend output/rendering

paper_pdf_gen.py
renderer.py
main.py (response payload and file-url propagation)
blob_upload.py
Backend schema/dependency

llm_schemas.py
requirements.txt
requirements.txt
Frontend contract + rendering

api.ts
projectApi.ts
useGenerationFlow.ts:190
GeneratedPaperView.tsx
frontend/src/app/qpilot/[projectId]/resultqp/page.tsx
package.json
Recommended integration design (safe, backward-compatible)

Standardize question JSON contract first.
Keep current fields unchanged.
Add optional fields only:
question_assets: list of image/formula/graph/table assets.
gdt_blocks: normalized structural blocks (table, graph_ds, plot, formula).
has_visuals: boolean.
render_mode: text_only | text_with_assets.
This avoids breaking old papers and old UI.
Refactor GDT module into a pure service module.
Convert gdt_module.py into importable utilities only.
Remove shell magics, demo execution, downloads.
Replace eval parsing with safe parser.
Expose functions like:
detect_gdt_requirements(question_text, marks, bloom)
generate_gdt_blocks(...)
render_formula_image(...)
render_graph_image(...)
upload_assets_and_return_urls(...)
Integrate GDT in generation and rephrasing paths.
In question_service.py:
prompt additions for structured output (question_text + optional gdt_blocks/latex_segments)
post-processing to normalize and validate blocks
call gdt render/upload utilities
write question_assets and gdt_blocks into each question object
In paper_fix.py:
ensure reselection path regenerates/preserves assets and gdt fields.
Ensure pipeline passes complete context.
Update pipeline.py:562 to pass knowledge_graph into select_questions.
Ensure draft_paper/final_paper persistence includes added fields as-is.
Update renderers for PDF and DOCX template.
PDF in paper_pdf_gen.py:
detect asset type and insert image/table blocks after question text.
support latex by either:
pre-rendered image url/path inserted into PDF, or
direct reportlab math support via image fallback.
DOCX template in renderer.py:
current placeholder engine is text-only, so add explicit media placeholders or post-row insertion logic.
define deterministic placeholder naming for assets, like [1a_img_1], [1a_formula_1], [1a_table_1].
Frontend rendering support.
Update TypeScript types in api.ts.
Update API response typing mismatch and include new fields in projectApi.ts:558.
In GeneratedPaperView.tsx, render:
question text
inline/block formulas
images/tables/graphs based on asset type
In frontend/src/app/qpilot/[projectId]/resultqp/page.tsx, carry through the same fields into preview and export flows.
Add LaTeX renderer deps in package.json (KaTeX route recommended).
Edge cases you should explicitly handle

No GDT needed.
Keep behavior identical to today (text-only path).
Asset generation fails partially.
Question should still return with text.
Store per-asset error metadata, do not fail entire paper.
Reselection/repair loops.
Repaired questions must re-render assets or preserve prior valid assets.
Avoid losing fields in paper_fix.py:235.
URL lifecycle.
Local temporary paths must not leak into frontend payload.
Return stable URLs only after upload.
Template mismatch.
If template has no media placeholders, fallback to appending media after question text.
Security.
Remove eval usage in graph parsing from gdt_module.py:71.
Validate external URLs and sanitize text used in templates/PDF.
Dependency drift.
backend requirements currently miss matplotlib/networkx/pandas for full GDT support.
Align dependency files and Docker build.
Rollout plan (practical sequence)

Phase 1: Contract and backend plumbing
Define question_assets/gdt_blocks schema.
Wire question_service + pipeline + paper_fix.
Persist fields end-to-end.
Phase 2: Rendering backend
Add PDF GDT/LaTeX rendering.
Add DOCX template media insertion strategy.
Phase 3: Frontend rendering
Type updates.
Generated paper + result page media rendering.
LaTeX rendering integration.
Phase 4: Hardening
Add fallback behavior tests.
Test with:
no GDT
table only
graph only
formula only
mixed assets
repair-loop regenerated questions
template rendering with and without placeholders
Key risks to fix early

Runtime break risk from current notebook code in gdt_module.py:10.
Data-loss risk in repair path in paper_fix.py:235.
Rendering gap risk in paper_pdf_gen.py:94 and renderer.py:238.
Frontend schema drift risk between api.ts:56 and projectApi.ts:558.
No code changes were made. This is analysis-only as requested.