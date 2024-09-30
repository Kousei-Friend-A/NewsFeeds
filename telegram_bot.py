import os
import feedparser
import requests
import logging
from pytube import YouTube
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import time
from collections import deque

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Directly set your configuration here
API_ID = 8143727
API_HASH = "e2e9b22c6522465b62d8445840a526b1"
BOT_TOKEN = "7735485169:AAEReRLDsc-GshqXOKVveRGtPHpjv13Lrj4"
CHANNEL_ID = -1002311865677
RSS_URL = "https://www.livechart.me/feeds/headlines"

# Create a new Pyrogram client with API credentials
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Caching for sent updates
sent_updates = deque(maxlen=100)  # Store last 100 sent titles

def download_image(image_url, title):
    try:
        logging.info(f"Downloading image from {image_url}")
        response = requests.get(image_url)
        response.raise_for_status()
        file_path = f"{title}.jpg"
        with open(file_path, 'wb') as file:
            file.write(response.content)
        logging.info(f"Downloaded image: {file_path}")
        return file_path
    except requests.RequestException as e:
        logging.error(f"Failed to download image: {e}")
        return None

def download_youtube_video(video_url):
    try:
        logging.info(f"Downloading video from {video_url}")
        yt = YouTube(video_url)
        video_stream = yt.streams.get_highest_resolution()
        file_path = f"{yt.title}.mp4"
        video_stream.download(filename=file_path)
        logging.info(f"Downloaded video: {file_path}")
        return file_path
    except Exception as e:
        logging.error(f"Failed to download video: {e}")
        return None

def fetch_and_send_updates():
    while True:
        try:
            logging.info("Fetching RSS feed...")
            feed = feedparser.parse(RSS_URL)

            for entry in feed.entries:
                title = entry.title

                # Check if the title has already been sent
                if title not in sent_updates:
                    sent_updates.append(title)
                    youtube_link = entry.link if "youtube.com" in entry.link else None

                    if youtube_link:
                        video_path = download_youtube_video(youtube_link)
                        if video_path:
                            app.send_video(chat_id=CHANNEL_ID, video=video_path, caption=title)
                            os.remove(video_path)
                    else:
                        image_url = entry.enclosure.url if 'enclosure' in entry else None
                        if image_url:
                            image_path = download_image(image_url, title)
                            if image_path:
                                app.send_photo(chat_id=CHANNEL_ID, photo=image_path, caption=title)
                                os.remove(image_path)

                    logging.info(f"Sent update for: {title}")

            logging.info("Waiting for the next update...")
            time.sleep(600)  # Wait before fetching again

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            time.sleep(60)

@app.on_message(filters.command("start") & filters.private)
def start(client, message):
    logging.info(f"Start command received from {message.chat.id}")
    
    button = InlineKeyboardMarkup([[InlineKeyboardButton("Visit Channel", url=f"tg://resolve?domain={CHANNEL_ID}")]])
    
    # Sending a message with the button
    app.send_message(
        chat_id=message.chat.id,
        text="Welcome to the Anime Headlines Bot! Updates will be sent to the channel.",
        reply_markup=button
    )

if __name__ == '__main__':
    with app:
        logging.info("Bot is starting...")
        fetch_and_send_updates()
