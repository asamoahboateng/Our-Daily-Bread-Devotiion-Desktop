import sys
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image
import re
from urllib.parse import urlparse, parse_qs, unquote

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QTextBrowser, QVBoxLayout,
    QScrollArea, QPushButton, QHBoxLayout, QSlider
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

FEED_URL = "https://ourdailybreadministries.ca/feed/"

# ----------------------------
# Utility Functions
# ----------------------------

def fetch_first_item():
    response = requests.get(FEED_URL, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "xml")

    first_item = soup.find("item")
    title = first_item.find("title").text.strip()
    link = first_item.find("link").text.strip()
    pubDate = first_item.find("pubDate").text.strip()
    creator_tag = first_item.find("dc:creator")
    creator = creator_tag.text.strip() if creator_tag else "Unknown"
    description_tag = first_item.find("description")
    description = description_tag.text.strip() if description_tag else ""

    # Optional: try to get image from description HTML
    img_soup = BeautifulSoup(description, "html.parser")
    img_tag = img_soup.find("img")
    image_url = img_tag["src"] if img_tag else None

    return {
        "title": title,
        "creator": creator,
        "pubDate": pubDate,
        "link": link,
        "description": description,
        "image": image_url
    }

def get_mp3_from_page(url):
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if response.status_code != 200:
        raise Exception(f"Failed to load devotional page: {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")

    # 1. Check <audio> tag (Direct link)
    audio_tag = soup.find("audio")
    if audio_tag and audio_tag.get("src"):
        print("[INFO] Found MP3 URL in <audio> tag.")
        return audio_tag.get("src")

    # 2. Check for playlist.json URL in page
    match = re.search(r'https://ourdailybreadministries\.ca/\?load=playlist\.json[^\s"\']+', response.text)
    if match:
        playlist_url = match.group(0)
        print(f"[INFO] Found playlist JSON URL: {playlist_url}")

        # Normalize the URL by replacing the HTML entity before parsing
        normalized_playlist_url = playlist_url.replace("&#038;", "&")
        
        # Parse query string for 'feed'
        parsed = urlparse(normalized_playlist_url)
        qs = parse_qs(parsed.query)
        
        if "feed" in qs and qs["feed"]:
            # Use unquote to decode the URL-encoded MP3 link
            mp3_url = unquote(qs["feed"][0]) 
            print(f"[INFO] Direct MP3 URL from 'feed' param: {mp3_url}")
            return mp3_url

        # Fallback: fetch JSON if feed param not found (less common)
        try:
            json_resp = requests.get(normalized_playlist_url, headers={"User-Agent": "Mozilla/5.0"}).json()
            if "tracks" in json_resp and len(json_resp["tracks"]) > 0:
                mp3_url = json_resp["tracks"][0].get("file")
                if mp3_url:
                    print(f"[INFO] Direct MP3 URL from JSON: {mp3_url}")
                    return mp3_url
        except requests.exceptions.JSONDecodeError:
            print("[WARNING] Could not decode playlist JSON.")

    # 3. Fallback: search for any .mp3 in page (only run if steps 1 & 2 failed)
    match2 = re.search(r'https?://[^\s"]+\.mp3', response.text)
    if match2:
        print("[INFO] Found MP3 URL via simple regex fallback (should only run if extraction failed).")
        return match2.group(0)

    print("[ERROR] Could not find MP3 URL after checking all methods.")
    return None

def format_time(ms):
    """Converts milliseconds to HH:MM:SS format."""
    s = int(ms / 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02}:{m:02}:{s:02}"
    else:
        return f"{m:02}:{s:02}"

# ----------------------------
# GUI Class
# ----------------------------
class ODBViewer(QWidget):
    def __init__(self, data):
        super().__init__()
        self.setWindowTitle("ODB Devotional Viewer")
        self.setGeometry(200, 200, 400, 600)

        layout = QVBoxLayout()

        # --- Content Display ---
        title_label = QLabel(data["title"])
        title_label.setStyleSheet("font-size: 22px; font-weight: bold;")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        author_label = QLabel(f"By: {data['creator']}")
        author_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(author_label)

        date_label = QLabel(data["pubDate"])
        date_label.setStyleSheet("font-size: 14px; color: gray;")
        layout.addWidget(date_label)

        # Image Rendering
        if data["image"]:
            self.render_image(data["image"], layout)

        # Description
        text_browser = QTextBrowser()
        text_browser.setHtml(data["description"])
        text_browser.setMinimumHeight(200)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(text_browser)
        layout.addWidget(scroll)

        # --- Audio Player Setup ---
        self.player = QMediaPlayer()
        self.mp3_url = get_mp3_from_page(data["link"])
        print(f"[INFO] Direct MP3 URL assigned to player: {self.mp3_url}\n") 

        # --- Audio Controls Layout ---
        self.create_audio_controls(layout)

        # Connect Signals for Progress Bar
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)

        # Auto-play
        if self.mp3_url:
            self.play_audio()

        self.setLayout(layout)

    def render_image(self, image_url, parent_layout):
        """Fetches and displays the image."""
        try:
            img_data = requests.get(image_url).content
            pil_img = Image.open(BytesIO(img_data))
            # Resize image to fit the layout width (e.g., 750px) while maintaining aspect ratio
            width = 750
            height = int(pil_img.height * (width / pil_img.width))
            pil_img = pil_img.resize((width, height))
            
            img_buffer = BytesIO()
            pil_img.save(img_buffer, format="PNG")
            pix = QPixmap()
            pix.loadFromData(img_buffer.getvalue())
            img_label = QLabel()
            img_label.setPixmap(pix)
            img_label.setAlignment(Qt.AlignCenter)
            parent_layout.addWidget(img_label)
        except Exception as e:
            print(f"[ERROR] Could not load or display image: {e}")

    def create_audio_controls(self, parent_layout):
        """Sets up the buttons, slider, and time labels."""
        
        # 1. Playback Buttons
        button_layout = QHBoxLayout()
        play_btn = QPushButton("▶️ Play")
        pause_btn = QPushButton("⏸️ Pause")
        stop_btn = QPushButton("⏹️ Stop")

        play_btn.clicked.connect(self.play_audio)
        pause_btn.clicked.connect(self.player.pause)
        stop_btn.clicked.connect(self.player.stop)

        button_layout.addWidget(play_btn)
        button_layout.addWidget(pause_btn)
        button_layout.addWidget(stop_btn)
        parent_layout.addLayout(button_layout)
        
        # 2. Progress Bar and Time Labels
        progress_layout = QHBoxLayout()
        
        self.position_label = QLabel("00:00")
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0) # Range will be set dynamically by durationChanged
        # Connect slider movement to player position
        self.slider.sliderMoved.connect(self.player.setPosition)
        
        self.duration_label = QLabel("00:00")
        
        progress_layout.addWidget(self.position_label)
        progress_layout.addWidget(self.slider)
        progress_layout.addWidget(self.duration_label)
        
        parent_layout.addLayout(progress_layout)

    def play_audio(self):
        if self.mp3_url:
            if self.player.mediaStatus() == QMediaPlayer.NoMedia:
                self.player.setMedia(QMediaContent(QUrl(self.mp3_url)))
            self.player.play()
        else:
            print("[ERROR] No MP3 found to play.")

    # ----------------------------
    # Progress Bar Handlers
    # ----------------------------
    def duration_changed(self, duration):
        """Sets the maximum value of the slider."""
        self.slider.setRange(0, duration)
        self.duration_label.setText(format_time(duration))

    def position_changed(self, position):
        """Updates the slider position and current time label."""
        if not self.slider.isSliderDown():
            self.slider.setValue(position)
        self.position_label.setText(format_time(position))


# ----------------------------
# Run App
# ----------------------------
if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        devotional = fetch_first_item()
        viewer = ODBViewer(devotional)
        viewer.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"An error occurred during application startup: {e}")