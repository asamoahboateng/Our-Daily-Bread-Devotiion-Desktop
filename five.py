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

    # Search for playlist.json URL
    match = re.search(r'https://ourdailybreadministries\.ca/\?load=playlist\.json[^\s"\']+', response.text)
    if match:
        playlist_url = match.group(0).replace("&#038;", "&")
        parsed = urlparse(playlist_url)
        qs = parse_qs(parsed.query)
        if "feed" in qs and qs["feed"]:
            mp3_url = unquote(qs["feed"][0])
            print(f"[INFO] Direct MP3 URL: {mp3_url}")
            return mp3_url
    # fallback: search any .mp3
    match2 = re.search(r'https?://[^\s"]+\.mp3', response.text)
    if match2:
        print(f"[INFO] Direct MP3 URL (fallback): {match2.group(0)}")
        return match2.group(0)

    print("[ERROR] Could not find MP3 URL")
    return None

def format_time(ms):
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
        self.setGeometry(200, 200, 900, 1000)
        self.setStyleSheet("background-color: #f9f9f9;")

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Title, Author, Date
        title_label = QLabel(data["title"])
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        author_label = QLabel(f"By: {data['creator']}")
        author_label.setStyleSheet("font-size: 16px; color: #555;")
        layout.addWidget(author_label)

        date_label = QLabel(data["pubDate"])
        date_label.setStyleSheet("font-size: 14px; color: gray;")
        layout.addWidget(date_label)

        # Image
        if data["image"]:
            self.render_image(data["image"], layout)

        # Description
        text_browser = QTextBrowser()
        text_browser.setHtml(data["description"])
        text_browser.setMinimumHeight(400)
        text_browser.setStyleSheet("background-color: #fff; border-radius: 8px; padding: 10px;")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(text_browser)
        layout.addWidget(scroll)

        # Audio Player
        self.player = QMediaPlayer()
        self.mp3_url = get_mp3_from_page(data["link"])
        print(f"[INFO] MP3 URL assigned: {self.mp3_url}\n")

        self.create_audio_controls(layout)
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)

        # Auto-play
        if self.mp3_url:
            self.play_audio()

        self.setLayout(layout)

    def render_image(self, image_url, parent_layout):
        try:
            img_data = requests.get(image_url).content
            pil_img = Image.open(BytesIO(img_data))
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
            print(f"[ERROR] Could not load image: {e}")

    def create_audio_controls(self, parent_layout):
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        button_layout.setAlignment(Qt.AlignLeft)

        play_btn = QPushButton("▶️ Play")
        pause_btn = QPushButton("⏸️ Pause")
        stop_btn = QPushButton("⏹️ Stop")
        for btn, color in zip([play_btn, pause_btn, stop_btn], ["#4caf50", "#ff9800", "#f44336"]):
            btn.setStyleSheet(f"font-size: 16px; padding: 10px 20px; background-color: {color}; color: white; border-radius: 6px;")

        play_btn.clicked.connect(self.play_audio)
        pause_btn.clicked.connect(self.player.pause)
        stop_btn.clicked.connect(self.player.stop)
        button_layout.addWidget(play_btn)
        button_layout.addWidget(pause_btn)
        button_layout.addWidget(stop_btn)
        parent_layout.addLayout(button_layout)

        # Progress Slider
        progress_layout = QHBoxLayout()
        self.position_label = QLabel("00:00")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self.player.setPosition)
        self.duration_label = QLabel("00:00")
        self.slider.setStyleSheet(
            "QSlider::groove:horizontal {height:8px; background:#ddd; border-radius:4px;}"
            "QSlider::handle:horizontal {background:#2196f3; width:14px; margin:-3px 0; border-radius:7px;}"
        )
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

    def duration_changed(self, duration):
        self.slider.setRange(0, duration)
        self.duration_label.setText(format_time(duration))

    def position_changed(self, position):
        if not self.slider.isSliderDown():
            self.slider.setValue(position)
        self.position_label.setText(format_time(position))

# ----------------------------
# Run App
# ----------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    devotional = fetch_first_item()
    viewer = ODBViewer(devotional)
    viewer.show()
    sys.exit(app.exec_())
