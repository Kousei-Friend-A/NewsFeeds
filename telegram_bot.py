import os
import feedparser
import requests
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import asyncio
from collections import deque

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

async def fetch_and_send_updates():
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
                        # Create a button for More Info
                        button = InlineKeyboardMarkup(
                            [[InlineKeyboardButton("More Info", url=youtube_link)]]
                        )
                        await app.send_message(chat_id=CHANNEL_ID, text=title, reply_markup=button)
                    else:
                        # Get the media thumbnail URL first
                        image_url = None
                        if 'media_thumbnail' in entry:
                            image_url = entry.media_thumbnail[0]['url']
                        elif 'enclosure' in entry:
                            image_url = entry.enclosure.url

                        if image_url:
                            # Remove "/large.jpg" from the URL if it exists
                            if image_url.endswith("/large.jpg"):
                                image_url = image_url[:-10]  # Remove the last 10 characters

                            logging.info(f"Using image URL: {image_url}")
                            image_path = await download_image(image_url, title)
                            if image_path:
                                await app.send_photo(chat_id=CHANNEL_ID, photo=image_path, caption=title)
                                logging.info(f"Sent image with title: {title}")
                                os.remove(image_path)
                            else:
                                logging.warning(f"Image download failed for: {title}")

                    logging.info(f"Sent update for: {title}")

            logging.info("Waiting for the next update...")
            await asyncio.sleep(600)  # Wait before fetching again

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            await asyncio.sleep(60)

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
