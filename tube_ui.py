import os
import re
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from urllib.parse import urlparse, parse_qs
import yt_dlp
import shutil
import subprocess
import platform
import requests
import zipfile
from tkinter import font as tkfont
import sv_ttk
import json


class FFmpegManager:
    def __init__(self):
        self.ffmpeg_path = None
        self.ffmpeg_dir = os.path.join(os.path.dirname(__file__), 'ffmpeg')
    
    def check_ffmpeg(self):
        if shutil.which('ffmpeg'):
            self.ffmpeg_path = 'ffmpeg'
            return True
        
        system = platform.system().lower()
        if system == 'windows':
            local_ffmpeg = os.path.join(self.ffmpeg_dir, 'ffmpeg.exe')
        else:
            local_ffmpeg = os.path.join(self.ffmpeg_dir, 'ffmpeg')
        
        if os.path.exists(local_ffmpeg):
            self.ffmpeg_path = local_ffmpeg
            return True
        
        return False
    
    def install_ffmpeg(self):
        try:
            system = platform.system().lower()
            
            if system == 'windows':
                return self._install_ffmpeg_windows()
            elif system == 'darwin':
                return self._install_ffmpeg_mac()
            else:
                return self._install_ffmpeg_linux()
        except Exception as e:
            return False, f"Failed to install FFmpeg: {str(e)}"
    
    def _install_ffmpeg_windows(self):
        try:
            os.makedirs(self.ffmpeg_dir, exist_ok=True)
            
            ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
            
            try:
                response = requests.get(ffmpeg_url, stream=True, timeout=30)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                return False, f"Failed to download FFmpeg: {str(e)}"
            
            zip_path = os.path.join(self.ffmpeg_dir, 'ffmpeg.zip')
            try:
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            except Exception as e:
                return False, f"Failed to save FFmpeg download: {str(e)}"
            
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(self.ffmpeg_dir)
            except Exception as e:
                return False, f"Failed to extract FFmpeg: {str(e)}"
            
            extracted_dir = None
            for item in os.listdir(self.ffmpeg_dir):
                if item.startswith('ffmpeg-master') and os.path.isdir(os.path.join(self.ffmpeg_dir, item)):
                    extracted_dir = os.path.join(self.ffmpeg_dir, item)
                    break
            
            if extracted_dir:
                bin_dir = os.path.join(extracted_dir, 'bin')
                ffmpeg_exe = os.path.join(bin_dir, 'ffmpeg.exe')
                if os.path.exists(ffmpeg_exe):
                    shutil.move(ffmpeg_exe, os.path.join(self.ffmpeg_dir, 'ffmpeg.exe'))
                    shutil.rmtree(extracted_dir)
                    os.remove(zip_path)
            
            ffmpeg_path = os.path.join(self.ffmpeg_dir, 'ffmpeg.exe')
            if os.path.exists(ffmpeg_path):
                self.ffmpeg_path = ffmpeg_path
                return True, "FFmpeg installed successfully"
            
            return False, "FFmpeg installation failed"
            
        except Exception as e:
            return False, f"Windows FFmpeg installation failed: {str(e)}"
    
    def _install_ffmpeg_mac(self):
        try:
            if not shutil.which('brew'):
                return False, "Homebrew not found. Please install Homebrew first."
            
            result = subprocess.run(['brew', 'install', 'ffmpeg'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                self.ffmpeg_path = 'ffmpeg'
                return True, "FFmpeg installed successfully via Homebrew"
            else:
                return False, f"Homebrew installation failed: {result.stderr}"
                
        except Exception as e:
            return False, f"macOS FFmpeg installation failed: {str(e)}"
    
    def _install_ffmpeg_linux(self):
        try:
            if shutil.which('apt-get'):
                result = subprocess.run(['sudo', 'apt-get', 'update', '&&', 'sudo', 'apt-get', 'install', '-y', 'ffmpeg'], 
                                      shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    self.ffmpeg_path = 'ffmpeg'
                    return True, "FFmpeg installed successfully via apt-get"
            
            elif shutil.which('yum'):
                result = subprocess.run(['sudo', 'yum', 'install', '-y', 'ffmpeg'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    self.ffmpeg_path = 'ffmpeg'
                    return True, "FFmpeg installed successfully via yum"
            
            return False, "Could not install FFmpeg automatically. Please install it manually."
            
        except Exception as e:
            return False, f"Linux FFmpeg installation failed: {str(e)}"


class TubeUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Tube UI")
        self.root.geometry("800x750")
        self.root.resizable(True, True)
        self.root.minsize(700, 600)
        self.root.iconbitmap(default='')
        
        self.settings_file = os.path.join(os.path.dirname(__file__), 'settings.json')
        self.load_settings()
        
        # Set initial theme
        initial_theme = self.settings.get('theme', 'light')
        self.theme_mode = initial_theme
        sv_ttk.set_theme(initial_theme)
        self.update_window_titlebar_color(initial_theme)
        
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        self.download_path = os.path.expanduser("~/Downloads")
        self.is_downloading = False
        self.ffmpeg_manager = FFmpegManager()
        
        self.setup_ui()
        self.check_ffmpeg_availability()
        
        # Apply title bar color after window is fully shown
        self.root.after(100, lambda: self.update_window_titlebar_color(self.theme_mode))
    
    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    self.settings = json.load(f)
                    self.theme_mode = self.settings.get('theme', 'light')
            else:
                self.settings = {'theme': 'light'}
                self.theme_mode = 'light'
        except:
            self.settings = {'theme': 'light'}
            self.theme_mode = 'light'
    
    def save_settings(self):
        try:
            settings = {'theme': self.theme_mode}
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f)
        except:
            pass
    
    def update_window_titlebar_color(self, theme):
        try:
            import ctypes
            from ctypes import wintypes
            
            # Windows API constants
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            DWMWA_CAPTION_COLOR = 35
            
            # Ensure window is fully created
            self.root.update()
            
            # Get window handle
            hwnd = self.root.winfo_id()
            
            if hwnd:  # Only proceed if we have a valid window handle
                dwmapi = ctypes.windll.dwmapi
                
                # Set immersive dark mode for title bar
                use_dark_mode = 1 if theme == 'dark' else 0
                dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_USE_IMMERSIVE_DARK_MODE,
                    ctypes.byref(ctypes.c_int(use_dark_mode)),
                    ctypes.sizeof(ctypes.c_int)
                )
                
                # Also try to set caption color
                if theme == 'dark':
                    caption_color = 0x202020  # Dark gray
                else:
                    caption_color = 0xFFFFFF  # White
                
                dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_CAPTION_COLOR,
                    ctypes.byref(ctypes.c_int(caption_color)),
                    ctypes.sizeof(ctypes.c_int)
                )
        except Exception as e:
            # If it fails, continue without title bar color change
            pass
    
    def toggle_theme(self):
        if self.theme_mode == 'light':
            self.theme_mode = 'dark'
            sv_ttk.set_theme('dark')
            self.update_window_titlebar_color('dark')
        else:
            self.theme_mode = 'light'
            sv_ttk.set_theme('light')
            self.update_window_titlebar_color('light')
        
        self.save_settings()
        
        # Force immediate update of title bar color
        self.root.after(50, lambda: self.update_window_titlebar_color(self.theme_mode))
    
    def setup_ui(self):
        main_container = ttk.Frame(self.root, padding="40")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        
        header_frame = ttk.Frame(main_container)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 40))
        header_frame.columnconfigure(0, weight=0)
        header_frame.columnconfigure(1, weight=1)
        
        theme_button = ttk.Button(header_frame, text="🌙", command=self.toggle_theme, width=3)
        theme_button.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        title_label = ttk.Label(header_frame, text="Tube UI", font=('Segoe UI', 24, 'bold'))
        title_label.grid(row=0, column=1, sticky=tk.W)
        
        url_frame = ttk.Frame(main_container, padding="20")
        url_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        url_frame.columnconfigure(0, weight=1)
        
        url_label = ttk.Label(url_frame, text="Video URL", font=('Segoe UI', 11))
        url_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        self.url_entry = ttk.Entry(url_frame, font=('Segoe UI', 11))
        self.url_entry.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        options_frame = ttk.Frame(main_container, padding="20")
        options_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        options_frame.columnconfigure(1, weight=1)
        
        format_label = ttk.Label(options_frame, text="Format", font=('Segoe UI', 11))
        format_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        format_frame = ttk.Frame(options_frame)
        format_frame.grid(row=0, column=1, sticky=tk.W, pady=(0, 10), padx=(40, 0))
        
        self.format_var = tk.StringVar(value="mp4")
        mp4_radio = ttk.Radiobutton(format_frame, text="MP4 Video", variable=self.format_var, value="mp4",
                                   command=self.on_format_change)
        mp4_radio.pack(side=tk.LEFT, padx=(0, 20))
        mp3_radio = ttk.Radiobutton(format_frame, text="MP3 Audio", variable=self.format_var, value="mp3",
                                   command=self.on_format_change)
        mp3_radio.pack(side=tk.LEFT)
        
        self.quality_label = ttk.Label(options_frame, text="Quality", font=('Segoe UI', 11))
        self.quality_label.grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        
        self.quality_frame = ttk.Frame(options_frame)
        self.quality_frame.grid(row=1, column=1, sticky=tk.W, pady=(10, 0), padx=(40, 0))
        
        self.quality_var = tk.StringVar(value="1080p")
        self.quality_combo = ttk.Combobox(self.quality_frame, textvariable=self.quality_var, 
                                        values=["4K", "1440p", "1080p", "720p", "480p", "360p"], 
                                        state="readonly", width=18)
        self.quality_combo.pack(side=tk.LEFT)
        
        path_frame = ttk.Frame(main_container, padding="20")
        path_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        path_frame.columnconfigure(0, weight=1)
        
        path_label = ttk.Label(path_frame, text="Download Location", font=('Segoe UI', 11))
        path_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        path_input_frame = ttk.Frame(path_frame)
        path_input_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        path_input_frame.columnconfigure(0, weight=1)
        
        self.path_entry = ttk.Entry(path_input_frame, font=('Segoe UI', 10))
        self.path_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 16))
        self.path_entry.insert(0, self.download_path)
        
        browse_button = ttk.Button(path_input_frame, text="Browse", command=self.browse_path)
        browse_button.grid(row=0, column=1)
        
        progress_frame = ttk.Frame(main_container, padding="20")
        progress_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        progress_frame.columnconfigure(0, weight=1)
        
        progress_label = ttk.Label(progress_frame, text="Download Progress", font=('Segoe UI', 11))
        progress_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        self.status_label = ttk.Label(main_container, text="Ready to download", font=('Segoe UI', 9))
        self.status_label.grid(row=6, column=0, pady=(20, 30))
        
        button_frame = ttk.Frame(main_container)
        button_frame.grid(row=7, column=0)
        
        self.download_button = ttk.Button(button_frame, text="Download", command=self.start_download)
        self.download_button.pack(side=tk.LEFT, padx=(0, 16))
        
        self.clear_button = ttk.Button(button_frame, text="Clear", command=self.clear_fields)
        self.clear_button.pack(side=tk.LEFT, padx=(0, 16))
        
        self.install_ffmpeg_button = ttk.Button(button_frame, text="Install FFmpeg", command=self.install_ffmpeg_manual)
        self.install_ffmpeg_button.pack(side=tk.LEFT, padx=(0, 16))
        
        self.credits_button = ttk.Button(button_frame, text="Credits", command=self.show_credits)
        self.credits_button.pack(side=tk.LEFT)
    
    def show_credits(self):
        credits_text = """Tube UI

Made by Samuel

Software Used:
• yt-dlp - Video/audio downloading
• FFmpeg - Video/audio processing and conversion
• Tkinter - GUI framework
• sv-ttk - Sun Valley theme for modern UI
• Python - Programming language

Special thanks to:
• yt-dlp developers for the amazing download library
• FFmpeg team for media processing tools
• rdbende for the beautiful Sun Valley theme
• Python Software Foundation

Version: 1.0
Created: 2025"""
        
        credits_window = tk.Toplevel(self.root)
        credits_window.title("Credits")
        credits_window.geometry("400x350")
        credits_window.resizable(False, False)
        
        credits_window.update_idletasks()
        x = (credits_window.winfo_screenwidth() // 2) - (credits_window.winfo_width() // 2)
        y = (credits_window.winfo_screenheight() // 2) - (credits_window.winfo_height() // 2)
        credits_window.geometry(f"+{x}+{y}")
        
        text_frame = ttk.Frame(credits_window, padding="20")
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=('Segoe UI', 10), 
                             bg='#faf9f8', fg='#323130', relief=tk.FLAT, padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        text_widget.insert(tk.END, credits_text)
        text_widget.config(state=tk.DISABLED)
        
        close_button = ttk.Button(text_frame, text="Close", command=credits_window.destroy)
        close_button.pack(pady=(10, 0))
    
    def on_format_change(self):
        format_type = self.format_var.get()
        if format_type == "mp3":
            self.quality_label.grid_remove()
            self.quality_frame.grid_remove()
        else:
            self.quality_label.grid()
            self.quality_frame.grid()
    
    def check_ffmpeg_availability(self):
        if not self.ffmpeg_manager.check_ffmpeg():
            self.status_label.config(text="FFmpeg not found. Will install automatically when needed.", foreground="orange")
        else:
            self.status_label.config(text="FFmpeg available. Ready to download.", foreground="green")
        
    def browse_path(self):
        folder = filedialog.askdirectory(initialdir=self.download_path)
        if folder:
            self.download_path = folder
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, folder)
    
    def validate_url(self, url):
        video_regex = re.compile(
            r'(https?://)?(www\.)?(youtube\.com/(watch\?v=|embed/|v/)|youtu\.be/|youtube\.com/playlist\?list=)[\w-]+'
        )
        return bool(video_regex.match(url))
    
    def get_video_info(self, url):
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            raise Exception(f"Failed to get video info: {str(e)}")
    
    def download_progress_hook(self, d):
        if d['status'] == 'downloading':
            if 'total_bytes' in d and d['total_bytes'] > 0:
                percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                self.progress_var.set(percent)
                self.root.update_idletasks()
        elif d['status'] == 'finished':
            self.progress_var.set(100)
            self.root.update_idletasks()
    
    def download_video(self, url, output_path, format_type, quality):
        try:
            if not self.ffmpeg_manager.check_ffmpeg():
                self.status_label.config(text="FFmpeg not found. Please install FFmpeg manually or try again.", foreground="red")
                return False, "FFmpeg required but not available. Please install FFmpeg manually."
            
            info = self.get_video_info(url)
            title = info.get('title', 'video')
            safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
            
            ffmpeg_location = None
            if self.ffmpeg_manager.ffmpeg_path and self.ffmpeg_manager.ffmpeg_path != 'ffmpeg':
                ffmpeg_location = os.path.dirname(self.ffmpeg_manager.ffmpeg_path)
            
            if format_type == "mp3":
                # Download best audio only for MP3
                ydl_opts = {
                    'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio[ext=ogg]/bestaudio',
                    'outtmpl': os.path.join(output_path, f'{safe_title}_audio.%(ext)s'),
                    'progress_hooks': [self.download_progress_hook],
                    'noplaylist': True,
                }
            else:
                # For MP4, prioritize AAC audio and avoid OPUS completely
                if quality == "4K":
                    format_selector = 'bestvideo[height<=2160][fps<=60]+bestaudio[acodec=mp3]/bestvideo[height<=2160][fps<=60]+bestaudio[acodec=mp3]/bestvideo[height<=2160][fps<=60]+bestaudio[acodec=mp3]/bestvideo[height<=2160][fps<=60]+bestaudio'
                elif quality == "1440p":
                    format_selector = 'bestvideo[height<=1440][fps<=60]+bestaudio[acodec=mp3]/bestvideo[height<=1440][fps<=60]+bestaudio[acodec=mp3]/bestvideo[height<=1440][fps<=60]+bestaudio[acodec=mp3]/bestvideo[height<=1440][fps<=60]+bestaudio'
                elif quality == "1080p":
                    format_selector = 'bestvideo[height<=1080][fps<=60]+bestaudio[acodec=mp3]/bestvideo[height<=1080][fps<=60]+bestaudio[acodec=mp3]/bestvideo[height<=1080][fps<=60]+bestaudio[acodec=mp3]/bestvideo[height<=1080][fps<=60]+bestaudio'
                elif quality == "720p":
                    format_selector = 'bestvideo[height<=720][fps<=60]+bestaudio[acodec=mp3]/bestvideo[height<=720][fps<=60]+bestaudio[acodec=mp3]/bestvideo[height<=720][fps<=60]+bestaudio[acodec=mp3]/bestvideo[height<=720][fps<=60]+bestaudio'
                elif quality == "480p":
                    format_selector = 'bestvideo[height<=480]+bestaudio[acodec=mp3]/bestvideo[height<=480]+bestaudio[acodec=mp3]/bestvideo[height<=480]+bestaudio[acodec=mp3]/bestvideo[height<=480]+bestaudio'
                else:  # 360p
                    format_selector = 'bestvideo[height<=360]+bestaudio[acodec=mp3]/bestvideo[height<=360]+bestaudio[acodec=mp3]/bestvideo[height<=360]+bestaudio[acodec=mp3]/bestvideo[height<=360]+bestaudio'
                
                ydl_opts = {
                    'format': format_selector,
                    'outtmpl': os.path.join(output_path, f'{safe_title}.%(ext)s'),
                    'progress_hooks': [self.download_progress_hook],
                    'noplaylist': True,
                    'merge_output_format': 'mp4',
                    'postprocessors': [],
                }
            
            if ffmpeg_location:
                ydl_opts['ffmpeg_location'] = ffmpeg_location
            
            ydl_opts.update({
                'socket_timeout': 60,
                'retries': 3,
                'fragment_retries': 3,
                'skip_unavailable_fragments': True,
                'keep_fragments': False,
                'no_check_certificates': True,
                'extract_flat': False,
                'prefer_ffmpeg': True,
                'prefer_free_formats': False,
                'hls_prefer_native': False,
                'noplaylist': True,
                'extract_flat': False,
                'restrict_filenames': True,
                'format_sort_force': True,
            })
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if format_type == "mp3":
                # Convert downloaded audio to MP3
                try:
                    audio_file = None
                    for ext in ['.m4a', '.webm', '.ogg', '.opus', '.mp3']:
                        potential_file = os.path.join(output_path, f'{safe_title}_audio{ext}')
                        if os.path.exists(potential_file):
                            audio_file = potential_file
                            break
                    
                    if audio_file:
                        mp3_file = os.path.join(output_path, f'{safe_title}.mp3')
                        
                        # Convert audio to MP3 with better OPUS handling
                        cmd = [
                            self.ffmpeg_manager.ffmpeg_path,
                            '-i', audio_file,
                            '-vn',  # No video
                            '-acodec', 'mp3',
                            '-ab', '192k',
                            '-ar', '44100',
                            '-ac', '2',  # Stereo
                            '-avoid_negative_ts', 'make_zero',  # Fix timestamp issues
                            '-y',
                            mp3_file
                        ]
                        
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                        
                        if result.returncode == 0:
                            # Remove original audio file
                            os.remove(audio_file)
                            
                            return True, f"Successfully downloaded and converted: {title}.mp3"
                        else:
                            # If conversion fails, try alternative method
                            alt_cmd = [
                                self.ffmpeg_manager.ffmpeg_path,
                                '-i', audio_file,
                                '-f', 'mp3',
                                '-ab', '192k',
                                '-ar', '44100',
                                '-y',
                                mp3_file
                            ]
                            
                            alt_result = subprocess.run(alt_cmd, capture_output=True, text=True, timeout=300)
                            
                            if alt_result.returncode == 0:
                                os.remove(audio_file)
                                return True, f"Successfully downloaded and converted: {title}.mp3"
                            else:
                                return False, f"Audio conversion failed: {result.stderr}\nAlternative also failed: {alt_result.stderr}"
                    else:
                        return False, "Could not find downloaded audio file"
                        
                except Exception as e:
                    return False, f"Audio processing failed: {str(e)}"
            
            # For MP4, convert OPUS to AAC if needed for Windows compatibility
            if format_type == "mp4":
                try:
                    downloaded_file = None
                    for ext in ['.mp4', '.webm', '.mkv']:
                        potential_file = os.path.join(output_path, f'{safe_title}{ext}')
                        if os.path.exists(potential_file):
                            downloaded_file = potential_file
                            break
                    
                    if downloaded_file:
                        # Always convert audio to AAC for Windows compatibility
                        temp_file = os.path.join(output_path, f'{safe_title}_temp.mp4')
                        
                        cmd = [
                            self.ffmpeg_manager.ffmpeg_path,
                            '-i', downloaded_file,
                            '-c:v', 'copy',  # Copy video without re-encoding
                            '-c:a', 'aac',    # Convert audio to AAC
                            '-b:a', '192k',   # Good audio quality
                            '-ar', '44100',   # Standard sample rate
                            '-y',
                            temp_file
                        ]
                        
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                        
                        if result.returncode == 0:
                            # Replace original file with converted one
                            os.remove(downloaded_file)
                            os.rename(temp_file, downloaded_file)
                        else:
                            # Clean up temp file if conversion failed
                            if os.path.exists(temp_file):
                                os.remove(temp_file)
                except Exception as e:
                    pass  # Don't fail the download if audio conversion fails
            
            return True, f"Successfully downloaded: {title}"
            
        except Exception as e:
            return False, f"Download failed: {str(e)}"
    
    def start_download(self):
        if self.is_downloading:
            messagebox.showwarning("Warning", "Download in progress. Please wait.")
            return
        
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a video URL")
            return
        
        if not self.validate_url(url):
            messagebox.showerror("Error", "Invalid video URL")
            return
        
        output_path = self.path_entry.get().strip()
        if not os.path.exists(output_path):
            messagebox.showerror("Error", "Download path does not exist")
            return
        
        format_type = self.format_var.get()
        quality = self.quality_var.get() if format_type == "mp4" else None
        
        self.is_downloading = True
        self.download_button.config(state='disabled')
        self.status_label.config(text="Downloading...", foreground="blue")
        self.progress_var.set(0)
        
        thread = threading.Thread(target=self.download_worker, 
                                args=(url, output_path, format_type, quality))
        thread.daemon = True
        thread.start()
    
    def download_worker(self, url, output_path, format_type, quality):
        try:
            success, message = self.download_video(url, output_path, format_type, quality)
            
            self.root.after(0, self.download_complete, success, message)
            
        except Exception as e:
            self.root.after(0, self.download_complete, False, f"Error: {str(e)}")
    
    def download_complete(self, success, message):
        self.is_downloading = False
        self.download_button.config(state='normal')
        
        if success:
            self.status_label.config(text=message, foreground="green")
            messagebox.showinfo("Success", message)
        else:
            self.status_label.config(text=message, foreground="red")
            messagebox.showerror("Error", message)
    
    def install_ffmpeg_manual(self):
        self.status_label.config(text="Installing FFmpeg...", foreground="blue")
        self.install_ffmpeg_button.config(state='disabled')
        
        def install_worker():
            try:
                success, message = self.ffmpeg_manager.install_ffmpeg()
                self.root.after(0, self.ffmpeg_install_complete, success, message)
            except Exception as e:
                self.root.after(0, self.ffmpeg_install_complete, False, str(e))
        
        thread = threading.Thread(target=install_worker)
        thread.daemon = True
        thread.start()
    
    def ffmpeg_install_complete(self, success, message):
        self.install_ffmpeg_button.config(state='normal')
        if success:
            self.status_label.config(text="FFmpeg installed successfully!", foreground="green")
            messagebox.showinfo("Success", message)
        else:
            self.status_label.config(text="FFmpeg installation failed", foreground="red")
            messagebox.showerror("Error", message)
    
    def clear_fields(self):
        self.url_entry.delete(0, tk.END)
        self.progress_var.set(0)
        self.check_ffmpeg_availability()


def main():
    root = tk.Tk()
    app = TubeUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
