import os
import requests
import zipfile
from tqdm import tqdm
import torch
from TTS.api import TTS
from sentence_transformers import SentenceTransformer
import whisper
from datetime import datetime, timedelta
import ollama
import warnings
import logging

# Suppress specific warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# Set logging level to suppress less important messages
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

def download_file(url, filename):
    """
    Download a file from the given URL and save it with the specified filename.
    """
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))

    with open(filename, 'wb') as file, tqdm(
        desc=filename,
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as progress_bar:
        for data in response.iter_content(chunk_size=1024):
            size = file.write(data)
            progress_bar.update(size)

def extract_zip(zip_path, extract_to):
    """
    Extract a zip file to the specified directory.
    """
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def setup():
    """
    Main setup function to download and extract files.
    """
    # Define the Vosk model URL and its corresponding local paths
    vosk_model_url = 'https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip'
    vosk_model_filename = './models/vosk-model-en-us-0.22.zip'
    vosk_model_folder = './models/vosk-model-en-us-0.22'

    # Create the models directory if it doesn't exist
    os.makedirs('./models', exist_ok=True)

    # Check if Vosk model is already downloaded and extracted
    if not os.path.exists(vosk_model_folder):
        if not os.path.exists(vosk_model_filename):
            # Download the Vosk model
            print(f"Downloading Vosk model...")
            download_file(vosk_model_url, vosk_model_filename)
        
        # Extract the Vosk model
        print(f"Extracting Vosk model...")
        extract_zip(vosk_model_filename, './models')

        # Optionally, remove the zip file after extraction
        os.remove(vosk_model_filename)
        print("Vosk model setup complete.")
    else:
        print("Vosk model already exists. Skipping download and extraction.")

    print("Setting up Ollama models...")
    model_name = "gemma2:latest"

    def check_model_status(model_name):
        try:
            models = ollama.list()
            for model in models['models']:
                if model['name'] == model_name:
                    modified_time = datetime.strptime(model['modified'], "%Y-%m-%dT%H:%M:%S.%fZ")
                    return datetime.utcnow() - modified_time < timedelta(days=1)
            return False
        except Exception:
            return False

    if not check_model_status(model_name):
        print(f"Pulling model {model_name}...")
        ollama.pull(model_name)
    else:
        print(f"Model {model_name} is up to date.")

    # Coqui TTS setup
    print("Setting up Coqui TTS model...")
    tts = TTS("tts_models/en/vctk/vits", progress_bar=False)
    os.makedirs("assets/tmp", exist_ok=True)
    tts.tts_to_file(text="Test sentence for model download", 
                    file_path="assets/tmp/test_tts_output.wav", 
                    speaker="p225")

    # Whisper setup
    print("Setting up Whisper model...")
    whisper_model = whisper.load_model("base.en")

    # Sentence Transformer setup
    print("Setting up Sentence Transformer model...")
    sentence_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    print("All models have been set up successfully.")

if __name__ == "__main__":
    setup()
