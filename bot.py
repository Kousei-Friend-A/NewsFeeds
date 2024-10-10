import os
import feedparser
import aiohttp
import logging
import asyncio
from telethon import TelegramClient, events, Button  # Import Button
import re
from dateutil import parser

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Directly set your configuration here
API_ID = 8143727
API_HASH = "e2e9b22c6522465b62d8445840a526b1"
BOT_TOKEN = "7735485169:AAEReRLDsc-GshqXOKVveRGtPHpjv13Lrj4"
CHANNEL_ID = '@Anime_NewsLibrary'
RSS_URL = "https://www.livechart.me/feeds/headlines"

# Path to the file storing the last sent update timestamp
LAST_SENT_TIMESTAMP_FILE = "last_sent_timestamp.txt"
SENT_UPDATES_FILE = "sent_updates.txt"

# Create a new Telethon client with API credentials
client = TelegramClient("my_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Load last sent timestamp from the file
def load_last_sent_timestamp():
    if os.path.exists(LAST_SENT_TIMESTAMP_FILE):
        with open(LAST_SENT_TIMESTAMP_FILE, 'r') as file:
            return parser.parse(file.read().strip())
    return None

# Save the last sent timestamp to the file
def save_last_sent_timestamp(timestamp):
    with open(LAST_SENT_TIMESTAMP_FILE, 'w') as file:
        file.write(timestamp.isoformat())

# Load sent updates from the file
def load_sent_updates():
    if os.path.exists(SENT_UPDATES_FILE):
        with open(SENT_UPDATES_FILE, 'r') as file:
            return set(line.strip() for line in file)
    return set()

# Save a new title to the file
def save_sent_update(title):
    with open(SENT_UPDATES_FILE, 'a') as file:
        file.write(title + '\n')

# Function to sanitize the filename
def sanitize_filename(title):
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', title)

# Download image function
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

# Function to fetch and send updates
async def fetch_and_send_updates():
    last_sent_timestamp = load_last_sent_timestamp()
    sent_updates = load_sent_updates()  # Load previously sent updates
    
    while True:
        try:
            logging.info("Fetching RSS feed...")
            feed = feedparser.parse(RSS_URL)

            new_updates_count = 0
            latest_entries = []

            for entry in feed.entries:
                # Log the entry for debugging
                logging.debug(f"Feed Entry: {entry}")

                # Get the publication date if available, else set to None
                published = parser.parse(entry.pubDate) if hasattr(entry, 'pubDate') else None
                title = entry.title
                guid = entry.guid if hasattr(entry, 'guid') else title  # Use GUID or title if GUID is missing

                # Add entry to the list to send if not already sent
                if guid not in sent_updates:
                    latest_entries.append(entry)

            for entry in latest_entries:
                title = entry.title
                guid = entry.guid if hasattr(entry, 'guid') else title
                published = parser.parse(entry.pubDate) if hasattr(entry, 'pubDate') else None

                # Send the entry if published date is valid
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
                    reply_markup = []
                    if youtube_link:
                        reply_markup.append(Button.url("Watch Trailer", youtube_link))  # Updated button creation

                    # Send the photo using Telethon
                    await client.send_file(
                        CHANNEL_ID,
                        image_path,
                        caption=caption,
                        buttons=reply_markup if reply_markup else None  # Fixed button handling
                    )
                    logging.info(f"Sent image with title: {title}")
                    os.remove(image_path)  # Cleanup the image after sending

                    # Save the sent update
                    sent_updates.add(guid)
                    save_sent_update(guid)  # Store the GUID or title of the sent update
                else:
                    logging.warning(f"Image download failed for: {title}")

                new_updates_count += 1

            if new_updates_count > 0:
                logging.info(f"Sent {new_updates_count} updates.")
            else:
                logging.info("No new updates found.")

            await asyncio.sleep(600)  # Wait before fetching again

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            await asyncio.sleep(60)

# Start command handler
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    logging.info(f"Start command received from {event.chat_id}")
    button = [Button.url("Visit Channel", "https://t.me/Anime_NewsFeeds")]  # Updated button creation
    await event.respond(
        "Welcome to the Anime Headlines Bot! Updates will be sent to the channel.",
        buttons=button  # Fixed button handling
    )

# Main execution
if __name__ == '__main__':
    logging.info("Bot is starting...")
    client.loop.run_until_complete(fetch_and_send_updates())  # Properly run the fetch loop
