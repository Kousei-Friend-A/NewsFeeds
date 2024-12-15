import os
import feedparser
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dateutil import parser
import aiohttp
import re

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Bot credentials and configuration
API_ID = 27332239
API_HASH = "2fed2c90672125f4c6f42316eed6a837"
BOT_TOKEN = "7391079505:AAE33ohVv-pPWooCVsOaAoSd81DV9T9mC0Y"
CHANNEL_ID = '@anime_newslibrary'
RSS_URL = "https://www.livechart.me/feeds/headlines"

# Paths for storing state
LAST_SENT_TIMESTAMP_FILE = "last_sent_timestamp.txt"
SENT_UPDATES_FILE = "sent_updates.txt"

# Initialize Pyrogram client
app = Client("anime_news_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Utility functions for file-based state management
def load_last_sent_timestamp():
    if os.path.exists(LAST_SENT_TIMESTAMP_FILE):
        with open(LAST_SENT_TIMESTAMP_FILE, 'r') as file:
            return parser.parse(file.read().strip())
    return None

def save_last_sent_timestamp(timestamp):
    with open(LAST_SENT_TIMESTAMP_FILE, 'w') as file:
        file.write(timestamp.isoformat())

def load_sent_updates():
    if os.path.exists(SENT_UPDATES_FILE):
        with open(SENT_UPDATES_FILE, 'r') as file:
            return set(line.strip() for line in file)
    return set()

def save_sent_update(title):
    with open(SENT_UPDATES_FILE, 'a') as file:
        file.write(title + '\n')

def sanitize_filename(title):
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', title)

async def download_image(image_url, title):
    sanitized_title = sanitize_filename(title)
    file_path = f"{sanitized_title}.jpg"

    try:
        logging.info(f"Downloading image from {image_url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                response.raise_for_status()
                with open(file_path, 'wb') as file:
                    file.write(await response.read())
        logging.info(f"Downloaded image: {file_path}")
        return file_path
    except Exception as e:
        logging.error(f"Failed to download image: {e}")
        return None

# Fetch and send updates from RSS feed
async def fetch_and_send_updates():
    last_sent_timestamp = load_last_sent_timestamp()
    sent_updates = load_sent_updates()
    
    while True:
        try:
            logging.info("Fetching RSS feed...")
            feed = feedparser.parse(RSS_URL)

            new_updates_count = 0
            latest_entries = []

            for entry in feed.entries:
                try:
                    title = entry.title
                    guid = entry.guid if hasattr(entry, 'guid') else title
                    published = parser.parse(entry.pubDate) if hasattr(entry, 'pubDate') else None

                    if guid not in sent_updates:
                        latest_entries.append(entry)
                except Exception as entry_error:
                    logging.error(f"Error processing entry: {entry} - {entry_error}")
                    continue  # Skip this entry and proceed to the next one

            for entry in latest_entries:
                try:
                    title = entry.title
                    guid = entry.guid if hasattr(entry, 'guid') else title
                    published = parser.parse(entry.pubDate) if hasattr(entry, 'pubDate') else None

                    if published and (last_sent_timestamp is None or published > last_sent_timestamp):
                        last_sent_timestamp = max(last_sent_timestamp, published) if last_sent_timestamp else published
                        save_last_sent_timestamp(last_sent_timestamp)

                    youtube_link = entry.link if "youtube.com" in entry.link else None
                    image_url = entry.media_thumbnail[0]['url'] if 'media_thumbnail' in entry else entry.enclosure.url if 'enclosure' in entry else None

                    if image_url and image_url.endswith("/large.jpg"):
                        image_url = image_url[:-10]

                    logging.info(f"Using image URL: {image_url}")
                    image_path = await download_image(image_url, title)

                    if image_path:
                        caption = f"💫 {title}"
                        buttons = []
                        if youtube_link:
                            buttons.append([InlineKeyboardButton("Watch Trailer", url=youtube_link)])

                        try:
                            await app.send_photo(
                                chat_id=CHANNEL_ID,
                                photo=image_path,
                                caption=caption,
                                reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
                            )
                            logging.info(f"Sent image with title: {title}")
                        finally:
                            os.remove(image_path)

                        sent_updates.add(guid)
                        save_sent_update(guid)
                    else:
                        logging.warning(f"Image download failed for: {title}")

                    new_updates_count += 1

                except Exception as update_error:
                    logging.error(f"Error sending update for entry '{entry.title}': {update_error}")
                    continue  # Skip this update and proceed to the next one

            if new_updates_count > 0:
                logging.info(f"Sent {new_updates_count} updates.")
            else:
                logging.info("No new updates found.")

            await asyncio.sleep(600)

        except Exception as e:
            logging.error(f"An error occurred in the main loop: {e}")
            await asyncio.sleep(60)

# Start command handler
@app.on_message(filters.command("start"))
async def start_handler(client, message):
    logging.info(f"Start command received from {message.chat.id}")
    button = [[InlineKeyboardButton("Visit Channel", url="https://t.me/Anime_NewsLatest")]]
    await message.reply_text(
        "Welcome to the Anime News Bot! Updates will be sent to the channel.",
        reply_markup=InlineKeyboardMarkup(button)
    )

# Main execution
if __name__ == '__main__':
    logging.info("Bot is starting...")

    # Run the bot and RSS update loop
    app.start()
    try:
        asyncio.run(fetch_and_send_updates())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Shutting down bot.")
        app.stop()
