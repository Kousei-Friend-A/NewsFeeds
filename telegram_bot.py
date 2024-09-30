import os
import feedparser
import aiohttp
import logging
import asyncio
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from collections import deque
from pyrogram.errors import FloodWait
import re

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Directly set your configuration here
API_ID = 12321125
API_HASH = "6a34b69aa63177ec36f8d9b24c296f40"
BOT_TOKEN = "6315185069:AAGeIwcUzw66keUM6o0Mtv9sytWQWH_WhMI"
CHANNEL_ID = 'Elvazo'
RSS_URL = "https://www.livechart.me/feeds/headlines"

# Create a new Pyrogram client with API credentials
app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Caching for sent updates
sent_updates = deque(maxlen=100)

# Function to sanitize the filename
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

async def download_youtube_video(youtube_link):
    try:
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'outtmpl': '%(title)s.%(ext)s',
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'quiet': True,
            'verbose': True,  # Enable verbose logging for debugging
        }

        logging.info(f"Downloading YouTube video from {youtube_link}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_link, download=True)
            video_path = f"{sanitize_filename(info['title'])}.mp4"
            if os.path.exists(video_path):
                logging.info(f"Downloaded YouTube video: {video_path}")
                return video_path
            else:
                logging.error("Video path does not exist after download.")
                return None
    except Exception as e:
        logging.error(f"Failed to download YouTube video: {e}")
        return None

async def fetch_and_send_updates():
    while True:
        try:
            logging.info("Fetching RSS feed...")
            feed = feedparser.parse(RSS_URL)

            new_updates_count = 0

            for entry in feed.entries:
                title = entry.title

                if title not in sent_updates:
                    sent_updates.append(title)
                    youtube_link = entry.link if "youtube.com" in entry.link else None

                    image_url = entry.media_thumbnail[0]['url'] if 'media_thumbnail' in entry else entry.enclosure.url if 'enclosure' in entry else None

                    if image_url and image_url.endswith("/large.jpg"):
                        image_url = image_url[:-10]

                    if youtube_link:
                        # Download the YouTube video
                        video_path = await download_youtube_video(youtube_link)
                        if video_path and os.path.exists(video_path):
                            caption = f"**{title}** 💫"  # Bold the title
                            await app.send_video(
                                chat_id=CHANNEL_ID,
                                video=video_path,
                                caption=caption
                            )
                            os.remove(video_path)  # Cleanup the video after sending
                            logging.info(f"Sent YouTube video with title: {title}")
                        else:
                            logging.error(f"Video path is invalid: {video_path}")
                    else:
                        logging.info(f"Using image URL: {image_url}")
                        image_path = await download_image(image_url, title)

                        if image_path:
                            caption = f"**{title}** 💫"  # Bold the title
                            await app.send_photo(
                                chat_id=CHANNEL_ID,
                                photo=image_path,
                                caption=caption
                            )
                            logging.info(f"Sent image with title: {title}")
                            os.remove(image_path)  # Cleanup the image after sending
                        else:
                            logging.warning(f"Image download failed for: {title}")

                    new_updates_count += 1

            if new_updates_count > 0:
                logging.info(f"Sent {new_updates_count} updates.")
            else:
                logging.info("No new updates found.")

            await asyncio.sleep(600)  # Wait before fetching again

        except FloodWait as e:
            logging.warning(f"Flood wait triggered. Waiting for {e.x} seconds.")
            await asyncio.sleep(e.x)
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
