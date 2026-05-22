import os
import tempfile
import shutil
import streamlit as st
import yt_dlp
import threading
import time




# Set Page Config
st.set_page_config(
    page_title="yt-dlp Premium GUI",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 1. Custom CSS Theme & Styling Injection ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    font-family: 'Outfit', sans-serif !important;
    background-color: #0b0f19 !important;
    color: #f9fafb !important;
}

/* Glassmorphism Sidebar */
[data-testid="stSidebar"] {
    background-color: rgba(17, 24, 39, 0.95) !important;
    border-right: 1px solid rgba(168, 85, 247, 0.25) !important;
}

/* Sidebar labels and inputs */
[data-testid="stSidebar"] .stMarkdown h1, 
[data-testid="stSidebar"] .stMarkdown h2, 
[data-testid="stSidebar"] .stMarkdown h3 {
    color: #c084fc !important;
}

/* Page Header Title */
.header-title {
    background: linear-gradient(135deg, #c084fc 0%, #06b6d4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
    font-size: 3rem;
    margin-bottom: 0.2rem;
    text-align: center;
    filter: drop-shadow(0 2px 10px rgba(168, 85, 247, 0.4));
}

.header-subtitle {
    color: #94a3b8;
    text-align: center;
    font-size: 1.15rem;
    margin-bottom: 2rem;
}

/* Glassmorphism Cards */
.glass-card {
    background: rgba(30, 41, 59, 0.7);
    border-radius: 16px;
    padding: 24px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    margin-bottom: 1.5rem;
}

.glass-card-interactive {
    border: 1px solid rgba(168, 85, 247, 0.35) !important;
    box-shadow: 0 8px 32px 0 rgba(168, 85, 247, 0.15) !important;
}

.glass-card-success {
    border: 1px solid rgba(34, 197, 94, 0.35) !important;
    box-shadow: 0 8px 32px 0 rgba(34, 197, 94, 0.15) !important;
}

/* Glowing Badges */
.badge-playlist {
    background: linear-gradient(135deg, #a855f7 0%, #7e22ce 100%);
    color: white !important;
    padding: 6px 16px;
    border-radius: 20px;
    font-weight: 600;
    display: inline-block;
    box-shadow: 0 0 15px rgba(168, 85, 247, 0.4);
    font-size: 0.95rem;
    margin-bottom: 10px;
}

.badge-video {
    background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
    color: white !important;
    padding: 6px 16px;
    border-radius: 20px;
    font-weight: 600;
    display: inline-block;
    box-shadow: 0 0 15px rgba(6, 182, 212, 0.4);
    font-size: 0.95rem;
    margin-bottom: 10px;
}

/* Premium Buttons Styling */
div.stButton > button {
    background: linear-gradient(135deg, #a855f7 0%, #7e22ce 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 10px 24px !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(168, 85, 247, 0.3) !important;
    width: 100% !important;
}

div.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(168, 85, 247, 0.5) !important;
    background: linear-gradient(135deg, #c084fc 0%, #a855f7 100%) !important;
}

div.stButton > button:active {
    transform: translateY(1px) !important;
}

/* Cancel Button overrides */
.cancel-container div.stButton > button {
    background: rgba(51, 65, 85, 0.8) !important;
    color: #cbd5e1 !important;
    box-shadow: none !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
}

.cancel-container div.stButton > button:hover {
    background: rgba(71, 85, 105, 0.9) !important;
    color: white !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
}
</style>
""", unsafe_allow_html=True)


# --- 2. Helper Functions ---
import sys
import urllib.parse

def clean_youtube_url(url):
    try:
        parsed = urllib.parse.urlparse(url)
        if 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc:
            query_params = urllib.parse.parse_qs(parsed.query)
            if 'list' in query_params:
                playlist_id = query_params['list'][0]
                return f"https://www.youtube.com/playlist?list={playlist_id}"
    except Exception:
        pass
    return url

def make_progress_hook(state_ref):
    def progress_hook(d):
        if state_ref.get('cancel_download'):
            raise Exception("USER_CANCELLED")
            
        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            
            if total > 0:
                percentage = downloaded / total
                percentage = max(0.0, min(1.0, percentage))
            else:
                percentage = 0.0
                
            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024) if total > 0 else 0
            
            speed = d.get('speed')
            speed_mb = speed / (1024 * 1024) if speed else 0
            
            eta = d.get('eta')
            eta_str = f"{eta} 秒" if eta is not None else "計算中..."
            speed_str = f"{speed_mb:.2f} MB/秒" if speed_mb > 0 else "計算中..."
            
            filename = os.path.basename(d.get('filename', '檔案'))
            
            state_ref['progress'] = percentage
            state_ref['info_text'] = (
                f"📥 **正下載檔案**: `{filename}`\n\n"
                f"📊 **進度**: {percentage*100:.1f}% ({downloaded_mb:.1f} MB / {total_mb:.1f} MB)\n\n"
                f"⚡ **下載速度**: {speed_str} | ⏳ **預估剩餘時間**: {eta_str}"
            )
            
        elif d['status'] == 'finished':
            state_ref['progress'] = 1.0
            state_ref['info_text'] = "🎉 **檔案下載完成！** 正在進行轉檔或收尾處理中..."
    return progress_hook

def get_ffmpeg_dir():
    # If running inside PyInstaller bundle
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    
    # Check if ffmpeg.exe exists in the unpacked bundle folder
    if os.path.exists(os.path.join(base_dir, 'ffmpeg.exe')):
        return base_dir
        
    # Check if ffmpeg.exe exists in the local development 'bin' folder
    local_bin = os.path.join(base_dir, 'bin')
    if os.path.exists(os.path.join(local_bin, 'ffmpeg.exe')):
        return local_bin
        
    return None

def get_default_download_dir():
    home = os.path.expanduser('~')
    downloads = os.path.join(home, 'Downloads')
    if os.path.exists(downloads):
        return downloads
    return os.path.abspath('.')

def check_ffmpeg():
    if get_ffmpeg_dir() is not None:
        return True
    return shutil.which('ffmpeg') is not None


# --- 3. Session State Initialization ---
if 'analyzed_info' not in st.session_state:
    st.session_state.analyzed_info = None
if 'analysis_error' not in st.session_state:
    st.session_state.analysis_error = None
if 'confirm_screen' not in st.session_state:
    st.session_state.confirm_screen = False
if 'downloading' not in st.session_state:
    st.session_state.downloading = False
if 'download_success' not in st.session_state:
    st.session_state.download_success = False
if 'url_input' not in st.session_state:
    st.session_state.url_input = ""
if 'download_state' not in st.session_state:
    st.session_state.download_state = {
        'progress': 0.0,
        'info_text': "⏳ 正在啟動 yt-dlp 下載引擎...",
        'cancel_download': False,
        'status': 'idle',  # 'idle', 'running', 'success', 'failed', 'cancelled'
        'error_message': ''
    }
if 'add_index_prefix' not in st.session_state:
    st.session_state.add_index_prefix = True




# --- 4. Sidebar: Settings & Accounts ---
with st.sidebar:
    st.markdown('<div style="text-align: center;"><span style="font-size: 3rem;">⚙️</span></div>', unsafe_allow_html=True)
    st.title("系統設定")
    st.markdown("---")

    # Account Authentication Section
    st.subheader("👤 帳號與身份驗證")
    st.write("設定登入的帳號以存取私人影片或繞過限制。")
    
    use_auth = st.checkbox("啟用帳號密碼登入", value=False)
    
    username = ""
    password = ""
    if use_auth:
        username = st.text_input("帳號 (Username)")
        password = st.text_input("密碼 (Password)", type="password")
        
    st.markdown(" ")
    st.markdown("**📂 使用 Cookies 檔案登入 (極推薦)**")
    st.caption("很多影音網站（如 YouTube）對帳密登入有嚴格驗證。上傳 `cookies.txt` 是目前最穩定的繞過方式。")
    uploaded_cookie_file = st.file_uploader("上傳 cookies.txt", type=["txt"])

    st.markdown("---")
    
    # FFmpeg environment check
    ffmpeg_available = check_ffmpeg()
    st.subheader("🛠️ 系統環境檢查")
    if ffmpeg_available:
        st.success("✅ **FFmpeg 已安裝**\n支援高音質 MP3 轉檔！")
    else:
        st.warning("⚠️ **FFmpeg 未安裝**\n僅能下載原始音訊檔，無法轉檔為高音質 MP3，請先安裝並加入 PATH。")


# --- 5. Main UI Layout ---
st.markdown('<div class="header-title">yt-dlp Premium GUI</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">基於 yt-dlp 極速核心的圖形化影音下載器</div>', unsafe_allow_html=True)

# Main Grid/Form
if not st.session_state.confirm_screen and not st.session_state.downloading:
    
    # Show Success message from previous download
    if st.session_state.download_success:
        st.markdown("""
        <div class="glass-card glass-card-success">
            <h3 style="color: #22c55e; margin-top: 0;">🎉 下載成功！</h3>
            <p style="margin-bottom: 0;">您的影音檔案已經成功下載並儲存至指定資料夾。</p>
        </div>
        """, unsafe_allow_html=True)
        # Clear it
        st.session_state.download_success = False

    # Download configuration card
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("1. 選擇格式與下載資料夾")
    
    col1, col2 = st.columns(2)
    with col1:
        format_type = st.radio(
            "下載格式選擇",
            ["影片 (MP4 / 最佳畫質)", "音訊 (MP3 / 320kbps 最佳音質)"],
            index=0
        )
    with col2:
        default_dir = get_default_download_dir()
        download_dir = st.text_input("下載儲存路徑", value=default_dir)
        
        # Verify download directory
        if not os.path.exists(download_dir):
            st.caption("⚠️ 資料夾目前不存在，下載時將會自動為您建立。")
            
        # 自動前綴選項
        add_index_prefix = st.checkbox("自動為播放清單加上序號前綴 (如 01_檔名)", value=st.session_state.add_index_prefix)
        st.session_state.add_index_prefix = add_index_prefix
    
    st.markdown('</div>', unsafe_allow_html=True)

    # Input Box card
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("2. 輸入影音連結")
    
    url = st.text_input(
        "請輸入影音 URL (例如 YouTube 影片、播放清單連結)",
        placeholder="https://www.youtube.com/watch?v=... 或 https://www.youtube.com/playlist?list=...",
        value=st.session_state.url_input
    )
    st.session_state.url_input = url

    # Error alert
    if st.session_state.analysis_error:
        st.error(f"❌ 解析網址時發生錯誤:\n{st.session_state.analysis_error}")
        st.session_state.analysis_error = None
        
    st.markdown(" ")
    btn_col_1, btn_col_2, btn_col_3 = st.columns([1, 2, 1])
    with btn_col_2:
        analyze_btn = st.button("🚀 分析影音網址並下載", use_container_width=True)
        
    st.markdown('</div>', unsafe_allow_html=True)

    if analyze_btn:
        if not url.strip():
            st.warning("⚠️ 請輸入有效的 URL 連結！")
        else:
            # Show a loading spinner during extraction
            with st.spinner("🔍 正在分析網址並提取影音資訊，請稍候..."):
                # Build YDL options for metadata extraction
                ydl_opts = {
                    'extract_flat': True,
                    'skip_download': True,
                    'quiet': True,
                    'noplaylist': False,
                }
                
                # Setup FFmpeg Location
                ffmpeg_dir = get_ffmpeg_dir()
                if ffmpeg_dir:
                    ydl_opts['ffmpeg_location'] = ffmpeg_dir
                
                # Setup authentication
                if use_auth and username and password:
                    ydl_opts['username'] = username
                    ydl_opts['password'] = password
                
                # Save uploaded cookie file locally
                temp_cookie_path = None
                if uploaded_cookie_file is not None:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_cookie:
                        temp_cookie.write(uploaded_cookie_file.getvalue())
                        temp_cookie_path = temp_cookie.name
                    ydl_opts['cookiefile'] = temp_cookie_path

                try:
                    # Extract info
                    cleaned_url = clean_youtube_url(url)
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(cleaned_url, download=False)
                        
                    if info:
                        st.session_state.analyzed_info = info
                        # Save download configs for later
                        st.session_state.download_format = format_type
                        st.session_state.download_path = download_dir
                        st.session_state.confirm_screen = True
                        st.session_state.analysis_error = None
                        st.rerun()
                    else:
                        st.session_state.analysis_error = "未能獲取有效的影音資訊。"
                except Exception as e:
                    st.session_state.analysis_error = str(e)
                finally:
                    # Clean up temp cookie file
                    if temp_cookie_path and os.path.exists(temp_cookie_path):
                        try:
                            os.unlink(temp_cookie_path)
                        except:
                            pass


# --- 6. Confirmation Screen ---
elif st.session_state.confirm_screen and st.session_state.analyzed_info:
    
    info = st.session_state.analyzed_info
    is_playlist = info.get('_type') == 'playlist'
    title = info.get('title', '未知標題')
    uploader = info.get('uploader') or info.get('playlist_uploader') or '未知來源'
    
    # Determine count
    if is_playlist:
        entries = info.get('entries', [])
        count = len(entries) if entries else 0
    else:
        count = 1

    st.markdown('<div class="glass-card glass-card-interactive">', unsafe_allow_html=True)
    
    # Header Badge based on Type
    if is_playlist:
        st.markdown(f'<span class="badge-playlist">📢 偵測到整個播放清單 (Playlist)</span>', unsafe_allow_html=True)
    else:
        st.markdown(f'<span class="badge-video">🎥 偵測到單一影片 (Single Video)</span>', unsafe_allow_html=True)

    # Info Details
    st.subheader(f"🎵 標題：{title}")
    st.write(f"**來源 / 上傳者**：{uploader}")
    st.write(f"**目標儲存路徑**：`{st.session_state.download_path}`")
    st.write(f"**下載格式**：`{st.session_state.download_format}`")
    
    st.markdown("---")
    
    # Visual Highlights of files count
    col_badge1, col_badge2 = st.columns([1, 3])
    with col_badge1:
        st.markdown(f"""
        <div style="text-align: center; background: rgba(168, 85, 247, 0.15); border: 2px solid #a855f7; border-radius: 12px; padding: 10px;">
            <div style="font-size: 2.2rem; font-weight: 700; color: #c084fc;">{count}</div>
            <div style="font-size: 0.85rem; color: #e2e8f0; font-weight: 600;">預計下載總數</div>
        </div>
        """, unsafe_allow_html=True)
    with col_badge2:
        if is_playlist:
            st.markdown(f"""
            <div style="padding-top: 5px;">
                <span style="font-size: 1.1rem; font-weight: 600; color: #a855f7;">確定要下載整個播放清單嗎？</span><br>
                <span style="color: #94a3b8; font-size: 0.95rem;">這將會依序下載清單內的所有影音（共 <strong>{count}</strong> 個檔案）。這可能會花費較長的時間。</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="padding-top: 5px;">
                <span style="font-size: 1.1rem; font-weight: 600; color: #06b6d4;">即將下載此單一影片/音訊</span><br>
                <span style="color: #94a3b8; font-size: 0.95rem;">將直接抓取最佳品質檔案並儲存至您的儲存路徑。</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(" ")
    st.markdown(" ")
    
    # Controls Buttons
    btn_confirm_col, btn_cancel_col = st.columns(2)
    
    with btn_confirm_col:
        confirm_btn = st.button("🚀 確定！開始下載", key="confirm_download_btn")
        
    with btn_cancel_col:
        st.markdown('<div class="cancel-container">', unsafe_allow_html=True)
        cancel_btn = st.button("❌ 取消並返回", key="cancel_download_btn")
        st.markdown('</div>', unsafe_allow_html=True)
        
    st.markdown('</div>', unsafe_allow_html=True)

    # Handlers
    if cancel_btn:
        st.session_state.confirm_screen = False
        st.session_state.analyzed_info = None
        st.rerun()
        
    if confirm_btn:
        st.session_state.downloading = True
        st.session_state.confirm_screen = False
        st.rerun()


# --- 7. Downloading Screen & Live Progress ---
elif st.session_state.downloading:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("📥 正在為您下載影音，請勿關閉網頁...")
    
    state_ref = st.session_state.download_state
    
    # 渲染進度容器
    progress_bar = st.progress(state_ref['progress'])
    info_box = st.empty()
    
    # 顯示目前進度
    if state_ref['cancel_download']:
        info_box.warning("⏳ 正在要求終止下載，請稍候...")
    else:
        info_box.info(state_ref['info_text'])
        
    # 如果還在下載中，顯示終止下載按鈕
    if state_ref['status'] == 'running':
        st.markdown('<div class="cancel-container">', unsafe_allow_html=True)
        stop_btn = st.button("🛑 終止下載", key="stop_live_download_btn", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        if stop_btn:
            state_ref['cancel_download'] = True
            info_box.warning("⏳ 正在要求終止下載，請稍候...")
            st.rerun()

    # 啟動下載背景執行緒的邏輯
    if state_ref['status'] == 'idle':
        state_ref['status'] = 'running'
        state_ref['progress'] = 0.0
        state_ref['info_text'] = "⏳ 正在啟動 yt-dlp 下載引擎..."
        state_ref['cancel_download'] = False
        state_ref['error_message'] = ""
        
        # 判斷是否為播放清單，以決定是否加上序號前綴
        is_playlist = st.session_state.analyzed_info.get('_type') == 'playlist' if st.session_state.analyzed_info else False
        if st.session_state.add_index_prefix and is_playlist:
            filename_format = '%(playlist_index)02d_%(title)s.%(ext)s'
        else:
            filename_format = '%(title)s.%(ext)s'
            
        # 準備下載用的配置選項與 cookies 暫存
        ydl_opts = {
            'outtmpl': os.path.join(st.session_state.download_path, filename_format),
            'quiet': True,
            'no_warnings': True,
            'noplaylist': False,
        }
        
        ffmpeg_dir = get_ffmpeg_dir()
        if ffmpeg_dir:
            ydl_opts['ffmpeg_location'] = ffmpeg_dir
        
        is_mp3 = "音訊" in st.session_state.download_format
        if is_mp3:
            ydl_opts['format'] = 'bestaudio/best'
            if ffmpeg_available:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }]
        else:
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            ydl_opts['merge_output_format'] = 'mp4'

        if use_auth and username and password:
            ydl_opts['username'] = username
            ydl_opts['password'] = password
            
        temp_cookie_path = None
        if uploaded_cookie_file is not None:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_cookie:
                    temp_cookie.write(uploaded_cookie_file.getvalue())
                    temp_cookie_path = temp_cookie.name
                ydl_opts['cookiefile'] = temp_cookie_path
            except:
                pass

        ydl_opts['progress_hooks'] = [make_progress_hook(state_ref)]

        # 建立目標資料夾
        if not os.path.exists(st.session_state.download_path):
            try:
                os.makedirs(st.session_state.download_path, exist_ok=True)
            except Exception as e:
                state_ref['status'] = 'failed'
                state_ref['error_message'] = f"無法建立儲存資料夾: {str(e)}"
                st.rerun()

        # 定義背景執行緒的函數
        def bg_download_thread_func(opts, url_input, cookie_path, s_ref):
            try:
                url_to_download = clean_youtube_url(url_input)
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url_to_download])
                s_ref['status'] = 'success'
            except Exception as e:
                err_str = str(e)
                if "USER_CANCELLED" in err_str or s_ref.get('cancel_download'):
                    s_ref['status'] = 'cancelled'
                else:
                    s_ref['status'] = 'failed'
                    s_ref['error_message'] = err_str
            finally:
                # 清理暫存 cookie 檔
                if cookie_path and os.path.exists(cookie_path):
                    try:
                        os.unlink(cookie_path)
                    except:
                        pass

        # 啟動背景執行緒
        thread = threading.Thread(
            target=bg_download_thread_func,
            args=(ydl_opts, st.session_state.url_input, temp_cookie_path, state_ref),
            daemon=True
        )
        thread.start()
        st.rerun()

    # 處理不同的狀態
    if state_ref['status'] == 'running':
        # 如果還在運行中，就 sleep 0.3 秒後主動 rerun，維持進度更新與終止按鈕點擊偵測
        time.sleep(0.3)
        st.rerun()
        
    elif state_ref['status'] == 'success':
        # 成功下載，清理狀態並跳轉
        state_ref['status'] = 'idle'
        st.session_state.download_success = True
        st.session_state.downloading = False
        st.session_state.confirm_screen = False
        st.session_state.analyzed_info = None
        st.rerun()
        
    elif state_ref['status'] == 'cancelled':
        # 取消下載的 UI
        st.warning("⚠️ **下載已手動終止**")
        st.write("已成功取消本次的影音下載任務，未完成的暫存檔案也已被清理。")
        return_btn = st.button("返回主頁面", key="return_home_cancelled")
        if return_btn:
            state_ref['status'] = 'idle'
            st.session_state.downloading = False
            st.session_state.confirm_screen = False
            st.session_state.analyzed_info = None
            st.rerun()
            
    elif state_ref['status'] == 'failed':
        # 失敗的 UI
        st.error(f"❌ **下載失敗**\n\n發生了以下錯誤：\n`{state_ref['error_message']}`")
        return_btn = st.button("返回主頁面", key="return_home_failed")
        if return_btn:
            state_ref['status'] = 'idle'
            st.session_state.downloading = False
            st.session_state.confirm_screen = False
            st.session_state.analyzed_info = None
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
