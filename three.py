import sys
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image
import re

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QTextBrowser, QVBoxLayout,
    QScrollArea, QPushButton, QHBoxLayout
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

FEED_URL = "https://ourdailybreadministries.ca/feed/"

# ----------------------------
# Fetch first item from RSS
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

# ----------------------------
# Get MP3 from devotional page
# ----------------------------
def get_mp3_from_page(url):
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if response.status_code != 200:
        raise Exception(f"Failed to load devotional page: {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")
    # Check for <audio> tag
    audio_tag = soup.find("audio")
    if audio_tag and audio_tag.get("src"):
        return audio_tag.get("src")
    # Fallback: search for .mp3 in page
    match = re.search(r'https?://[^\s"]+\.mp3', response.text)
    if match:
        return match.group(0)
    return None

# ----------------------------
# GUI Class
# ----------------------------
class ODBViewer(QWidget):
    def __init__(self, data):
        super().__init__()
        self.setWindowTitle("ODB Devotional Viewer")
        self.setGeometry(200, 200, 900, 1000)

        layout = QVBoxLayout()

        # Title
        title_label = QLabel(data["title"])
        title_label.setStyleSheet("font-size: 22px; font-weight: bold;")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        # Author
        author_label = QLabel(f"By: {data['creator']}")
        author_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(author_label)

        # Date
        date_label = QLabel(data["pubDate"])
        date_label.setStyleSheet("font-size: 14px; color: gray;")
        layout.addWidget(date_label)

        # Image
        if data["image"]:
            img_data = requests.get(data["image"]).content
            pil_img = Image.open(BytesIO(img_data))
            pil_img = pil_img.resize((750, 420))
            img_buffer = BytesIO()
            pil_img.save(img_buffer, format="PNG")
            pix = QPixmap()
            pix.loadFromData(img_buffer.getvalue())
            img_label = QLabel()
            img_label.setPixmap(pix)
            img_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(img_label)

        # Description
        text_browser = QTextBrowser()
        text_browser.setHtml(data["description"])
        text_browser.setMinimumHeight(400)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(text_browser)
        layout.addWidget(scroll)

        # Audio Player
        self.player = QMediaPlayer()

        # Buttons: Play / Pause / Stop
        button_layout = QHBoxLayout()
        play_btn = QPushButton("Play")
        pause_btn = QPushButton("Pause")
        stop_btn = QPushButton("Stop")

        play_btn.clicked.connect(self.play_audio)
        pause_btn.clicked.connect(self.player.pause)
        stop_btn.clicked.connect(self.player.stop)

        button_layout.addWidget(play_btn)
        button_layout.addWidget(pause_btn)
        button_layout.addWidget(stop_btn)
        layout.addLayout(button_layout)

        self.mp3_url = get_mp3_from_page(data["link"])
        print("[INFO] MP3 URL:", self.mp3_url)

        # Auto-play on startup
        if self.mp3_url:
            self.play_audio()

        self.setLayout(layout)

    def play_audio(self):
        if self.mp3_url:
            self.player.setMedia(QMediaContent(QUrl(self.mp3_url)))
            self.player.play()
        else:
            print("[ERROR] No MP3 found to play.")

# ----------------------------
# Run app
# ----------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    devotional = fetch_first_item()
    viewer = ODBViewer(devotional)
    viewer.show()
    sys.exit(app.exec_())
