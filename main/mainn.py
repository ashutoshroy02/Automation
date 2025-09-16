import os
import streamlit as st
from download import download_shorts
from upload import authenticate_youtube, process_video_folder
import time
from datetime import datetime, timedelta
import pytz
import json
import jwt
import requests
import streamlit.components.v1 as components
import hashlib
import hmac

def init_session_state():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    if 'id_token' not in st.session_state:
        st.session_state.id_token = None
    if 'youtube_api_key' not in st.session_state:
        st.session_state.youtube_api_key = ""
    if 'google_client_configured' not in st.session_state:
        st.session_state.google_client_configured = False
    if 'google_client_id' not in st.session_state:
        st.session_state.google_client_id = ""

def create_google_signin_component(client_id):
    """Create Google Sign-In component with proper communication"""
    signin_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <script src="https://accounts.google.com/gsi/client" async defer></script>
        <style>
            body {{
                font-family: Arial, sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 200px;
                margin: 0;
                padding: 20px;
                background-color: #f8f9fa;
            }}
            .signin-container {{
                text-align: center;
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 400px;
                width: 100%;
            }}
            .user-info {{
                margin-top: 20px;
                padding: 15px;
                background: #e8f5e8;
                border-radius: 8px;
                border: 1px solid #28a745;
            }}
            .user-avatar {{
                width: 60px;
                height: 60px;
                border-radius: 50%;
                margin: 10px auto;
                display: block;
            }}
            .signout-btn {{
                background: #dc3545;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                cursor: pointer;
                margin-top: 10px;
            }}
            .signout-btn:hover {{
                background: #c82333;
            }}
            .error {{
                color: #dc3545;
                margin-top: 10px;
                padding: 10px;
                background: #f8d7da;
                border-radius: 4px;
                border: 1px solid #f5c6cb;
            }}
        </style>
    </head>
    <body>
        <div class="signin-container">
            <h3>🔐 Sign in with Google</h3>
            <div id="signin-button"></div>
            <div id="user-info" style="display: none;" class="user-info">
                <h4>✅ Signed In Successfully!</h4>
                <img id="user-picture" class="user-avatar" alt="Profile">
                <p><strong id="user-name"></strong></p>
                <p id="user-email" style="color: #666;"></p>
                <button class="signout-btn" onclick="signOut()">Sign Out</button>
            </div>
            <div id="error-message" style="display: none;" class="error"></div>
        </div>

        <script>
            let currentUser = null;

            function initializeGSI() {{
                try {{
                    google.accounts.id.initialize({{
                        client_id: '{client_id}',
                        callback: handleCredentialResponse,
                        auto_select: false,
                        cancel_on_tap_outside: false
                    }});

                    google.accounts.id.renderButton(
                        document.getElementById('signin-button'),
                        {{
                            theme: 'outline',
                            size: 'large',
                            text: 'signin_with',
                            shape: 'rectangular',
                            logo_alignment: 'left'
                        }}
                    );
                }} catch (error) {{
                    showError('Failed to initialize Google Sign-In: ' + error.message);
                }}
            }}

            function handleCredentialResponse(response) {{
                try {{
                    // Decode the JWT token
                    const token = response.credential;
                    const payload = JSON.parse(atob(token.split('.')[1]));
                    
                    // Verify the token is for our client
                    if (payload.aud !== '{client_id}') {{
                        showError('Invalid token audience');
                        return;}}

                    // Display user info
                    currentUser = payload;
                    document.getElementById('signin-button').style.display = 'none';
                    document.getElementById('user-info').style.display = 'block';
                    document.getElementById('user-name').textContent = payload.name;
                    document.getElementById('user-email').textContent = payload.email;
                    document.getElementById('user-picture').src = payload.picture;
                    
                    // Send data to Streamlit parent
                    const userData = {{
                        name: payload.name,
                        email: payload.email,
                        picture: payload.picture,
                        sub: payload.sub,
                        id_token: token
                    }};

                    // Use postMessage to communicate with Streamlit
                    if (window.parent && window.parent !== window) {{
                        window.parent.postMessage({{
                            type: 'GOOGLE_LOGIN_SUCCESS',
                            data: userData
                        }}, '*');
                    }}

                    // Also try to set a global variable that Streamlit can access
                    window.streamlit_google_user = userData;
                    
                    // Trigger a custom event
                    window.dispatchEvent(new CustomEvent('googleLogin', {{ detail: userData }}));

                }} catch (error) {{
                    showError('Error processing sign-in: ' + error.message);
                }}
            }}

            function signOut() {{
                try {{
                    google.accounts.id.disableAutoSelect();
                    
                    // Clear UI
                    document.getElementById('user-info').style.display = 'none';
                    document.getElementById('signin-button').style.display = 'block';
                    currentUser = null;
                    
                    // Notify Streamlit
                    if (window.parent && window.parent !== window) {{
                        window.parent.postMessage({{
                            type: 'GOOGLE_LOGOUT'
                        }}, '*');
                    }}
                    
                    window.streamlit_google_user = null;
                    window.dispatchEvent(new CustomEvent('googleLogout'));
                    
                }} catch (error) {{
                    showError('Error signing out: ' + error.message);
                }}
            }}

            function showError(message) {{
                const errorDiv = document.getElementById('error-message');
                errorDiv.textContent = message;
                errorDiv.style.display = 'block';
                
                // Hide error after 5 seconds
                setTimeout(() => {{
                    errorDiv.style.display = 'none';
                }}, 5000);
            }}

            // Initialize when the page loads
            window.addEventListener('load', function() {{
                if (typeof google !== 'undefined' && google.accounts) {{
                    initializeGSI();
                }} else {{
                    // Retry initialization after a short delay
                    setTimeout(initializeGSI, 500);
                }}
            }});

            // Listen for messages from parent (Streamlit)
            window.addEventListener('message', function(event) {{
                if (event.data.type === 'REQUEST_USER_DATA' && currentUser) {{
                    event.source.postMessage({{
                        type: 'GOOGLE_LOGIN_SUCCESS',
                        data: window.streamlit_google_user
                    }}, event.origin);
                }}
            }});
        </script>
    </body>
    </html>
    """
    return signin_html

def setup_page():
    """Setup page for Google Client ID and YouTube API Key"""
    st.markdown("# 🔧 Mitovoid Setup")
    st.markdown("---")
    
    st.markdown("### Initial Configuration Required")
    st.info("Before using the application, please configure your Google credentials and YouTube API key.")
    
    # Instructions
    with st.expander("📋 Setup Instructions", expanded=True):
        st.markdown("""
        ### How to get your Google Client ID:
        
        1. **Go to Google Cloud Console**: https://console.cloud.google.com/
        2. **Create or select a project**
        3. **Enable APIs**:
           - Go to "APIs & Services" > "Library"
           - Enable "Google+ API" or "Google Identity"
           - Enable "YouTube Data API v3"
        4. **Create OAuth 2.0 Credentials**:
           - Go to "APIs & Services" > "Credentials"
           - Click "Create Credentials" > "OAuth 2.0 Client IDs"
           - Application type: "Web application"
           - Add authorized JavaScript origins: `http://localhost:8501`
           - Add authorized redirect URIs: `http://localhost:8501`
        5. **Get API Key**:
           - In "Credentials", click "Create Credentials" > "API Key"
           - Restrict to "YouTube Data API v3" (recommended)
        """)
    
    # Google Client ID
    st.markdown("#### Step 1: Google OAuth2 Client ID")
    google_client_id = st.text_input(
        "Google OAuth2 Client ID:",
        help="From Google Cloud Console > Credentials (ends with .apps.googleusercontent.com)",
        placeholder="123456789-abc...xyz.apps.googleusercontent.com"
    )
    
    # YouTube API Key
    st.markdown("#### Step 2: YouTube Data API v3 Key")
    youtube_api_key = st.text_input(
        "YouTube Data API v3 Key:",
        type="password",
        help="API Key for YouTube operations"
    )
    
    # Save configuration
    if st.button("💾 Save Configuration", type="primary"):
        if google_client_id and youtube_api_key:
            # Validate Client ID format
            if not google_client_id.endswith('.apps.googleusercontent.com'):
                st.error("❌ Invalid Client ID format. It should end with '.apps.googleusercontent.com'")
                return
            
            # Store in session state
            st.session_state.google_client_id = google_client_id
            st.session_state.youtube_api_key = youtube_api_key
            st.session_state.google_client_configured = True
            
            # Save to file for persistence
            config = {
                "google_client_id": google_client_id,
                "youtube_api_key": youtube_api_key
            }
            
            try:
                with open("config.json", "w") as f:
                    json.dump(config, f, indent=2)
                st.success("✅ Configuration saved successfully!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error saving configuration: {str(e)}")
        else:
            st.error("❌ Please fill in all required fields.")
    
    # Load existing configuration
    if os.path.exists("config.json"):
        if st.button("🔄 Load Saved Configuration"):
            try:
                with open("config.json", "r") as f:
                    config = json.load(f)
                
                if config.get("google_client_id") and config.get("youtube_api_key"):
                    st.session_state.google_client_id = config["google_client_id"]
                    st.session_state.youtube_api_key = config["youtube_api_key"]
                    st.session_state.google_client_configured = True
                    st.success("✅ Configuration loaded successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Invalid configuration file.")
            except Exception as e:
                st.error(f"❌ Error loading configuration: {str(e)}")

def login_page():
    """Login page with Google Sign-In"""
    st.markdown("# 🔐 Mitovoid Login")
    st.markdown("---")
    
    client_id = st.session_state.get('google_client_id', '')
    
    if not client_id:
        st.error("❌ Google Client ID not configured.")
        if st.button("⚙️ Go to Setup"):
            st.session_state.google_client_configured = False
            st.rerun()
        return
    
    st.markdown("### Sign in with your Google Account")
    st.info(f"Using Client ID: {client_id[:20]}...")
    
    # Create the Google Sign-In component
    signin_html = create_google_signin_component(client_id)
    
    # Display the component
    components.html(signin_html, height=350, scrolling=False)
    
    # Check for authentication via URL parameters (callback handling)
    query_params = st.query_params
    if 'token' in query_params:
        try:
            token = query_params['token']
            # Basic JWT decode (without verification for demo)
            payload = jwt.decode(token, options={"verify_signature": False})
            
            if payload.get('aud') == client_id:
                st.session_state.authenticated = True
                st.session_state.user_info = {
                    'name': payload.get('name'),
                    'email': payload.get('email'),
                    'picture': payload.get('picture'),
                    'sub': payload.get('sub')
                }
                st.session_state.id_token = token
                st.success("✅ Login successful!")
                # Clear query params
                st.query_params.clear()
                time.sleep(1)
                st.rerun()
        except Exception as e:
            st.error(f"❌ Token validation failed: {str(e)}")
    
    # Manual token input as fallback
    st.markdown("---")
    st.markdown("### Alternative: Manual Token Input")
    with st.expander("Use this if the button above doesn't work"):
        st.markdown("""
        1. Go to https://accounts.google.com and sign in
        2. Open browser developer tools (F12)
        3. Look for ID token in network requests
        4. Copy and paste it below
        """)
        
        manual_token = st.text_area("Google ID Token:", height=100)
        
        if manual_token and st.button("Verify Token"):
            try:
                # Decode without verification (for demo purposes)
                payload = jwt.decode(manual_token, options={"verify_signature": False})
                
                if payload.get('aud') == client_id:
                    st.session_state.authenticated = True
                    st.session_state.user_info = {
                        'name': payload.get('name'),
                        'email': payload.get('email'),
                        'picture': payload.get('picture'),
                        'sub': payload.get('sub')
                    }
                    st.session_state.id_token = manual_token
                    st.success("✅ Manual login successful!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Token not valid for this application")
            except Exception as e:
                st.error(f"❌ Invalid token: {str(e)}")
    
    # Development bypass
    st.markdown("---")
    st.markdown("### 🔧 Development Mode")
    with st.expander("Bypass authentication for testing"):
        demo_name = st.text_input("Your Name:", value="Demo User")
        demo_email = st.text_input("Your Email:", value="demo@example.com")
        
        if st.button("Login (Development Mode)", type="secondary"):
            st.session_state.authenticated = True
            st.session_state.user_info = {
                'name': demo_name,
                'email': demo_email,
                'picture': 'https://via.placeholder.com/60x60/007bff/ffffff?text=DU',
                'sub': 'dev_user_123'
            }
            st.success("✅ Development login successful!")
            time.sleep(1)
            st.rerun()

def logout():
    """Handle user logout"""
    st.session_state.authenticated = False
    st.session_state.user_info = None
    st.session_state.id_token = None
    st.success("✅ Logged out successfully!")
    time.sleep(0.5)
    st.rerun()

def main_app():
    """Main application after authentication"""
    # Header with user info and logout
    header_col1, header_col2, header_col3, header_col4 = st.columns([4, 1, 1, 1])
    
    with header_col1:
        st.markdown("# ⚡ Mitovoid Content Manager")
        if st.session_state.user_info:
            st.markdown(f"Welcome back, **{st.session_state.user_info.get('name', 'User')}**! 👋")
    
    with header_col2:
        if st.session_state.user_info and st.session_state.user_info.get('picture'):
            st.image(st.session_state.user_info['picture'], width=50, caption="")
    
    with header_col3:
        st.write(f"**{st.session_state.user_info.get('email', 'No email')[:15]}...**" if len(st.session_state.user_info.get('email', '')) > 15 else f"**{st.session_state.user_info.get('email', 'No email')}**")
    
    with header_col4:
        if st.button("🚪 Logout", type="secondary"):
            logout()
    
    st.markdown("---")
    
    # Configuration status
    status_col1, status_col2 = st.columns(2)
    with status_col1:
        if st.session_state.authenticated:
            st.success("✅ User Authentication: Active")
        else:
            st.error("❌ User Authentication: Inactive")
    
    with status_col2:
        if st.session_state.youtube_api_key:
            st.success("✅ YouTube API: Configured")
        else:
            st.error("❌ YouTube API: Not configured")
            api_key_input = st.text_input("Enter YouTube API Key:", type="password", key="quick_api_key")
            if api_key_input and st.button("Save", key="save_quick_api"):
                st.session_state.youtube_api_key = api_key_input
                # Update config file
                try:
                    config = {}
                    if os.path.exists("config.json"):
                        with open("config.json", "r") as f:
                            config = json.load(f)
                    config["youtube_api_key"] = api_key_input
                    with open("config.json", "w") as f:
                        json.dump(config, f, indent=2)
                    st.success("✅ API Key saved!")
                    st.rerun()
                except Exception as e:
                    st.warning(f"Saved to session but couldn't update config file: {e}")
            return  # Don't show main content until API key is configured
    
    # Main content tabs
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📥 Content Acquisition", "📤 Content Publishing", "🔄 Automated Pipeline"])

    output_folder = "videos"

    with tab1:
        st.header("📥 Content Acquisition")
        
        channel_url = st.text_input("📺 Enter YouTube channel URL:")
        
        col1, col2 = st.columns(2)
        with col1:
            sort_by = st.selectbox("📊 Sort videos by:", ["views", "date"], index=0)
        with col2:
            limit = st.number_input("🔢 Number of videos to download:", min_value=1, max_value=100, value=50)
        
        if st.button("🚀 Start Download", type="primary"):
            if not channel_url:
                st.error("❌ Please enter a YouTube channel URL")
                return
            
            with st.spinner("📥 Downloading videos..."):
                progress_bar = st.progress(0)
                status_text = st.empty()

                def update_progress(current, total, message):
                    if total > 0:
                        progress = int((current / total) * 100)
                        progress_bar.progress(progress)
                    status_text.text(f"📥 {message}")

                try:
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
                        st.success("✅ Videos downloaded successfully!")
                        if os.path.exists(output_folder):
                            video_count = len([f for f in os.listdir(output_folder) if f.endswith(('.mp4', '.mkv', '.avi'))])
                            st.info(f"📁 {video_count} videos ready in the {output_folder} folder")
                    else:
                        st.error("❌ Failed to download videos. Please check the URL and try again.")
                except Exception as e:
                    st.error(f"❌ Download error: {str(e)}")
                    progress_bar.empty()
                    status_text.empty()

    with tab2:
        st.header("📤 Content Publishing")
        
        # Check for videos
        video_files = []
        if os.path.exists(output_folder):
            video_files = [f for f in os.listdir(output_folder) if f.endswith(('.mp4', '.mkv', '.avi'))]
        
        if not video_files:
            st.warning("⚠️ No videos found in the videos folder. Please download some videos first.")
            st.info("💡 Use the 'Content Acquisition' tab to download videos from YouTube channels.")
        else:
            st.success(f"📁 Found {len(video_files)} videos ready for upload")
            
            # Upload settings
            st.markdown("### ⚙️ Upload Configuration")
            
            col1, col2 = st.columns(2)
            with col1:
                upload_interval = st.number_input("⏱️ Hours between uploads:", min_value=1, max_value=48, value=6)
            with col2:
                use_custom_time = st.checkbox("🕐 Set custom start time")
            
            custom_start = None
            if use_custom_time:
                date_col, time_col = st.columns(2)
                with date_col:
                    custom_start_date = st.date_input("📅 Start date:", min_value=datetime.now().date())
                with time_col:
                    custom_start_time = st.time_input("🕐 Start time:")
                
                if custom_start_date and custom_start_time:
                    ist = pytz.timezone('Asia/Kolkata')
                    local_dt = datetime.combine(custom_start_date, custom_start_time)
                    local_dt = ist.localize(local_dt)
                    utc_dt = local_dt.astimezone(pytz.UTC)
                    custom_start = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                    
                    st.info(f"🕐 **Scheduled start time:**\n"
                           f"📍 IST: {local_dt.strftime('%Y-%m-%d %I:%M %p')}\n"
                           f"🌍 UTC: {utc_dt.strftime('%Y-%m-%d %I:%M %p')}")
            
            if st.button("🚀 Start Upload Process", type="primary"):
                with st.spinner("🔐 Authenticating with YouTube..."):
                    try:
                        os.environ['YOUTUBE_API_KEY'] = st.session_state.youtube_api_key
                        youtube = authenticate_youtube()
                        
                        if youtube:
                            st.success("✅ YouTube authentication successful!")
                            
                            with st.spinner("📤 Processing video uploads..."):
                                process_video_folder(
                                    youtube=youtube,
                                    folder_path=output_folder,
                                    schedule_interval=upload_interval,
                                    start_time=custom_start
                                )
                                
                                # Clean up uploaded videos
                                cleanup_count = 0
                                for file in video_files:
                                    try:
                                        os.remove(os.path.join(output_folder, file))
                                        cleanup_count += 1
                                    except Exception as e:
                                        st.warning(f"⚠️ Could not delete {file}: {str(e)}")
                                
                                st.success(f"✅ Upload process complete!\n"
                                          f"📤 Videos scheduled with {upload_interval}h intervals\n"
                                          f"🗑️ {cleanup_count} files cleaned up")
                        else:
                            st.error("❌ YouTube authentication failed. Please check your API key.")
                    except Exception as e:
                        st.error(f"❌ Upload process failed: {str(e)}")

    with tab3:
        st.header("🔄 Automated Download & Upload Pipeline")
        st.markdown("*Complete workflow: Download → Upload → Schedule → Cleanup*")
        
        # Pipeline settings
        st.markdown("### 📥 Download Settings")
        pipe_col1, pipe_col2 = st.columns(2)
        
        with pipe_col1:
            channel_url = st.text_input("📺 YouTube Channel URL:", key="pipe_url")
            sort_by = st.selectbox("📊 Sort by:", ["views", "date"], index=0, key="pipe_sort")
        
        with pipe_col2:
            limit = st.number_input("🔢 Videos to download:", min_value=1, max_value=100, value=50, key="pipe_limit")
            schedule = st.checkbox("⏱️ Schedule uploads", key="pipe_sched")
        
        # Upload scheduling
        if schedule:
            st.markdown("### 📤 Upload Scheduling")
            sched_col1, sched_col2 = st.columns(2)
            
            with sched_col1:
                interval = st.number_input("⏱️ Hours between uploads:", min_value=1, max_value=48, value=4, key="pipe_interval")
            
            with sched_col2:
                use_custom_start = st.checkbox("🕐 Custom start time", key="pipe_custom")
            
            custom_start = None
            if use_custom_start:
                date_col, time_col = st.columns(2)
                with date_col:
                    custom_start_date = st.date_input("📅 Start date:", min_value=datetime.now().date(), key="pipe_date")
                with time_col:
                    custom_start_time = st.time_input("🕐 Start time:", key="pipe_time")
                
                if custom_start_date and custom_start_time:
                    ist = pytz.timezone('Asia/Kolkata')
                    local_dt = datetime.combine(custom_start_date, custom_start_time)
                    local_dt = ist.localize(local_dt)
                    utc_dt = local_dt.astimezone(pytz.UTC)
                    custom_start = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                    st.info(f"🕐 Pipeline will start: {local_dt.strftime('%Y-%m-%d %I:%M %p')} IST")
        
        # Start pipeline
        if st.button("🚀 Start Complete Pipeline", key="pipe_btn", type="primary"):
            if not channel_url:
                st.error("❌ Please enter a YouTube channel URL")
                return
            
            pipeline_container = st.container()
            
            with pipeline_container:
                # Phase 1: Download
                st.markdown("### 📥 Phase 1: Downloading Content")
                with st.spinner("📥 Downloading videos from channel..."):
                    try:
                        download_shorts(
                            channel_url=channel_url, 
                            output_folder=output_folder, 
                            sort_by=sort_by, 
                            limit=limit
                        )
                        st.success("✅ Download phase completed successfully!")
                        
                        # Count downloaded videos
                        downloaded_videos = [f for f in os.listdir(output_folder) if f.endswith(('.mp4', '.mkv', '.avi'))]
                        st.info(f"📁 Downloaded {len(downloaded_videos)} videos")
                        
                    except Exception as e:
                        st.error(f"❌ Download phase failed: {e}")
                        return
                
                # Phase 2: Upload
                st.markdown("### 📤 Phase 2: Processing Uploads")
                with st.spinner("📤 Setting up YouTube uploads..."):
                    try:
                        os.environ['YOUTUBE_API_KEY'] = st.session_state.youtube_api_key
                        youtube = authenticate_youtube()
                        
                        if not youtube:
                            st.error("❌ YouTube authentication failed")
                            return
                        
                        st.success("✅ YouTube authentication successful")
                        
                        # Process uploads
                        video_files = [f for f in os.listdir(output_folder) if f.endswith(('.mp4', '.mkv', '.avi'))]
                        total_videos = len(video_files)
                        
                        if total_videos == 0:
                            st.warning("⚠️ No videos found to upload")
                            return
                        
                        # Upload progress
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        process_video_folder(
                            youtube=youtube,
                            folder_path=output_folder,
                            schedule_interval=interval if schedule else None,
                            start_time=custom_start if schedule else None
                        )
                        
                        # Phase 3: Cleanup
                        st.markdown("### 🗑️ Phase 3: Cleanup")
                        cleanup_count = 0
                        for file in video_files:
                            try:
                                os.remove(os.path.join(output_folder, file))
                                cleanup_count += 1
                            except Exception as e:
                                                                st.warning(f"⚠️ Could not delete {file}: {str(e)}")
                        st.success(f"✅ Cleanup completed! {cleanup_count} files removed.")
                        
                        st.balloons()
                        st.info("🎉 Pipeline process finished successfully!")
                    
                    except Exception as e:
                        st.error(f"❌ Upload phase failed: {str(e)}")

def main():
    """Main entry point of the app"""
    st.set_page_config(page_title="Mitovoid Content Manager", layout="wide", initial_sidebar_state="expanded")
    
    init_session_state()
    
    if not st.session_state.google_client_configured:
        setup_page()
    else:
        if not st.session_state.authenticated:
            login_page()
        else:
            main_app()

if __name__ == "__main__":
    main()
