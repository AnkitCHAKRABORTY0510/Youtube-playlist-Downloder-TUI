import yt_dlp  # Library for downloading YouTube videos and playlists.
import os  # Provides functions to interact with the operating system.
import time  # Used for adding delays
import humanize  # To humanize the file size

# Function to extract video or playlist info with retries
def extract_info_with_retries(ydl, url, retries=3, delay=5):
    """
    Extracts video or playlist information with retries.
    :param ydl: yt-dlp instance.
    :param url: Video or playlist URL.
    :param retries: Number of retries.
    :param delay: Delay between retries (in seconds).
    :return: Extracted info dictionary.
    """
    for attempt in range(retries):
        try:
            print(f"Attempting to extract info (try {attempt + 1}/{retries})...")
            info = ydl.extract_info(url, download=False)  # Attempt to extract info.
            return info  # Return extracted info if successful.
        except yt_dlp.utils.DownloadError as e:
            print(f"Error extracting info: {e}")
            if attempt < retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)  # Wait before retrying.
            else:
                print("Failed to extract info after multiple attempts.")
                raise  # Re-raise the exception if all retries fail.

# Function to download a video with specific format, add audio if missing, and download subtitles
def download_video_with_audio_and_subtitles(video_url, format_id, subtitle_lang, download_folder="./"):
    # Extract video and formats info
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        info = ydl.extract_info(video_url, download=False)  # Extract video info
        formats = info.get('formats', [])

        # Locate the selected video format
        video_format = next((fmt for fmt in formats if fmt['format_id'] == format_id), None)
        audio_format = next((fmt for fmt in formats if fmt.get('acodec', 'none') != 'none'), None)

        if not video_format:
            print("Invalid video format selected. Skipping download.")
            return

        if video_format.get('acodec', 'none') == 'none':  # If video has no audio
            if audio_format:
                format_str = f"{video_format['format_id']}+{audio_format['format_id']}"
            else:
                print("No audio format available to merge with the video. Skipping download.")
                return
        else:
            format_str = format_id  # Video already includes audio

    # Set options for yt-dlp
    ydl_opts = {
        'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),  # File naming format with folder path.
        'format': format_str,  # Specify the format string to download.
        'continuedl': True,  # Resume interrupted downloads.
        'merge_output_format': 'mp4',  # Ensure audio/video streams merge into an MP4 file.
        'postprocessors': [{
            'key': 'FFmpegEmbedSubtitle',  # Embed subtitles into the video.
        }],
        'writesubtitles': True,  # Download subtitles if available.
        'subtitleslangs': [subtitle_lang],  # Subtitle language preference.
        'subtitlesformat': 'srt',  # Subtitle format.
        'addmetadata': True,  # Add metadata to the output file.
    }

    # Download the video with audio and subtitles (if available)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])  # Start downloading the video.

# Function to list available formats and allow user selection
def select_format(video_url):
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:  # Initialize yt-dlp in quiet mode.
        info_dict = ydl.extract_info(video_url, download=False)  # Extract video information without downloading.
        formats = info_dict.get('formats', [])  # Get available formats.

        print("\nAvailable Formats:")
        for i, fmt in enumerate(formats):
            # Display format ID, resolution, audio codec, file extension, and size (if available)
            size = fmt.get('filesize')  # Get file size if available
            human_size = humanize.naturalsize(size) if size else "N/A"
            print(f"{i + 1}. ID: {fmt['format_id']} | Resolution: {fmt.get('height', 'Audio')}p | "
                  f"Audio: {fmt.get('acodec', 'none')} | Ext: {fmt['ext']} | Size: {human_size}")

        # Prompt the user to choose a format
        while True:
            try:
                choice = int(input("\nEnter the number corresponding to your desired format: ")) - 1
                return formats[choice]['format_id']  # Return the selected format ID.
            except (ValueError, IndexError):
                print("Invalid selection. Please try again.")

if __name__ == "__main__":
    playlist_url = input("Enter the YouTube playlist URL: ")  # Prompt the user to enter the playlist URL.
    subtitle_lang = input("Enter the subtitle language code (e.g., 'en' for English, leave blank for none): ").strip() or 'en'

    # Extract playlist or video info with retries
    with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True, 'quiet': False}) as ydl:
        try:
            info = extract_info_with_retries(ydl, playlist_url)
        except Exception as e:
            print(f"Unable to process the URL: {e}")
            exit(1)

    # Check if the URL is a playlist or a single video
    if 'entries' in info:  # Playlist
        videos = info['entries']
        playlist_name = info.get('title', 'Untitled Playlist')  # Get playlist name or fallback to 'Untitled Playlist'
        print(f"Found {len(videos)} videos in the playlist: {playlist_name}")
    else:  # Single video
        videos = [info]
        playlist_name = info.get('title', 'Untitled Video')  # Get video name or fallback to 'Untitled Video'
        print(f"Single video URL provided: {playlist_name}")

    custom_folder = input("Enter the download folder path (leave blank for default './'): ").strip()  # Prompt for custom folder.

    # Use the playlist name (or video name) as folder name or prompt user if not provided
    download_folder = custom_folder if custom_folder else playlist_name
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    # Process each video
    for video in videos:
        print(f"\nProcessing video: {video['title']}")
        # Check if 'webpage_url' exists, otherwise use 'url' or construct the URL from 'id'
        video_url = video.get('webpage_url', video.get('url', f"https://youtube.com/watch?v={video.get('id')}"))
        if not video_url:
            print(f"Skipping video: {video['title']} - Missing URL.")
            continue

        format_id = select_format(video_url)  # Let the user select a format for each video
        try:
            print(f"Downloading {video['title']}...")
            download_video_with_audio_and_subtitles(video_url, format_id, subtitle_lang, download_folder)  # Download video
            print(f"Download completed: {video['title']}")
        except Exception as e:
            print(f"An error occurred while downloading {video['title']}: {e}")

    print(f"\nAll downloads completed. Files saved in: {os.path.abspath(download_folder)}")
