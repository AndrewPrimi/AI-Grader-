from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import nbformat

app = FastAPI()

# This is your grading function placeholder
def grade_notebook(code_cells):
    # Example: your model analyzes code_cells and returns a score
    # Replace this with your actual AI grader
    total_score = 0
    for code in code_cells:
        # Example: give 10 points per cell that contains code
        if code.strip():
            total_score += 10
    return min(total_score, 100)

@app.post("/submit-notebook/")
async def submit_notebook(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        return JSONResponse(content={"error": "Only .pdf files are allowed."}, status_code=400)
    
    contents = await file.read()
    notebook = nbformat.reads(contents.decode("utf-8"), as_version=4)
    
    # Extract code cells from the notebook
    code_cells = [cell['source'] for cell in notebook.cells if cell.cell_type == 'code']
    
    # Pass the code to your model for grading
    score = grade_notebook(code_cells)
    
    return {"filename": file.filename, "score": score}