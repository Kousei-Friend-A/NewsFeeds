import os
import feedparser
import requests
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext
from datetime import datetime
from dateutil import parser

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Directly set your configuration here
BOT_TOKEN = "7735485169:AAEReRLDsc-GshqXOKVveRGtPHpjv13Lrj4"
CHANNEL_ID = '@Anime_NewsFeeds'
RSS_URL = "https://www.livechart.me/feeds/headlines"

# Path to the file storing the last sent update timestamp
LAST_SENT_TIMESTAMP_FILE = "last_sent_timestamp.txt"
SENT_UPDATES_FILE = "sent_updates.txt"

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

# Function to download image
def download_image(image_url, title):
    sanitized_title = sanitize_filename(title)
    file_path = f"{sanitized_title}.jpg"
    
    try:
        logging.info(f"Downloading image from {image_url}")
        response = requests.get(image_url)
        response.raise_for_status()
        with open(file_path, 'wb') as file:
            file.write(response.content)
        logging.info(f"Downloaded image: {file_path}")
        return file_path
    except Exception as e:
        logging.error(f"Failed to download image: {e}")
        return None

# Function to fetch and send updates
def fetch_and_send_updates(context: CallbackContext):
    last_sent_timestamp = load_last_sent_timestamp()
    sent_updates = load_sent_updates()  # Load previously sent updates

    logging.info("Fetching RSS feed...")
    feed = feedparser.parse(RSS_URL)

    new_updates_count = 0
    latest_entries = []

    for entry in feed.entries:
        # Log the entry for debugging
        logging.debug(f"Feed Entry: {entry}")

        # Get the publication date if available, else set to None
        published = parser.parse(entry.published) if hasattr(entry, 'published') else None
        title = entry.title
        guid = entry.id if hasattr(entry, 'id') else title  # Use GUID or title if GUID is missing

        # Add entry to the list to send if not already sent
        if guid not in sent_updates:
            latest_entries.append(entry)

    for entry in latest_entries:
        title = entry.title
        guid = entry.id if hasattr(entry, 'id') else title
        published = parser.parse(entry.published) if hasattr(entry, 'published') else None

        # Send the entry
        if published and (last_sent_timestamp is None or published > last_sent_timestamp):
            last_sent_timestamp = max(last_sent_timestamp, published) if last_sent_timestamp else published
            save_last_sent_timestamp(last_sent_timestamp)

        youtube_link = entry.link if "youtube.com" in entry.link else None
        image_url = entry.media_thumbnail[0]['url'] if 'media_thumbnail' in entry else None

        if image_url and image_url.endswith("/large.jpg"):
            image_url = image_url[:-10]

        logging.info(f"Using image URL: {image_url}")
        image_path = download_image(image_url, title)

        if image_path:
            caption = f"💫 {title}"
            reply_markup = []
            if youtube_link:
                reply_markup.append([InlineKeyboardButton("Watch Trailer", url=youtube_link)])

            # Send the image with caption to the channel
            context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=open(image_path, 'rb'),
                caption=caption,
                reply_markup=InlineKeyboardMarkup(reply_markup) if reply_markup else None
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

# Start command handler
def start(update: Update, context: CallbackContext):
    logging.info(f"Start command received from {update.message.chat_id}")
    button = InlineKeyboardMarkup([[InlineKeyboardButton("Visit Channel", url="https://t.me/Anime_NewsFeeds")]])
    update.message.reply_text(
        "Welcome to the Anime Headlines Bot! Updates will be sent to the channel.",
        reply_markup=button
    )

def main():
    # Create the Updater and pass it your bot's token
    updater = Updater(token=BOT_TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Register command handler
    dp.add_handler(CommandHandler("start", start))

    # Job to fetch and send updates every 10 minutes
    job_queue = updater.job_queue
    job_queue.run_repeating(fetch_and_send_updates, interval=600, first=0)

    # Start the Bot
    updater.start_polling()

    logging.info("Bot started...")

    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main()
