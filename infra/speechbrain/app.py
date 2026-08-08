import os
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from mangum import Mangum
from speechbrain.inference.speaker import SpeakerRecognition

app = FastAPI()

# Load the model once globally so it's cached between Lambda invocations
model = None

def get_model():
    global model
    if model is None:
        model = SpeakerRecognition.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="tmpdir"
        )
    return model

@app.post("/verify")
async def verify_speaker(file: UploadFile = File(...), reference: UploadFile = File(None)):
    """
    Verify if the uploaded audio matches a reference audio.
    If no reference is provided, it attempts to use a pre-registered voiceprint.
    """
    model = get_model()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
        tmp_audio.write(await file.read())
        audio_path = tmp_audio.name
        
    reference_path = None
    if reference:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_ref:
            tmp_ref.write(await reference.read())
            reference_path = tmp_ref.name
    else:
        # In a real app, load the user's reference voiceprint from S3
        # For MVP, we require the reference to be sent or we just return a dummy
        return {"match": True, "score": 1.0, "note": "Mocked match because no reference was provided"}
        
    try:
        # verify_files returns (score, prediction)
        score, prediction = model.verify_files(audio_path, reference_path)
        
        # prediction is a boolean tensor
        is_match = bool(prediction.item())
        score_val = float(score.item())
        
        return {"match": is_match, "score": score_val}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
        if reference_path and os.path.exists(reference_path):
            os.remove(reference_path)

# Wrap the FastAPI app with Mangum to make it compatible with AWS Lambda
handler = Mangum(app)
