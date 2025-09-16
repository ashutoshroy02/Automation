import os
import streamlit as st
from download import download_shorts
from upload import authenticate_youtube, process_video_folder
import time
from datetime import datetime, timedelta
import pytz
import json

def init_session_state():
    """Initialize session state variables"""
    if 'youtube_api_key' not in st.session_state:
        st.session_state.youtube_api_key = ""

def setup_page():
    """Setup page to enter YouTube API Key"""
    st.title("⚙️ Mitovoid Setup")
    st.markdown("Please enter your **YouTube Data API v3 Key** from Google Cloud Console.")
    
    youtube_api_key = st.text_input(
        "YouTube API Key:",
        type="password",
        help="Get it from Google Cloud Console > APIs & Services > Credentials > API Key"
    )
    
    if st.button("💾 Save API Key", type="primary"):
        if youtube_api_key.strip():
            st.session_state.youtube_api_key = youtube_api_key.strip()
            config = {"youtube_api_key": youtube_api_key.strip()}
            with open("config.json", "w") as f:
                json.dump(config, f, indent=2)
            st.success("✅ API Key saved successfully!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ Please enter a valid API key.")
    
    if os.path.exists("config.json"):
        if st.button("🔄 Load Saved API Key"):
            try:
                with open("config.json", "r") as f:
                    config = json.load(f)
                    st.session_state.youtube_api_key = config.get("youtube_api_key", "")
                    st.success("✅ Loaded API key!")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to load config: {str(e)}")

def main_app():
    """Main content after entering API key"""
    st.title("⚡ Mitovoid Content Manager")
    
    st.info("✅ Using YouTube API Key for all operations")
    
    output_folder = "videos"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Tabs for Download and Upload
    tab1, tab2 = st.tabs(["📥 Download Videos", "📤 Upload Videos"])
    
    with tab1:
        st.header("📥 Download YouTube Shorts or Videos")
        
        channel_url = st.text_input("📺 Enter YouTube Channel URL:")
        
        sort_by = st.selectbox("Sort by:", ["views", "date"])
        limit = st.number_input("Number of videos:", min_value=1, max_value=100, value=10)
        
        if st.button("🚀 Download Videos"):
            if not channel_url.strip():
                st.error("❌ Please enter a valid channel URL")
            else:
                with st.spinner("📥 Downloading..."):
                    def update_progress(current, total, message):
                        st.progress(int((current / total) * 100))
                        st.text(message)

                    success = download_shorts(
                        channel_url=channel_url,
                        output_folder=output_folder,
                        sort_by=sort_by,
                        limit=limit,
                        progress_callback=update_progress
                    )
                    
                    if success:
                        st.success("✅ Videos downloaded successfully!")
                        files = [f for f in os.listdir(output_folder) if f.endswith(('.mp4', '.mkv', '.avi'))]
                        st.info(f"📂 {len(files)} videos available in `{output_folder}` folder.")
                    else:
                        st.error("❌ Download failed.")

    with tab2:
        st.header("📤 Upload Videos to YouTube")
        
        files = [f for f in os.listdir(output_folder) if f.endswith(('.mp4', '.mkv', '.avi'))]
        
        if not files:
            st.warning("⚠️ No videos found to upload. Please download some first.")
        else:
            st.info(f"📂 {len(files)} videos found for upload.")
            
            interval = st.number_input("Upload interval (hours):", min_value=1, max_value=24, value=4)
            use_custom = st.checkbox("Set custom start time")
            
            custom_start = None
            if use_custom:
                date = st.date_input("Start Date", min_value=datetime.now().date())
                time_ = st.time_input("Start Time")
                
                if date and time_:
                    ist = pytz.timezone('Asia/Kolkata')
                    local_dt = datetime.combine(date, time_)
                    local_dt = ist.localize(local_dt)
                    utc_dt = local_dt.astimezone(pytz.UTC)
                    custom_start = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                    st.info(f"Start at: {local_dt.strftime('%Y-%m-%d %I:%M %p')} IST / {utc_dt.strftime('%Y-%m-%d %I:%M %p')} UTC")

            if st.button("🚀 Start Upload"):
                with st.spinner("🔐 Authenticating with YouTube..."):
                    try:
                        os.environ['YOUTUBE_API_KEY'] = st.session_state.youtube_api_key
                        youtube = authenticate_youtube()
                        
                        if youtube:
                            st.success("✅ Authentication successful!")
                            
                            with st.spinner("📤 Uploading videos..."):
                                process_video_folder(
                                    youtube=youtube,
                                    folder_path=output_folder,
                                    schedule_interval=interval,
                                    start_time=custom_start
                                )
                                st.success("✅ Upload process completed!")
                                
                                # Cleanup
                                cleanup_count = 0
                                for file in files:
                                    try:
                                        os.remove(os.path.join(output_folder, file))
                                        cleanup_count += 1
                                    except Exception as e:
                                        st.warning(f"⚠️ Could not delete {file}: {str(e)}")
                                st.success(f"🗑️ Cleanup completed! {cleanup_count} files removed.")
                        else:
                            st.error("❌ Authentication failed.")
                    except Exception as e:
                        st.error(f"❌ Upload process failed: {str(e)}")

def main():
    st.set_page_config(page_title="Mitovoid", layout="wide")
    init_session_state()
    
    if not st.session_state.youtube_api_key:
        setup_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
