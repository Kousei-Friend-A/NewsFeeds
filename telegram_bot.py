import os
import feedparser
import requests
import logging
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import asyncio
from collections import deque
from pyrogram.errors import FloodWait

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Directly set your configuration here
API_ID = 8143727
API_HASH = "e2e9b22c6522465b62d8445840a526b1"
BOT_TOKEN = "7735485169:AAEReRLDsc-GshqXOKVveRGtPHpjv13Lrj4"
CHANNEL_ID = '@Anime_NewsFeeds'  # Use the channel username
RSS_URL = "https://www.livechart.me/feeds/headlines"

# Create a new Pyrogram client with API credentials
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Caching for sent updates
sent_updates = deque(maxlen=100)  # Store last 100 sent titles

async def download_image(image_url, title):
    try:
        logging.info(f"Downloading image from {image_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'
        }
        response = requests.get(image_url, headers=headers)
        response.raise_for_status()
        file_path = f"{title}.jpg"
        with open(file_path, 'wb') as file:
            file.write(response.content)
        logging.info(f"Downloaded image: {file_path}")
        return file_path
    except requests.RequestException as e:
        logging.error(f"Failed to download image: {e}")
        return None

async def download_youtube_video(video_url):
    try:
        logging.info(f"Downloading video from {video_url}")
        ydl_opts = {
            'format': 'best',
            'outtmpl': '%(title)s.%(ext)s',
            'noplaylist': True,
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            file_path = f"{info['title']}.{info['ext']}"
            logging.info(f"Downloaded video: {file_path}")
            return file_path
    except Exception as e:
        logging.error(f"Failed to download video from {video_url}: {e}")
        return None

async def fetch_and_send_updates():
    while True:
        try:
            logging.info("Fetching RSS feed...")
            feed = feedparser.parse(RSS_URL)

            for entry in feed.entries:
                title = entry.title

                if title not in sent_updates:
                    sent_updates.append(title)
                    youtube_link = entry.link if "youtube.com" in entry.link else None

                    if youtube_link:
                        video_path = await download_youtube_video(youtube_link)
                        if video_path:
                            await app.send_video(chat_id=CHANNEL_ID, video=video_path, caption=title)
                            logging.info(f"Sent video with title: {title}")
                            os.remove(video_path)  # Clean up the downloaded video
                    else:
                        # Prepare to send the image
                        image_url = None
                        if 'media_thumbnail' in entry:
                            image_url = entry.media_thumbnail[0]['url']
                        elif 'enclosure' in entry:
                            image_url = entry.enclosure.url

                        if image_url:
                            if image_url.endswith("/large.jpg"):
                                image_url = image_url[:-10]

                            logging.info(f"Using image URL: {image_url}")
                            image_path = await download_image(image_url, title)
                            if image_path:
                                await app.send_photo(chat_id=CHANNEL_ID, photo=image_path, caption=title)
                                logging.info(f"Sent image with title: {title}")
                                os.remove(image_path)  # Clean up the downloaded image
                            else:
                                logging.warning(f"Image download failed for: {title}")

                    logging.info(f"Sent update for: {title}")
                    await asyncio.sleep(2)  # Adjust this value as needed

            logging.info("Waiting for the next update...")
            await asyncio.sleep(600)  # Wait before fetching again

        except FloodWait as e:
            logging.warning(f"Flood wait triggered. Waiting for {e.x} seconds.")
            await asyncio.sleep(e.x)  # Wait for the required time

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            await asyncio.sleep(60)  # Wait before retrying

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    logging.info(f"Start command received from {message.chat.id}")
    button = InlineKeyboardMarkup([[InlineKeyboardButton("Visit Channel", url="https://t.me/Anime_NewsFeeds")]])
    await app.send_message(
        chat_id=message.chat.id,
        text="Welcome to the Anime Headlines Bot! Updates will be sent to the channel.",
        reply_markup=button
    )

if __name__ == '__main__':
    with app:
        logging.info("Bot is starting...")
        app.run(fetch_and_send_updates())
