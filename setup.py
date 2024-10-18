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
    # Define your file URLs and their corresponding local paths
    files_to_download = {
        'https://example.com/file1.zip': 'downloads/file1.zip',
        'https://example.com/file2.zip': 'downloads/file2.zip',
    }

    # Create the downloads directory if it doesn't exist
    os.makedirs('downloads', exist_ok=True)

    # Download files
    for url, filename in files_to_download.items():
        print(f"Downloading {filename}...")
        download_file(url, filename)

    # Extract files
    for filename in files_to_download.values():
        if filename.endswith('.zip'):
            print(f"Extracting {filename}...")
            extract_to = os.path.splitext(filename)[0]  # Remove .zip extension
            os.makedirs(extract_to, exist_ok=True)
            extract_zip(filename, extract_to)

if __name__ == "__main__":
    setup()

