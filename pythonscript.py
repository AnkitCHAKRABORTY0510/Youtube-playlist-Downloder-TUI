import yt_dlp
import os
from tqdm import tqdm

# Function to download videos from the playlist
def download_playlist(playlist_url, download_folder="./"):
    # Create a folder for downloads if it doesn't exist
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)
    
    # Set options for yt-dlp
    ydl_opts = {
        'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook],
        'noplaylist': False,
        'playlist_items': None,  # To download entire playlist
        'continuedl': True,  # Enable download resume
        'merge_output_format': 'mp4',  # Ensure audio/video merge as MP4
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }

    # Download the playlist using yt-dlp
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([playlist_url])

# Progress hook function
def progress_hook(d):
    if d['status'] == 'downloading':
        progress = d.get('downloaded_bytes', 0) / d.get('total_bytes', 1) * 100
        bar.update(progress - bar.n)
    if d['status'] == 'finished':
        bar.update(bar.total - bar.n)

if __name__ == "__main__":
    playlist_url = input("Enter the YouTube playlist URL: ")
    bar = tqdm(total=100, desc="Download Progress", ncols=100, position=0, leave=True)
    try:
        download_playlist(playlist_url)
        print("Download completed successfully!")
    except Exception as e:
        print(f"An error occurred: {e}")
