import os
import requests
import zipfile
from tqdm import tqdm

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
    # Define the Vosk model URL and its corresponding local path
    vosk_model_url = 'https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip'
    vosk_model_filename = './models/vosk-model-en-us-0.22.zip'

    # Create the models directory if it doesn't exist
    os.makedirs('./models', exist_ok=True)

    # Download the Vosk model
    print(f"Downloading Vosk model...")
    download_file(vosk_model_url, vosk_model_filename)

    # Extract the Vosk model
    print(f"Extracting Vosk model...")
    extract_zip(vosk_model_filename, './models')

    # Optionally, remove the zip file after extraction
    os.remove(vosk_model_filename)
    print("Vosk model setup complete.")

if __name__ == "__main__":
    setup()
