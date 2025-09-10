import os
import yt_dlp
import re
from datetime import datetime

def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def is_single_video_url(url):
    """Check if the URL is a single video URL"""
    return 'watch?v=' in url or 'youtu.be/' in url

def download_single_video(video_url, output_folder="videos"):
    """
    Download a single YouTube video
    video_url: URL of the YouTube video
    output_folder: Folder to save the downloaded video
    """
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Configure yt-dlp options for single video
    ydl_opts = {
        'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_folder, '%(title).50s.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
        'merge_output_format': 'mp4',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info first
            video_info = ydl.extract_info(video_url, download=False)
            video_title = video_info.get('title', 'Unknown')
            duration = video_info.get('duration', 0)
            
            print(f"Video: {video_title}")
            print(f"Duration: {duration} seconds")
            
            # Ask user if they want to proceed
            proceed = input("Do you want to download this video? (y/n) [default: y]: ").lower() or "y"
            
            if proceed in ['y', 'yes']:
                print(f"Downloading: {video_title}")
                ydl.download([video_url])
                
                # Handle file renaming if needed
                original_filename = f"{video_title}.mp4"
                sanitized_filename = sanitize_filename(original_filename)
                
                if original_filename != sanitized_filename:
                    original_path = os.path.join(output_folder, original_filename)
                    new_path = os.path.join(output_folder, sanitized_filename)
                    if os.path.exists(original_path):
                        os.rename(original_path, new_path)
                        print(f"Renamed: {original_filename} -> {sanitized_filename}")
                
                print("Single video download completed successfully!")
                return True
            else:
                print("Download cancelled.")
                return False
                
    except Exception as e:
        print(f"Error downloading single video: {str(e)}")
        return False

def download_shorts(channel_url, output_folder="videos", sort_by="views", limit=5, progress_callback=None):
    """
    Download shorts from a YouTube channel
    channel_url: URL of the YouTube channel
    output_folder: Folder to save the downloaded videos
    sort_by: How to sort videos ('views' or 'date')
    limit: Maximum number of videos to download
    progress_callback: Optional callback function for progress updates
    """
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Build the URL for shorts
    if '/shorts' not in channel_url:
        if channel_url.endswith('/'):
            channel_url = channel_url + 'shorts'
        else:
            channel_url = channel_url + '/shorts'

    print(f"Downloading from: {channel_url}")

    # Configure yt-dlp options
    ydl_opts = {
        'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        # 'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
        'outtmpl': os.path.join(output_folder, '%(title).50s.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
        'extract_flat': False,
        'playlist_items': f'1:{limit}',  # Fixed syntax
        # '
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        'ignoreerrors': True,  # Continue on errors
        'writeinfojson': False,
        'writethumbnail': False,
    }

    # Add duration filter for shorts (typically under 60 seconds)
    if sort_by == 'views':
        ydl_opts['playlistsort'] = 'view_count'
        ydl_opts['playlistreverse'] = True
    else:
        ydl_opts['playlistsort'] = 'upload_date'
        ydl_opts['playlistreverse'] = True

    downloaded_count = 0
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Extracting video information from channel...")
            
            # Extract playlist info
            playlist_info = ydl.extract_info(channel_url, download=False)
            
            if not playlist_info or 'entries' not in playlist_info:
                print("No videos found or unable to extract playlist info")
                return False

            entries = list(playlist_info['entries'])[:limit]
            total_videos = len(entries)
            
            print(f"Found {total_videos} videos to process")
            
            if total_videos == 0:
                print("No videos found in the channel shorts")
                return False

            for i, entry in enumerate(entries, 1):
                if entry is None:
                    continue

                try:
                    video_url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
                    video_title = entry.get('title', 'Unknown Title')
                    duration = entry.get('duration', 0)
                    
                    print(f"\n[{i}/{total_videos}] Processing: {video_title}")
                    print(f"Duration: {duration} seconds")
                    
                    # Skip videos longer than 60 seconds (not typical shorts)
                    if duration and duration > 60:
                        print(f"Skipping (too long): {video_title}")
                        continue
                    
                    # Sanitize filename to check if it already exists
                    original_filename = f"{video_title}.mp4"
                    sanitized_filename = sanitize_filename(original_filename)
                    file_path = os.path.join(output_folder, sanitized_filename)

                    # Check if file already exists
                    if os.path.exists(file_path):
                        print(f"✓ Skipping download, file already exists: {sanitized_filename}")
                        continue

                    # Download the video
                    download_opts = ydl_opts.copy()
                    download_opts['extract_flat'] = False
                    if progress_callback:
                        progress_callback(i-1, total_videos, f"Downloading: {video_title}")
                    
                    with yt_dlp.YoutubeDL(download_opts) as download_ydl:
                        download_ydl.download([video_url])
                    
                    if progress_callback:
                        progress_callback(i, total_videos, f"Downloaded: {video_title}")
                    
                    # Handle file renaming if needed
                    original_filename = f"{video_title}.mp4"
                    sanitized_filename = sanitize_filename(original_filename)
                    
                    if original_filename != sanitized_filename:
                        original_path = os.path.join(output_folder, original_filename)
                        new_path = os.path.join(output_folder, sanitized_filename)
                        if os.path.exists(original_path):
                            os.rename(original_path, new_path)
                            print(f"Renamed file for compatibility")
                    
                    downloaded_count += 1
                    print(f"✓ Downloaded successfully")
                    
                except Exception as e:
                    error_msg = str(e)
                    if "Sign in to confirm your age" in error_msg:
                        print(f"⚠ Age-restricted content, skipping: {video_title}")
                    elif "Private video" in error_msg:
                        print(f"⚠ Private video, skipping: {video_title}")
                    elif "Video unavailable" in error_msg:
                        print(f"⚠ Video unavailable, skipping: {video_title}")
                    else:
                        print(f"⚠ Error downloading: {error_msg}")
                    continue

        print(f"\n=== Download Summary ===")
        print(f"Successfully downloaded: {downloaded_count} videos")
        print(f"Total processed: {total_videos}")
        print("Channel download completed!")
        
        return downloaded_count > 0
        
    except Exception as e:
        print(f"Error during download setup: {str(e)}")
        return False

if __name__ == "__main__":
    print("YouTube Video Downloader")
    print("=" * 50)
    
    # Ask user what they want to download
    download_type = input("What do you want to download?\n1. Single video\n2. Channel videos (shorts)\nEnter choice (1/2): ").strip()
    
    if download_type == "1":
        # Single video download
        print("\n--- Single Video Download ---")
        video_url = input("Enter YouTube video URL: ").strip()
        
        if not video_url:
            print("No URL provided. Exiting.")
            exit()
        
        if not is_single_video_url(video_url):
            print("Invalid video URL format. Please provide a valid YouTube video URL.")
            exit()
        
        output_folder = input("Enter output folder [default: videos]: ").strip() or "videos"
        download_single_video(video_url, output_folder)
        
    elif download_type == "2":
        # Channel download
        print("\n--- Channel Videos Download ---")
        channel_url = input("Enter YouTube channel URL: ").strip()
        
        if not channel_url:
            print("No URL provided. Exiting.")
            exit()
        
        output_folder = input("Enter output folder [default: videos]: ").strip() or "videos"
        sort_by = input("Sort by views or date? (views/date) [default: views]: ").lower() or "views"
        limit = input("How many videos to download? [default: 50]: ") or "50"
        
        try:
            limit = int(limit)
        except ValueError:
            print("Invalid limit. Using default value of 50.")
            limit = 50
        
        download_shorts(channel_url, output_folder, sort_by, limit)
        
    else:
        print("Invalid choice. Please run the script again and select 1 or 2.")
