import sys
import requests
import xml.etree.ElementTree as ET
from io import BytesIO
from PIL import Image
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QTextBrowser, QScrollArea
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

FEED_URL = "https://api.experience.odb.org/devotionals/feed/?country=CA"

def fetch_first_item():
    response = requests.get(FEED_URL)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    item = root.find("./channel/item")

    def get(tag):
        el = item.find(tag)
        return el.text if el is not None else ""

    return {
        "title": get("title"),
        "creator": get("{http://purl.org/dc/elements/1.1/}creator"),
        "description": get("description"),
        "pubDate": get("pubDate"),
        "image": get("image"),
        "link": get("link")
    }

class ODBViewer(QWidget):
    def __init__(self, data):
        super().__init__()
        self.setWindowTitle("ODB Devotional Viewer")
        self.setGeometry(200, 200, 900, 1100)

        layout = QVBoxLayout()

        # Title
        title = QLabel(data["title"])
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        title.setWordWrap(True)
        layout.addWidget(title)

        # Creator
        creator = QLabel(f"By: {data['creator']}")
        creator.setStyleSheet("font-size: 16px;")
        layout.addWidget(creator)

        # Date
        date = QLabel(data["pubDate"])
        date.setStyleSheet("font-size: 14px; color: gray;")
        layout.addWidget(date)

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

        # Description (HTML in scroll area)
        text_browser = QTextBrowser()
        text_browser.setHtml(data["description"])
        text_browser.setMinimumHeight(600)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(text_browser)
        layout.addWidget(scroll)

        self.setLayout(layout)

def main():
    app = QApplication(sys.argv)
    data = fetch_first_item()
    viewer = ODBViewer(data)
    viewer.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

