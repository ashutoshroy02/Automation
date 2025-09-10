import os
import pickle
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import googleapiclient.http
from google.auth.transport.requests import Request
from tqdm import tqdm
from datetime import datetime, timedelta, timezone
import pathlib
import time
import json
from hashtag_generator import TrendingHashtagGenerator

# YouTube API scopes
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly"
]
TOKEN_FILE = 'token.pickle'
CLIENT_SECRETS_FILE = 'client_secrets.json'

def authenticate_youtube():
    """Authenticate with YouTube API with improved token handling"""
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    credentials = None
    
    # Check if token file exists and load saved credentials
    if os.path.exists(TOKEN_FILE):
        try:
            print("Loading saved credentials...")
            with open(TOKEN_FILE, 'rb') as token:
                credentials = pickle.load(token)
            print("✓ Credentials loaded from file")
        except Exception as e:
            print(f"Error loading saved credentials: {str(e)}")
            print("Removing corrupted token file...")
            try:
                os.remove(TOKEN_FILE)
            except:
                pass
            credentials = None

    # Check if credentials are valid or need refresh
    if credentials:
        if credentials.valid:
            print("✓ Using existing valid credentials")
            return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)
        elif credentials.expired and credentials.refresh_token:
            print("Credentials expired, attempting to refresh...")
            try:
                credentials.refresh(Request())
                print("✓ Credentials refreshed successfully")
                
                # Save refreshed credentials
                try:
                    with open(TOKEN_FILE, 'wb') as token:
                        pickle.dump(credentials, token)
                    print("✓ Refreshed credentials saved")
                except Exception as e:
                    print(f"Warning: Could not save refreshed credentials: {str(e)}")
                
                return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)
            except Exception as e:
                print(f"Error refreshing credentials: {str(e)}")
                print("Will need to re-authenticate...")
                # Remove invalid token file
                try:
                    os.remove(TOKEN_FILE)
                except:
                    pass
                credentials = None
        else:
            print("Credentials invalid and cannot be refreshed")
            credentials = None
    
    # If we reach here, we need fresh authentication
    print("Getting new credentials...")
    
    # Check if client secrets file exists
    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(f"Error: {CLIENT_SECRETS_FILE} not found!")
        print("Please download your OAuth 2.0 client credentials from Google Cloud Console")
        print("and save it as 'client_secrets.json' in the same directory as this script.")
        raise FileNotFoundError(f"{CLIENT_SECRETS_FILE} not found")
    
    # Verify client secrets file is valid JSON
    try:
        with open(CLIENT_SECRETS_FILE, 'r') as f:
            client_config = json.load(f)
        print("✓ Client secrets file is valid")
    except json.JSONDecodeError:
        print("Error: client_secrets.json is not valid JSON!")
        raise ValueError("Invalid client_secrets.json file")
    
    # Create the flow and run authentication
    try:
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, SCOPES)
        
        print("\n" + "="*50)
        print("OPENING BROWSER FOR AUTHENTICATION")
        print("="*50)
        print("1. A browser window will open")
        print("2. Sign in to your Google account")
        print("3. Grant permissions to the application")
        print("4. The authentication will complete automatically")
        print("="*50 + "\n")
        
        credentials = flow.run_local_server(
            port=0,
            open_browser=True,
            success_message='Authentication successful! You can close this window.'
        )
        
        print("✓ Authentication completed successfully!")
        
    except Exception as e:
        print(f"Error during authentication flow: {str(e)}")
        raise
    
    # Save the credentials for future use
    try:
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(credentials, token)
        print("✓ New credentials saved successfully")
        
        # Set file permissions to be more restrictive (Unix/Linux/Mac)
        try:
            os.chmod(TOKEN_FILE, 0o600)
        except:
            pass  # Windows doesn't support chmod
            
    except Exception as e:
        print(f"Warning: Could not save credentials: {str(e)}")
        print("You may need to re-authenticate next time")

    return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

def test_authentication(youtube):
    """Test if authentication is working by making a simple API call"""
    try:
        print("\nTesting authentication...")
        request = youtube.channels().list(part="snippet", mine=True)
        response = request.execute()
        
        if 'items' in response and len(response['items']) > 0:
            channel_name = response['items'][0]['snippet']['title']
            print(f"✓ Authentication test successful!")
            print(f"  Connected to channel: {channel_name}")
            return True
        else:
            print("✗ Authentication test failed - no channel found")
            return False
            
    except Exception as e:
        print(f"✗ Authentication test failed: {str(e)}")
        return False
        
# def hashtag(video_title):



#     return description, hashtags

def generate_basic_metadata(video_title):
    """Generate basic metadata for a video"""
    
    generator = TrendingHashtagGenerator()
    
    # Test with a sample title
    original_title = video_title
    
    # Generate viral title
    viral_title = generator.generate_viral_title(original_title)

    
    # Analyze category
    category = generator.analyze_title_for_category(original_title)

    
    # Generate hashtags
    tags = generator.generate_hashtags(original_title, category)


    description = generator.generate_description(viral_title, tags)
    
    return description, tags

def upload_video(youtube, video_path, publish_time=None):
    """Upload a video to YouTube"""
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        return None
    
    video_title = pathlib.Path(video_path).stem
    description, tags = generate_basic_metadata(video_title)
    
    request_body = {
        "snippet": {
            "categoryId": "22",
            "title": video_title,
            "description": description,
            "tags": tags[:10]
        },
        "status": {
            "privacyStatus": "private" if publish_time else "public",
            "selfDeclaredMadeForKids": False
        }
    }
    
    if publish_time:
        request_body["status"]["publishAt"] = publish_time

    file_size = os.path.getsize(video_path)
    
    media = googleapiclient.http.MediaFileUpload(
        video_path,
        chunksize=1024*1024,
        resumable=True,
        mimetype='video/mp4'
    )
    
    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    )

    response = None
    
    print(f"Starting upload: {video_title}")
    print(f"File size: {file_size / (1024*1024):.1f} MB")
    
    with tqdm(total=100, desc=f"Uploading", unit="%", ncols=80) as pbar:
        last_progress = 0
        retry_count = 0
        max_retries = 5
        
        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    current_progress = int(status.progress() * 100)
                    pbar.update(current_progress - last_progress)
                    last_progress = current_progress
                retry_count = 0
            except Exception as e:
                retry_count += 1
                if retry_count > max_retries:
                    print(f"\nFailed to upload after {max_retries} retries: {str(e)}")
                    return None
                
                print(f"\nUpload error (retry {retry_count}/{max_retries}): {str(e)}")
                time.sleep(2 ** retry_count)
                continue

    if response:
        video_id = response['id']
        
        if publish_time:
            print(f"✓ Video scheduled for: {publish_time}")
            print(f"  Video ID: {video_id}")
            print(f"  Title: {video_title}")
        else:
            print(f"✓ Video uploaded successfully!")
            print(f"  Video ID: {video_id}")
            print(f"  Title: {video_title}")
            print(f"  URL: https://www.youtube.com/watch?v={video_id}")
        
        return video_id
    else:
        print("✗ Upload failed - no response received")
        return None

def process_video_folder(youtube, folder_path, schedule_interval=None, start_time=None):
    """Process and upload all videos in a folder"""
    video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm')
    
    if not os.path.exists(folder_path):
        print(f"Error: Folder not found: {folder_path}")
        return
    
    video_files = [
        f for f in os.listdir(folder_path) 
        if os.path.isfile(os.path.join(folder_path, f)) 
        and f.lower().endswith(video_extensions)
    ]
    
    if not video_files:
        print("No video files found in the specified folder!")
        return
    
    video_files.sort()
    
    print(f"\n=== Upload Summary ===")
    print(f"Found {len(video_files)} videos to upload")
    print(f"Folder: {folder_path}")
    if schedule_interval:
        print(f"Schedule interval: {schedule_interval} hours")
    else:
        print("Upload mode: Immediate (public)")
    
    base_time = datetime.now(timezone.utc)
    if start_time:
        try:
            base_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            print(f"Custom start time: {base_time}")
        except ValueError:
            print("Invalid start time format. Using current time instead.")
            base_time = datetime.now(timezone.utc)
    
    print(f"Starting upload process...\n")
    
    successful_uploads = 0
    failed_uploads = 0
    
    for i, video_file in enumerate(video_files):
        video_path = os.path.join(folder_path, video_file)
        
        print(f"\n--- Video {i+1}/{len(video_files)} ---")
        
        publish_time = None
        if schedule_interval:
            scheduled_time = base_time + timedelta(hours=schedule_interval * i)
            publish_time = scheduled_time.isoformat().replace('+00:00', 'Z')
        
        try:
            video_id = upload_video(youtube, video_path, publish_time)
            if video_id:
                successful_uploads += 1
            else:
                failed_uploads += 1
                
            if i < len(video_files) - 1:
                time.sleep(2)
                
        except Exception as e:
            print(f"✗ Error uploading {video_file}: {str(e)}")
            failed_uploads += 1
            continue
    
    print(f"\n=== Upload Complete ===")
    print(f"Successfully uploaded: {successful_uploads}")
    print(f"Failed uploads: {failed_uploads}")
    print(f"Total processed: {len(video_files)}")

def clear_saved_credentials():
    """Clear saved credentials to force re-authentication"""
    if os.path.exists(TOKEN_FILE):
        try:
            os.remove(TOKEN_FILE)
            print("✓ Saved credentials cleared")
        except Exception as e:
            print(f"Error clearing credentials: {str(e)}")
    else:
        print("No saved credentials found")

if __name__ == "__main__":
    VIDEOS_FOLDER = "videos"
    
    try:
        print("=== YouTube Video Uploader ===")
        
        # Add option to clear credentials
        clear_creds = input("Clear saved credentials and re-authenticate? (y/n) [default: n]: ").lower() or "n"
        if clear_creds in ['y', 'yes']:
            clear_saved_credentials()
        
        # Check if videos folder exists
        if not os.path.exists(VIDEOS_FOLDER):
            print(f"Videos folder '{VIDEOS_FOLDER}' not found!")
            exit()
        
        # Authenticate
        print("\nAuthenticating with YouTube...")
        youtube = authenticate_youtube()
        
        # Test authentication
        if not test_authentication(youtube):
            print("Authentication test failed. Please check your setup.")
            exit()
        
        # Get scheduling preferences
        schedule_choice = input("\nDo you want to schedule uploads? (y/n) [default: n]: ").lower() or "n"
        
        if schedule_choice in ['y', 'yes']:
            interval = input("Hours between each upload [default: 6]: ").strip() or "4"
            try:
                interval = int(interval)
            except ValueError:
                print("Invalid interval. Using default value of 6 hours.")
                interval = 4

            custom_start = input("Enter custom start time (YYYY-MM-DDTHH:MM:SSZ) or press Enter for current time: ").strip()
            if not custom_start:
                custom_start = None
        else:
            interval = None
            custom_start = None
        
        # Process uploads
        process_video_folder(
            youtube=youtube, 
            folder_path=VIDEOS_FOLDER, 
            schedule_interval=interval,
            start_time=custom_start
        )
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        print("\nTroubleshooting steps:")
        print("1. Make sure you have a valid client_secrets.json file")
        print("2. Check that the YouTube Data API v3 is enabled in Google Cloud Console")
        print("3. Verify your OAuth 2.0 credentials are configured correctly")
        print("4. Try running with --clear-credentials flag")
        print("5. Install required packages: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client tqdm")
