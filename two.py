import requests
from bs4 import BeautifulSoup
import pygame
from io import BytesIO
from PIL import Image
import datetime
import re

FEED_URL = "https://ourdailybreadministries.ca/feed/"

# ----------------------------
# 1. Fetch the RSS feed
# ----------------------------
def fetch_first_item():
    print("[INFO] Fetching RSS feed...")
    response = requests.get(FEED_URL, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "xml")

    first_item = soup.find("item")
    if not first_item:
        raise Exception("No items found in feed.")

    title = first_item.find("title").text.strip()
    link = first_item.find("link").text.strip()
    pubDate = first_item.find("pubDate").text.strip()
    creator_tag = first_item.find("dc:creator")
    creator = creator_tag.text.strip() if creator_tag else "Unknown"
    description_tag = first_item.find("description")
    description = description_tag.text.strip() if description_tag else ""

    print(f"[INFO] Title: {title}")
    print(f"[INFO] Author: {creator}")
    print(f"[INFO] Date: {pubDate}")
    print(f"[INFO] Link: {link}")

    return {
        "title": title,
        "creator": creator,
        "pubDate": pubDate,
        "link": link,
        "description": description
    }


# ----------------------------
# 2. Scrape the devotional page for MP3
# ----------------------------
def get_mp3_from_page(url):
    print(f"[INFO] Fetching devotional page: {url}")
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if response.status_code != 200:
        raise Exception(f"Failed to load devotional page: {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")

    # 1. Check for <audio> tag
    audio_tag = soup.find("audio")
    if audio_tag and audio_tag.get("src"):
        return audio_tag.get("src")

    # 2. Fallback: search for any .mp3 link in HTML
    match = re.search(r'https?://[^\s"]+\.mp3', response.text)
    if match:
        return match.group(0)

    return None


# ----------------------------
# 3. Play MP3 using pygame
# ----------------------------
def play_mp3(mp3_url):
    print(f"[INFO] MP3 URL found: {mp3_url}")
    print("[INFO] Downloading MP3...")

    mp3_data = requests.get(mp3_url, headers={"User-Agent": "Mozilla/5.0"}).content
    mp3_file = "today_devotional.mp3"

    with open(mp3_file, "wb") as f:
        f.write(mp3_data)

    print("[INFO] Playing devotional audio...")
    pygame.mixer.init()
    pygame.mixer.music.load(mp3_file)
    pygame.mixer.music.play()

    # Wait until playback finishes
    while pygame.mixer.music.get_busy():
        continue

# ----------------------------
# MAIN EXECUTION
# ----------------------------
if __name__ == "__main__":
    try:
        item = fetch_first_item()
        mp3_url = get_mp3_from_page(item["link"])
        if not mp3_url:
            print("[ERROR] Could not find MP3 for this devotional.")
        else:
            play_mp3(mp3_url)
    except Exception as e:
        print("[ERROR]", e)
