from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
import shutil
import zipfile
import uuid

app = FastAPI()

BASE_DIR = Path(__file__).parent
WORK_DIR = BASE_DIR / "workdir"
NKI_DIR = BASE_DIR / "nki_templates"
STATIC_DIR = BASE_DIR / "static"

WORK_DIR.mkdir(exist_ok=True)
NKI_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

# TODO: change these names to match your real templates
ROOT_NOTE_TEMPLATES = {
    "C0": "Snare_C0.nki",
    "C1": "Snare_C1.nki",
    "C2": "Snare_C2.nki",
    "C3": "Snare_C3.nki",
    "C4": "Snare_C4.nki",
    "D4": "Snare_D4.nki",
}


@app.get("/", response_class=HTMLResponse)
async def home():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return "<h1>NKI Generator backend is running.</h1>"


@app.post("/generate")
async def generate_instrument(
    root_note: str = Form(...),
    instrument_name: str = Form(...),
    wav_files: list[UploadFile] = File(...)
):
    if not wav_files:
        raise HTTPException(status_code=400, detail="No WAV files uploaded.")

    template_name = ROOT_NOTE_TEMPLATES.get(root_note)
    if not template_name:
        raise HTTPException(status_code=400, detail=f"Unsupported root note: {root_note}")

    template_path = NKI_DIR / template_name
    if not template_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"NKI template not found on server: {template_name}. "
                   f"Upload it into the nki_templates/ folder in the repo."
        )

    job_id = str(uuid.uuid4())
    job_dir = WORK_DIR / job_id
    samples_dir = job_dir / "Samples"
    job_dir.mkdir(parents=True, exist_ok=True)
    samples_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded wavs as-is for now
    for uf in wav_files:
        dest = samples_dir / uf.filename
        with dest.open("wb") as f:
            shutil.copyfileobj(uf.file, f)

    # Copy the correct NKI template
    out_nki = job_dir / template_path.name
    shutil.copy2(template_path, out_nki)

    # Zip NKI + Samples/*
    zip_path = WORK_DIR / f"{instrument_name}_{root_note}_{job_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(out_nki, out_nki.name)
        for p in samples_dir.glob("*"):
            zf.write(p, f"Samples/{p.name}")

    return FileResponse(zip_path, filename=zip_path.name)
