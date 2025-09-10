import os
import streamlit as st
from download import download_shorts
from upload import authenticate_youtube, process_video_folder
import time
from datetime import datetime, timedelta
import pytz

def main():
    st.set_page_config(page_title="Mitovoid Content Manager", page_icon="⚡")
    
    # Company branding
    st.markdown("# Mitovoid")
    st.markdown("---")

    # Main interface
    tab1, tab2, tab3 = st.tabs(["Content Acquisition", "Content Publishing", "Automated Pipeline"])

    output_folder = "videos"  # Keep consistent with both scripts

    with tab1:
        st.header("Content Acquisition")
        # Get user inputs for downloading
        channel_url = st.text_input("Enter YouTube channel URL:")
        sort_by = st.selectbox("Sort videos by:", ["views", "date"], index=0)
        limit = st.number_input("Number of videos to download:", min_value=1, max_value=100, value=50)
        if st.button("Start Download"):
            if not channel_url:
                st.error("Please enter a YouTube channel URL")
            else:
                with st.spinner("Downloading videos..."):
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    def update_progress(current, total, message):
                        progress = int((current / total) * 100)
                        progress_bar.progress(progress)
                        status_text.text(message)

                    success = download_shorts(
                        channel_url=channel_url,
                        output_folder=output_folder,
                        sort_by=sort_by,
                        limit=int(limit),
                        progress_callback=update_progress
                    )

                    progress_bar.empty()
                    status_text.empty()

                    if success:
                        st.success("Videos downloaded successfully!")
                    else:
                        st.error("Failed to download videos. Please check the URL and try again.")

    with tab2:
        st.header("Content Publishing")
        if not os.path.exists(output_folder) or not any(f.endswith((".mp4", ".mkv", ".avi")) for f in os.listdir(output_folder)):
            st.warning("No videos found in the videos folder. Please download some videos first.")
        else:
            st.write("Configure Upload Settings:")
            upload_interval = st.number_input("Hours between each upload:", min_value=1, max_value=24, value=6)
            use_custom_time = st.checkbox("Set custom start time")
            custom_start = None
            if use_custom_time:
                col1, col2 = st.columns(2)
                with col1:
                    custom_start_date = st.date_input("Select start date", min_value=datetime.now().date())
                with col2:
                    custom_start_time = st.time_input("Select start time")
                if custom_start_date and custom_start_time:
                    # Create datetime in local timezone (IST)
                    ist = pytz.timezone('Asia/Kolkata')
                    local_dt = datetime.combine(custom_start_date, custom_start_time)
                    local_dt = ist.localize(local_dt)
                    # Convert to UTC
                    utc_dt = local_dt.astimezone(pytz.UTC)
                    custom_start = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                    # Show the scheduled time in both IST and UTC
                    st.info(f"Scheduled time: {local_dt.strftime('%Y-%m-%d %I:%M %p')} IST ({utc_dt.strftime('%Y-%m-%d %I:%M %p')} UTC)")
            if st.button("Start Upload"):
                with st.spinner("Authenticating with YouTube..."):
                    try:
                        youtube = authenticate_youtube()
                        if youtube:
                            st.success("Authentication successful!")
                            with st.spinner("Uploading videos..."):
                                time.sleep(3)
                                process_video_folder(
                                    youtube=youtube,
                                    folder_path=output_folder,
                                    schedule_interval=upload_interval,
                                    start_time=custom_start
                                )
                                # Delete uploaded videos
                                for file in os.listdir(output_folder):
                                    if file.endswith(('.mp4', '.mkv', '.avi')):
                                        try:
                                            os.remove(os.path.join(output_folder, file))
                                        except Exception as e:
                                            st.warning(f"Could not delete {file}: {str(e)}")
                                st.success(f"Videos have been scheduled for upload with {upload_interval} hour intervals and cleared from the folder.")
                        else:
                            st.error("Authentication failed. Please check your credentials.")
                    except Exception as e:
                        st.error(f"Error during upload process: {str(e)}")

    with tab3:
        st.header("Download & Upload Pipeline")
        channel_url = st.text_input("Enter YouTube channel URL:", key="pipe_url")
        sort_by = st.selectbox("Sort videos by:", ["views", "date"], index=0, key="pipe_sort")
        limit = st.number_input("Number of videos to download:", min_value=1, max_value=100, value=50, key="pipe_limit")
        schedule = st.checkbox("Schedule uploads?", key="pipe_sched")
        interval = st.number_input("Hours between uploads:", min_value=1, max_value=24, value=4, key="pipe_interval") if schedule else None
        custom_start = None
        if schedule:
            col1, col2 = st.columns(2)
            with col1:
                custom_start_date = st.date_input("Select start date", min_value=datetime.now().date(), key="pipe_date")
            with col2:
                custom_start_time = st.time_input("Select start time", key="pipe_time")
            if custom_start_date and custom_start_time:
                # Create datetime in local timezone (IST)
                ist = pytz.timezone('Asia/Kolkata')
                local_dt = datetime.combine(custom_start_date, custom_start_time)
                local_dt = ist.localize(local_dt)
                # Convert to UTC
                utc_dt = local_dt.astimezone(pytz.UTC)
                custom_start = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                # Show the scheduled time in both IST and UTC
                st.info(f"Scheduled time: {local_dt.strftime('%Y-%m-%d %I:%M %p')} IST ({utc_dt.strftime('%Y-%m-%d %I:%M %p')} UTC)")
        if st.button("Start Download & Upload", key="pipe_btn"):
            with st.spinner("Downloading videos..."):
                try:
                    download_shorts(channel_url, output_folder=output_folder, sort_by=sort_by, limit=limit)
                    st.success("Download complete!")
                except Exception as e:
                    st.error(f"Download failed: {e}")
                    return
            with st.spinner("Authenticating and uploading videos..."):
                try:
                    youtube = authenticate_youtube()
                    video_files = [f for f in os.listdir(output_folder) if f.endswith(('.mp4', '.mkv', '.avi'))]
                    total_videos = len(video_files)
                    
                    if total_videos > 0:
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        for index, file in enumerate(video_files):
                            progress = int((index / total_videos) * 100)
                            status_text.text(f"Uploading: {file}")
                            progress_bar.progress(progress)
                            
                            # Process this video
                            process_video_folder(
                                youtube=youtube,
                                folder_path=output_folder,
                                schedule_interval=interval if schedule else None,
                                start_time=custom_start if schedule else None
                            )
                            
                            # Delete the uploaded video
                            try:
                                os.remove(os.path.join(output_folder, file))
                            except Exception as e:
                                st.warning(f"Could not delete {file}: {str(e)}")
                        
                        progress_bar.progress(100)
                        progress_bar.empty()
                        status_text.empty()
                        st.success("Upload complete! All videos have been processed and cleared from the folder.")
                except Exception as e:
                    st.error(f"Upload failed: {e}")
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")