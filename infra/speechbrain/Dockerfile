FROM public.ecr.aws/lambda/python:3.10

# Install system dependencies for audio processing
RUN yum update -y && \
    yum install -y libsndfile && \
    yum clean all

# Copy requirements and install
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app code
COPY app.py ${LAMBDA_TASK_ROOT}

# Pre-download the SpeechBrain ECAPA-TDNN model to bake it into the image
# This avoids downloading it on cold starts
RUN python -c "from speechbrain.inference.speaker import SpeakerRecognition; SpeakerRecognition.from_hparams(source='speechbrain/spkrec-ecapa-voxceleb', savedir='tmpdir')"

# Set the CMD to your handler
CMD ["app.handler"]
