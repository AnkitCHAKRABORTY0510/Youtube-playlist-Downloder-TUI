import tkinter as tk
from tkinter import ttk, messagebox
import yt_dlp
import os
from threading import Thread
from queue import Queue
import time
from datetime import timedelta
import concurrent.futures

class DownloadProgress:
    def __init__(self, video_id, progress_var, status_var, time_var, speed_var):
        self.video_id = video_id
        self.progress_var = progress_var
        self.status_var = status_var
        self.time_var = time_var
        self.speed_var = speed_var
        self.start_time = None
        self.paused = False
        self.total_bytes = 0
        self.downloaded_bytes = 0

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            if not self.start_time and 'total_bytes' in d:
                self.start_time = time.time()
                self.total_bytes = d['total_bytes']

            self.downloaded_bytes = d['downloaded_bytes']
            percentage = (self.downloaded_bytes / self.total_bytes * 100) if self.total_bytes else 0
            self.progress_var.set(percentage)
            
            elapsed_time = time.time() - self.start_time if self.start_time else 0
            speed = d.get('speed', 0)
            if speed:
                eta = (self.total_bytes - self.downloaded_bytes) / speed
                self.time_var.set(str(timedelta(seconds=int(eta))))
                self.speed_var.set(f"{speed/1024/1024:.1f} MB/s")

            self.status_var.set('Downloading...' if not self.paused else 'Paused')

        elif d['status'] == 'finished':
            self.progress_var.set(100)
            self.status_var.set('Complete')
            self.time_var.set('0:00:00')
            self.speed_var.set('0 MB/s')

class YoutubeDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        self.root.geometry("1000x800")
        
        # URL Input
        self.url_frame = ttk.LabelFrame(root, text="URL Input", padding=10)
        self.url_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(self.url_frame, text="YouTube URL:").pack(side="left")
        self.url_entry = ttk.Entry(self.url_frame, width=50)
        self.url_entry.pack(side="left", padx=5)
        
        # Subtitle Language
        self.sub_frame = ttk.LabelFrame(root, text="Subtitle Options", padding=10)
        self.sub_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(self.sub_frame, text="Subtitle Language Code:").pack(side="left")
        self.sub_entry = ttk.Entry(self.sub_frame, width=10)
        self.sub_entry.pack(side="left", padx=5)
        self.sub_entry.insert(0, "en")
        
        # Download Path
        self.path_frame = ttk.LabelFrame(root, text="Download Path", padding=10)
        self.path_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(self.path_frame, text="Save to:").pack(side="left")
        self.path_entry = ttk.Entry(self.path_frame, width=50)
        self.path_entry.pack(side="left", padx=5)
        self.path_entry.insert(0, "./")
        
        # Video List
        self.list_frame = ttk.LabelFrame(root, text="Videos", padding=10)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.video_canvas = tk.Canvas(self.list_frame)
        self.scrollbar = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.video_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.video_canvas)
        
        self.video_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.video_canvas.configure(scrollregion=self.video_canvas.bbox("all"))
        )
        
        self.video_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.video_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Control buttons
        self.button_frame = ttk.Frame(root)
        self.button_frame.pack(fill="x", padx=10, pady=5)
        
        self.fetch_btn = ttk.Button(self.button_frame, text="Fetch Video Info", command=self.fetch_info)
        self.fetch_btn.pack(side="left", padx=5)
        
        self.download_btn = ttk.Button(self.button_frame, text="Download All", command=self.start_download)
        self.download_btn.pack(side="left", padx=5)
        
        self.max_concurrent = tk.IntVar(value=3)
        ttk.Label(self.button_frame, text="Max Concurrent:").pack(side="left", padx=5)
        self.concurrent_spin = ttk.Spinbox(self.button_frame, from_=1, to=10, width=5, textvariable=self.max_concurrent)
        self.concurrent_spin.pack(side="left")
        
        # Status
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(root, textvariable=self.status_var)
        self.status_label.pack(pady=5)
        
        self.videos = []
        self.format_vars = []
        self.download_progress = {}
        self.download_threads = {}
        self.executor = None

    def clear_video_list(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.videos = []
        self.format_vars = []
        self.download_progress = {}

    def fetch_info(self):
        self.clear_video_list()
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL")
            return
        
        self.status_var.set("Fetching video information...")
        Thread(target=self._fetch_info_thread).start()

    def _fetch_info_thread(self):
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
                info = ydl.extract_info(self.url_entry.get(), download=False)
            
            self.root.after(0, self._update_video_list, info)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.status_var.set("Error fetching video information"))

    def _update_video_list(self, info):
        videos = info['entries'] if 'entries' in info else [info]
        
        for video in videos:
            if video.get('title') == '[Deleted video]':
                continue
            
            format_var = self._create_video_entry(video)
            self.format_vars.append(format_var)
            self.videos.append(video)
            
            Thread(target=self._fetch_formats, args=(video['id'], format_var)).start()
        
        self.status_var.set("Ready to download")

    def _fetch_formats(self, video_id, format_var):
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                formats = info.get('formats', [])
                
                format_options = []
                for fmt in formats:
                    if fmt.get('height'):
                        acodec = fmt.get('acodec', 'none')
                        vcodec = fmt.get('vcodec', 'none')
                        if vcodec != 'none':
                            size = fmt.get('filesize', 0)
                            size_str = f"{size/1024/1024:.1f}MB" if size else "N/A"
                            format_options.append(
                                f"{fmt['format_id']} | {fmt['height']}p | {fmt['ext']} | {size_str}"
                            )
                
                self.root.after(0, lambda: format_var.configure(values=format_options))
                if format_options:
                    self.root.after(0, lambda: format_var.set(format_options[-1]))
        
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Error fetching formats: {str(e)}"))

    def _create_video_entry(self, video):
        video_frame = ttk.Frame(self.scrollable_frame)
        video_frame.pack(fill="x", pady=2)
        
        # Title and format selection
        ttk.Label(video_frame, text=video['title'], width=40).pack(side="left", padx=5)
        
        format_var = tk.StringVar()
        format_combobox = ttk.Combobox(video_frame, textvariable=format_var, width=30)
        format_combobox.pack(side="left", padx=5)
        
        # Progress tracking
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(video_frame, length=200, variable=progress_var)
        progress_bar.pack(side="left", padx=5)
        
        status_var = tk.StringVar(value="Waiting...")
        status_label = ttk.Label(video_frame, textvariable=status_var, width=15)
        status_label.pack(side="left", padx=5)
        
        time_var = tk.StringVar(value="--:--:--")
        time_label = ttk.Label(video_frame, textvariable=time_var, width=10)
        time_label.pack(side="left", padx=5)
        
        speed_var = tk.StringVar(value="0 MB/s")
        speed_label = ttk.Label(video_frame, textvariable=speed_var, width=10)
        speed_label.pack(side="left", padx=5)
        
        pause_var = tk.BooleanVar(value=False)
        pause_btn = ttk.Button(video_frame, text="Pause",
                             command=lambda: self.toggle_pause(video['id'], pause_var))
        pause_btn.pack(side="left", padx=5)
        
        self.download_progress[video['id']] = DownloadProgress(
            video['id'], progress_var, status_var, time_var, speed_var
        )
        
        return format_var

    def toggle_pause(self, video_id, pause_var):
        if video_id in self.download_progress:
            progress = self.download_progress[video_id]
            progress.paused = not progress.paused
            if progress.paused:
                pause_var.set(True)
            else:
                pause_var.set(False)

    def start_download(self):
        download_path = self.path_entry.get().strip() or "./"
        if not os.path.exists(download_path):
            os.makedirs(download_path)
        
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_concurrent.get()
        )
        
        for video, format_var in zip(self.videos, self.format_vars):
            if not self.download_progress[video['id']].paused:
                self.executor.submit(self.download_video, video, format_var)

    def download_video(self, video, format_var):
        progress = self.download_progress[video['id']]
        format_str = format_var.get().split(" | ")[0]
        url = f"https://www.youtube.com/watch?v={video['id']}"
        
        ydl_opts = {
            'format': f"{format_str}+bestaudio/best",
            'outtmpl': os.path.join(self.path_entry.get(), '%(title)s.%(ext)s'),
            'writesubtitles': True,
            'subtitleslangs': [self.sub_entry.get()],
            'merge_output_format': 'mp4',
            'progress_hooks': [progress.progress_hook],
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Download error: {str(e)}"))
            progress.status_var.set("Failed")

if __name__ == "__main__":
    root = tk.Tk()
    app = YoutubeDownloaderGUI(root)
    root.mainloop()