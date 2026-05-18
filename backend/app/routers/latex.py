import subprocess, tempfile, os
from fastapi import APIRouter

router = APIRouter(prefix="/latex")

@router.post("/diff")
def latex_diff(old: str, new: str):
    with tempfile.NamedTemporaryFile("w", suffix=".tex", delete=False) as f1, \
         tempfile.NamedTemporaryFile("w", suffix=".tex", delete=False) as f2:
        f1.write(old); f2.write(new)
        f1_path, f2_path = f1.name, f2.name

    result = subprocess.run(
        ["latexdiff", f1_path, f2_path],
        capture_output=True, text=True
    )
    os.unlink(f1_path); os.unlink(f2_path)
    return {"diff": result.stdout}
