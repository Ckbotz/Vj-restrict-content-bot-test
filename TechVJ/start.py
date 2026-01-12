# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os
import asyncio
import random
import pyrogram
import re
import subprocess
import time
import aiohttp
from pyrogram import Client, filters, enums
from pyrogram.errors import (
    FloodWait,
    UserIsBlocked,
    InputUserDeactivated,
    UserAlreadyParticipant,
    InviteHashExpired,
    UsernameNotOccupied
)
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from config import API_ID, API_HASH, ERROR_MESSAGE, LOGIN_SYSTEM, STRING_SESSION
from database.db import db
from TechVJ.strings import HELP_TXT
from bot import TechVJUser

# ========== CONFIGURATION SECTION ==========
# Add words to remove from filename (case-insensitive)
WORDS_TO_REMOVE = [
    "@ADL_DRAMA",
    "#ADL",
    "[MABLG]",
    "@DA_RIPS",
    "@Da_Rips",
    "DA_Rips",
    "ADL_DRAMA",
    "ADL",
    "MABLG",
    "[DnO]",
]

# Permanent thumbnail URL (leave empty string "" to disable)
PERMANENT_THUMBNAIL_URL = "https://i.ibb.co/nqVhZrzT/IMG-20251124-185914-275.jpg"

# Prefix and Suffix settings
FILE_PREFIX = os.environ.get("FILE_PREFIX", "").strip() or None
FILE_SUFFIX = os.environ.get("FILE_SUFFIX", "@DramaShip").strip() or None

# Metadata settings
METADATA_TITLE = os.environ.get("METADATA_TITLE", "{file_name}").strip() or None
METADATA_AUTHOR = os.environ.get("METADATA_AUTHOR", "@DramaShip").strip() or None
METADATA_ARTIST = os.environ.get("METADATA_ARTIST", "@DramaShip").strip() or None
METADATA_DESCRIPTION = os.environ.get("METADATA_DESCRIPTION", "uploaded by @Dramaship").strip() or None
METADATA_COMMENT = os.environ.get("METADATA_COMMENT", "@DramaShip").strip() or None

# Video/Audio/Subtitle Stream Title settings
METADATA_VIDEO_TITLE = os.environ.get("METADATA_VIDEO_TITLE", "@DramaShip").strip() or None
METADATA_AUDIO_TITLE = os.environ.get("METADATA_AUDIO_TITLE", "@DramaShip").strip() or None
METADATA_SUBTITLE_TITLE = os.environ.get("METADATA_SUBTITLE_TITLE", "").strip() or None
# =========================================


# Custom exception for cancellation
class ProcessCancelled(Exception):
    """Custom exception for user-initiated cancellation"""
    pass


class batch_temp(object):
    IS_BATCH = {}
    CUSTOM_SLEEP = {}
    CANCEL_TASKS = {}
    ACTIVE_SESSIONS = {}
    DOWNLOAD_TASKS = {}  # Store download task references
    PROGRESS_MESSAGES = {}  # Store progress message IDs


def clean_filename(filename):
    """Remove unwanted words from filename"""
    if not filename:
        return filename
    
    name_parts = filename.rsplit('.', 1)
    name = name_parts[0]
    ext = name_parts[1] if len(name_parts) > 1 else ""
    
    for word in WORDS_TO_REMOVE:
        name = re.sub(re.escape(word), '', name, flags=re.IGNORECASE)
    
    name = re.sub(r'\s+', ' ', name).strip()
    name = re.sub(r'[_\-\s]+', ' ', name).strip()
    
    return f"{name}.{ext}" if ext else name


def apply_prefix_suffix(filename):
    """Apply prefix and suffix to filename"""
    if not filename:
        return filename
    
    name_parts = filename.rsplit('.', 1)
    if len(name_parts) == 2:
        name, ext = name_parts
    else:
        name = filename
        ext = ""
    
    if FILE_PREFIX:
        name = f"{FILE_PREFIX}.{name}"
    
    if FILE_SUFFIX:
        name = f"{name}.{FILE_SUFFIX}"
    
    if ext:
        return f"{name}.{ext}"
    return name


def format_bytes(size):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def format_time(seconds):
    """Format seconds into readable time"""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds / 60)}m {int(seconds % 60)}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"


async def download_thumbnail(client, url):
    """Download thumbnail from URL"""
    if not url:
        return None
    
    try:
        os.makedirs("temp_thumbs", exist_ok=True)
        thumb_path = f"temp_thumbs/thumb_{random.randint(1000, 9999)}.jpg"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    with open(thumb_path, 'wb') as f:
                        f.write(await response.read())
                    return thumb_path
    except Exception as e:
        print(f"Error downloading thumbnail: {e}")
    
    return None


async def add_metadata_with_ffmpeg(input_file, final_filename):
    """Add metadata to video/audio files using ffmpeg while preserving all streams and adding stream titles
    
    If metadata variables are blank/None, original metadata is preserved.
    If metadata variables are set, they override original metadata.
    """
    
    if not any([METADATA_TITLE, METADATA_AUTHOR, METADATA_ARTIST, METADATA_DESCRIPTION, 
                METADATA_COMMENT, METADATA_VIDEO_TITLE, METADATA_AUDIO_TITLE, METADATA_SUBTITLE_TITLE]):
        return input_file, False
    
    ext = input_file.rsplit('.', 1)[-1].lower()
    if ext not in ['mp4', 'mkv', 'avi', 'mov', 'flv', 'wmv', 'webm', 'mp3', 'flac', 'wav', 'm4a', 'aac', 'ogg']:
        return input_file, False
    
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("FFmpeg/FFprobe not found. Skipping metadata addition.")
        return input_file, False
    
    try:
        dir_name = os.path.dirname(input_file)
        output_file = os.path.join(dir_name, f"temp_meta_{random.randint(1000, 9999)}.{ext}")
        
        # First, probe the file to get stream information
        probe_cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_streams', input_file
        ]
        
        try:
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            import json
            probe_data = json.loads(probe_result.stdout)
            streams = probe_data.get('streams', [])
        except:
            streams = []
        
        cmd = [
            'ffmpeg', '-i', input_file,
            '-map', '0',
            '-c', 'copy',
            '-map_metadata', '0'  # Preserve all original metadata by default
        ]
        
        # Add/override global metadata only if set
        if METADATA_TITLE:
            title = METADATA_TITLE.format(file_name=final_filename)
            cmd.extend(['-metadata', f'title={title}'])
        if METADATA_AUTHOR:
            author = METADATA_AUTHOR.format(file_name=final_filename)
            cmd.extend(['-metadata', f'author={author}'])
        if METADATA_ARTIST:
            artist = METADATA_ARTIST.format(file_name=final_filename)
            cmd.extend(['-metadata', f'artist={artist}'])
        if METADATA_DESCRIPTION:
            description = METADATA_DESCRIPTION.format(file_name=final_filename)
            cmd.extend(['-metadata', f'description={description}'])
        if METADATA_COMMENT:
            comment = METADATA_COMMENT.format(file_name=final_filename)
            cmd.extend(['-metadata', f'comment={comment}'])
        
        # Add stream-specific metadata only if set (preserves original if not set)
        for idx, stream in enumerate(streams):
            codec_type = stream.get('codec_type', '').lower()
            
            if codec_type == 'video' and METADATA_VIDEO_TITLE:
                video_title = METADATA_VIDEO_TITLE.format(file_name=final_filename)
                # Count video streams before this one
                video_idx = sum(1 for s in streams[:idx] if s.get('codec_type') == 'video')
                cmd.extend([f'-metadata:s:v:{video_idx}', f'title={video_title}'])
            
            elif codec_type == 'audio' and METADATA_AUDIO_TITLE:
                audio_title = METADATA_AUDIO_TITLE.format(file_name=final_filename)
                # Count audio streams before this one
                audio_idx = sum(1 for s in streams[:idx] if s.get('codec_type') == 'audio')
                cmd.extend([f'-metadata:s:a:{audio_idx}', f'title={audio_title}'])
            
            elif codec_type == 'subtitle' and METADATA_SUBTITLE_TITLE:
                subtitle_title = METADATA_SUBTITLE_TITLE.format(file_name=final_filename)
                # Count subtitle streams before this one
                subtitle_idx = sum(1 for s in streams[:idx] if s.get('codec_type') == 'subtitle')
                cmd.extend([f'-metadata:s:s:{subtitle_idx}', f'title={subtitle_title}'])
        
        cmd.extend(['-y', output_file])
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        process.wait()
        
        if process.returncode == 0 and os.path.exists(output_file):
            os.remove(input_file)
            os.rename(output_file, input_file)
            return input_file, True
        else:
            if os.path.exists(output_file):
                os.remove(output_file)
            raise Exception("FFmpeg failed")
            
    except Exception as e:
        print(f"Metadata error: {e}")
        if 'output_file' in locals() and os.path.exists(output_file):
            try:
                os.remove(output_file)
            except:
                pass
        return input_file, False


async def smart_sleep(user_id):
    """Intelligent sleep with randomization and cancel check"""
    base_sleep = batch_temp.CUSTOM_SLEEP.get(user_id, [3, 5, 7, 10])
    sleep_time = random.choice(base_sleep)
    jitter = random.uniform(-0.2, 0.2) * sleep_time
    final_sleep = sleep_time + jitter
    
    # Check every 0.2 seconds for more responsive cancellation
    sleep_chunks = int(final_sleep / 0.2)
    for _ in range(sleep_chunks):
        if batch_temp.CANCEL_TASKS.get(user_id, False):
            raise ProcessCancelled("Process cancelled by user")
        await asyncio.sleep(0.2)


async def get_user_session(user_id):
    """Get or create user session and ensure it's started"""
    if LOGIN_SYSTEM:
        user_data = await db.get_session(user_id)
        if user_data is None:
            return None, "**For Downloading Restricted Content You Have To /login First.**"
        
        if user_id in batch_temp.ACTIVE_SESSIONS:
            try:
                await batch_temp.ACTIVE_SESSIONS[user_id].get_me()
                return batch_temp.ACTIVE_SESSIONS[user_id], None
            except:
                try:
                    await batch_temp.ACTIVE_SESSIONS[user_id].stop()
                except:
                    pass
                del batch_temp.ACTIVE_SESSIONS[user_id]
        
        try:
            acc = Client(
                f"session_{user_id}",
                session_string=user_data,
                api_hash=API_HASH,
                api_id=API_ID,
            )
            await acc.start()
            batch_temp.ACTIVE_SESSIONS[user_id] = acc
            return acc, None
        except Exception as e:
            return None, "**Your Login Session Expired. So /logout First Then Login Again By - /login**"
    else:
        if TechVJUser is None:
            return None, "**String Session is not Set**"
        return TechVJUser, None


async def stop_user_session(user_id):
    """Stop and cleanup user session after task completion"""
    if user_id in batch_temp.ACTIVE_SESSIONS:
        try:
            await batch_temp.ACTIVE_SESSIONS[user_id].stop()
            print(f"✅ Session stopped for user {user_id}")
        except Exception as e:
            print(f"Error stopping session for user {user_id}: {e}")
        finally:
            del batch_temp.ACTIVE_SESSIONS[user_id]


UPDATE_DELAY = 7
SPINNER = ["**○**", "**◐**", "**●**", "**◑**", "**○**", "**◑**"]
last_edit_time = {}
spinner_index = {}


async def progress_callback(current, total, message, mode, start_time):
    """Enhanced progress bar with cancel button and frequent cancel checks"""
    global last_edit_time, spinner_index

    if message is None:
        return

    msg_id = message.id

    if msg_id not in spinner_index:
        spinner_index[msg_id] = 0

    now = time.time()
    
    user_id = getattr(getattr(message, "from_user", None), "id", None)
    if not user_id:
        user_id = getattr(message, "chat", None)
        if user_id:
            user_id = user_id.id

    # Check for cancellation MORE FREQUENTLY - raise custom exception
    if user_id and batch_temp.CANCEL_TASKS.get(user_id, False):
        raise ProcessCancelled("Process cancelled by user")

    if msg_id in last_edit_time:
        if now - last_edit_time[msg_id] < UPDATE_DELAY:
            return
    last_edit_time[msg_id] = now

    diff = now - start_time
    percentage = (current / total) * 100 if total else 0
    speed = current / diff if diff > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0

    filled_len = int(percentage // 5)
    bar = "**▰**" * filled_len + "**▱**" * (20 - filled_len)

    spinner = SPINNER[spinner_index[msg_id] % len(SPINNER)]
    spinner_index[msg_id] += 1

    status_emoji = "📥" if mode == "download" else "📤"
    status_text = "Downloading" if mode == "download" else "Uploading"

    text = (
        f"{spinner} **{status_emoji} {status_text}**\n\n"
        f"**Progress:** {percentage:.1f}%\n"
        f"`[{bar}]`\n\n"
        f"**Speed:** {format_bytes(speed)}/s\n"
        f"**Processed:** {format_bytes(current)} / {format_bytes(total)}\n"
        f"**ETA:** {format_time(eta)}"
    )

    # Add cancel button
    cancel_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛑 Cancel Process", callback_data=f"cancel_{user_id}")]
    ])

    try:
        await message.edit_text(text, reply_markup=cancel_button)
        await asyncio.sleep(0.05)
    except:
        pass


@Client.on_callback_query(filters.regex(r"^cancel_"))
async def cancel_callback(client: Client, callback_query: CallbackQuery):
    """Handle cancel button press"""
    data = callback_query.data
    user_id = int(data.split("_")[1])
    
    if callback_query.from_user.id != user_id:
        await callback_query.answer("⚠️ This is not your process!", show_alert=True)
        return
    
    batch_temp.CANCEL_TASKS[user_id] = True
    batch_temp.IS_BATCH[user_id] = True
    
    await callback_query.answer("🛑 Cancelling process...", show_alert=True)
    
    try:
        await callback_query.message.edit_text(
            "**🛑 CANCELLATION IN PROGRESS**\n\n"
            "⚠️ Stopping current operation...\n"
            "⚠️ Cleaning up files...\n"
            "⚠️ Session will be terminated..."
        )
    except:
        pass


@Client.on_message(filters.command(["start"]))
async def send_start(client: Client, message: Message):
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)

    buttons = [
        [InlineKeyboardButton("❣️ Developer", url="https://t.me/kingvj01")],
        [
            InlineKeyboardButton("🔍 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ", url="https://t.me/vj_bot_disscussion"),
            InlineKeyboardButton("🤖 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ", url="https://t.me/vj_botz"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await client.send_message(
        chat_id=message.chat.id,
        text=(
            f"<b>👋 Hi {message.from_user.mention}, I am Save Restricted Content Bot. "
            f"I can send you restricted content by its post link.\n\n"
            f"For downloading restricted content /login first.\n\n"
            f"Know how to use bot by - /help</b>"
        ),
        reply_markup=reply_markup,
        reply_to_message_id=message.id,
    )


@Client.on_message(filters.command(["help"]))
async def send_help(client: Client, message: Message):
    help_text = f"{HELP_TXT}\n\n**🕐 Custom Sleep Settings:**\n" \
                f"Use `/setsleep` command to set custom delays between batch downloads.\n" \
                f"Example: `/setsleep 3 5 7 10` (bot will randomly pick from these values)\n\n" \
                f"Use `/getsleep` to see your current sleep settings.\n\n" \
                f"**🛑 Cancel Command:**\n" \
                f"Use `/cancel` to immediately stop any ongoing batch process.\n" \
                f"You can also click the 'Cancel' button during download/upload.\n\n" \
                f"**💤 Session Management:**\n" \
                f"Your session automatically goes to sleep after task completion to save resources.\n\n" \
                f"**📝 File Customization:**\n" \
                f"• Files are auto-cleaned (removes keywords)\n" \
                f"• Prefix/Suffix added automatically\n" \
                f"• Metadata embedded in videos/audio\n" \
                f"• Stream titles (video/audio/subtitle) added\n" \
                f"• All subtitles & audio tracks preserved"
    await client.send_message(chat_id=message.chat.id, text=help_text)


@Client.on_message(filters.command(["setsleep"]))
async def set_sleep(client: Client, message: Message):
    try:
        parts = message.text.split()[1:]
        if not parts:
            await message.reply(
                "**Usage:** `/setsleep 3 5 7 10`\n\n"
                "Provide space-separated sleep values in seconds.\n"
                "Bot will randomly pick one value for each download to avoid detection.\n\n"
                "**Allowed range:** 1-1000 seconds\n"
                "**Example:** `/setsleep 3 5 7 10 12 15`"
            )
            return
        
        sleep_values = [int(x) for x in parts if x.isdigit() and 1 <= int(x) <= 1000]
        
        if not sleep_values:
            await message.reply("❌ Please provide valid sleep values between 1-1000 seconds!")
            return
        
        batch_temp.CUSTOM_SLEEP[message.from_user.id] = sleep_values
        await message.reply(
            f"✅ **Sleep values set successfully!**\n\n"
            f"Values: `{', '.join(map(str, sleep_values))}` seconds\n"
            f"Bot will randomly pick one value between downloads.\n\n"
            f"💡 **Tip:** More varied values = better anti-detection!"
        )
    except ValueError:
        await message.reply("❌ Please provide valid numeric values only!")


@Client.on_message(filters.command(["getsleep"]))
async def get_sleep(client: Client, message: Message):
    sleep_values = batch_temp.CUSTOM_SLEEP.get(message.from_user.id, [3, 5, 7, 10])
    await message.reply(
        f"**⏱️ Current Sleep Settings:**\n\n"
        f"Values: `{', '.join(map(str, sleep_values))}` seconds\n"
        f"Random selection with ±20% jitter for natural behavior.\n\n"
        f"Use `/setsleep` to change these values."
    )


@Client.on_message(filters.command(["cancel"]))
async def send_cancel(client: Client, message: Message):
    user_id = message.from_user.id
    
    if user_id not in batch_temp.IS_BATCH or batch_temp.IS_BATCH.get(user_id, True) is True:
        await client.send_message(
            chat_id=message.chat.id, 
            text="**❌ No Active Batch Process To Cancel.**",
            reply_to_message_id=message.id
        )
        return
    
    batch_temp.CANCEL_TASKS[user_id] = True
    batch_temp.IS_BATCH[user_id] = True
    
    # Cancel active download task if exists
    if user_id in batch_temp.DOWNLOAD_TASKS:
        try:
            batch_temp.DOWNLOAD_TASKS[user_id].cancel()
        except:
            pass
    
    await client.send_message(
        chat_id=message.chat.id, 
        text="**🛑 CANCELLING ALL PROCESSES IMMEDIATELY!**\n\n"
             "⚠️ Stopping current download/upload...\n"
             "⚠️ Cleaning up temporary files...\n"
             "⚠️ Session will be terminated...",
        reply_to_message_id=message.id
    )
    
    # Force stop session immediately
    await stop_user_session(user_id)


@Client.on_message(filters.text & filters.private)
async def save(client: Client, message: Message):
    if ("https://t.me/+" in message.text or "https://t.me/joinchat/" in message.text) and LOGIN_SYSTEM is False:
        if TechVJUser is None:
            await client.send_message(
                message.chat.id,
                "**String Session is not Set**",
                reply_to_message_id=message.id,
            )
            return

        try:
            try:
                await TechVJUser.join_chat(message.text)
            except Exception as e:
                await client.send_message(
                    message.chat.id,
                    f"**Error** : __{e}__",
                    reply_to_message_id=message.id,
                )
                return

            await client.send_message(
                message.chat.id,
                "**Chat Joined**",
                reply_to_message_id=message.id,
            )

        except UserAlreadyParticipant:
            await client.send_message(
                message.chat.id,
                "**Chat already Joined**",
                reply_to_message_id=message.id,
            )

        except InviteHashExpired:
            await client.send_message(
                message.chat.id,
                "**Invalid Link**",
                reply_to_message_id=message.id,
            )

        return

    if "https://t.me/" in message.text:
        user_id = message.from_user.id
        
        if batch_temp.IS_BATCH.get(user_id) is False:
            return await message.reply_text(
                "**⚠️ One Task Is Already Processing!**\n\n"
                "Please wait for it to complete or use /cancel to stop it."
            )

        datas = message.text.split("/")
        temp = datas[-1].replace("?single", "").split("-")
        fromID = int(temp[0].strip())

        try:
            toID = int(temp[1].strip())
        except:
            toID = fromID

        batch_temp.CANCEL_TASKS[user_id] = False
        batch_temp.IS_BATCH[user_id] = False
        
        total_items = toID - fromID + 1
        completed = 0

        acc, error_msg = await get_user_session(user_id)
        if acc is None:
            await message.reply(error_msg)
            batch_temp.IS_BATCH[user_id] = True
            batch_temp.CANCEL_TASKS[user_id] = False
            return

        try:
            for msgid in range(fromID, toID + 1):
                # Check cancel flag at start of each iteration
                if batch_temp.CANCEL_TASKS.get(user_id, False):
                    await client.send_message(
                        message.chat.id,
                        f"**🛑 Batch Process Cancelled!**\n\n"
                        f"✅ Completed: {completed}/{total_items} items\n"
                        f"❌ Cancelled at: {msgid}/{toID}\n"
                        f"💤 Session terminated.",
                        reply_to_message_id=message.id
                    )
                    break

                if "https://t.me/c/" in message.text:
                    chatid = int("-100" + datas[4])
                    try:
                        success = await handle_private(client, acc, message, chatid, msgid)
                        if success:
                            completed += 1
                    except ProcessCancelled:
                        break
                    except Exception as e:
                        if ERROR_MESSAGE:
                            await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)

                elif "https://t.me/b/" in message.text:
                    username = datas[4]
                    try:
                        success = await handle_private(client, acc, message, username, msgid)
                        if success:
                            completed += 1
                    except ProcessCancelled:
                        break
                    except Exception as e:
                        if ERROR_MESSAGE:
                            await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)

                else:
                    username = datas[3]
                    try:
                        msg = await client.get_messages(username, msgid)
                    except UsernameNotOccupied:
                        await client.send_message(
                            message.chat.id,
                            "The username is not occupied by anyone",
                            reply_to_message_id=message.id,
                        )
                        break

                    try:
                        await client.copy_message(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
                        completed += 1
                    except:
                        try:
                            success = await handle_private(client, acc, message, username, msgid)
                            if success:
                                completed += 1
                        except ProcessCancelled:
                            break
                        except Exception as e:
                            if ERROR_MESSAGE:
                                await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)

                # Check cancel again before sleep
                if batch_temp.CANCEL_TASKS.get(user_id, False):
                    await client.send_message(
                        message.chat.id,
                        f"**🛑 Batch Process Cancelled!**\n\n"
                        f"✅ Completed: {completed}/{total_items} items\n"
                        f"💤 Session terminated.",
                        reply_to_message_id=message.id
                    )
                    break

                if msgid < toID:
                    try:
                        await smart_sleep(user_id)
                    except ProcessCancelled:
                        await client.send_message(
                            message.chat.id,
                            f"**🛑 Process Cancelled During Sleep!**\n\n"
                            f"✅ Completed: {completed}/{total_items} items",
                            reply_to_message_id=message.id
                        )
                        break
                    
                if completed % 5 == 0 and completed < total_items and completed > 0:
                    try:
                        await client.send_message(
                            message.chat.id,
                            f"📊 Progress: {completed}/{total_items} completed...",
                            reply_to_message_id=message.id
                        )
                    except:
                        pass

        except ProcessCancelled:
            await client.send_message(
                message.chat.id,
                f"**🛑 Batch Process Cancelled!**\n\n"
                f"✅ Completed: {completed}/{total_items} items\n"
                f"💤 Session terminated.",
                reply_to_message_id=message.id
            )
        except Exception as e:
            print(f"Error in batch process: {e}")
        finally:
            batch_temp.IS_BATCH[user_id] = True
            batch_temp.CANCEL_TASKS[user_id] = False
            
            # Clean up download task reference
            if user_id in batch_temp.DOWNLOAD_TASKS:
                del batch_temp.DOWNLOAD_TASKS[user_id]
            
            # Force stop session
            await stop_user_session(user_id)
            
            if completed > 0 and not batch_temp.CANCEL_TASKS.get(user_id, False):
                await client.send_message(
                    message.chat.id,
                    f"✅ **Batch Complete!**\n\n"
                    f"Processed: {completed}/{total_items} items\n"
                    f"💤 Session terminated - will restart on next task",
                    reply_to_message_id=message.id
                )


async def handle_private(client: Client, acc, message: Message, chatid: int, msgid: int):
    user_id = message.from_user.id
    
    # Early cancel check
    if batch_temp.CANCEL_TASKS.get(user_id, False):
        raise ProcessCancelled("Process cancelled by user")
    
    msg: Message = await acc.get_messages(chatid, msgid)
    if msg.empty:
        return False

    msg_type = get_message_type(msg)
    if not msg_type:
        return False

    chat = message.chat.id
    
    # Check cancel again
    if batch_temp.CANCEL_TASKS.get(user_id, False):
        raise ProcessCancelled("Process cancelled by user")

    if msg_type == "Text":
        try:
            await client.send_message(
                chat,
                msg.text,
                entities=msg.entities,
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML,
            )
            return True
        except Exception as e:
            if ERROR_MESSAGE:
                await client.send_message(
                    message.chat.id,
                    f"Error: {e}",
                    reply_to_message_id=message.id,
                    parse_mode=enums.ParseMode.HTML,
                )
            return False

    smsg = await client.send_message(message.chat.id, "**📥 Downloading...**", reply_to_message_id=message.id)
    
    # Store progress message for potential cleanup
    batch_temp.PROGRESS_MESSAGES[user_id] = smsg.id
    
    file = None
    start_time = time.time()
    
    try:
        # Final cancel check before download
        if batch_temp.CANCEL_TASKS.get(user_id, False):
            try:
                await smsg.delete()
            except:
                pass
            raise ProcessCancelled("Process cancelled by user")
        
        # Create download task and store reference for cancellation
        download_task = asyncio.create_task(
            acc.download_media(
                msg, 
                progress=progress_callback,
                progress_args=(smsg, "download", start_time)
            )
        )
        batch_temp.DOWNLOAD_TASKS[user_id] = download_task
        
        # Wait for download with cancel checking
        try:
            file = await download_task
        except asyncio.CancelledError:
            raise ProcessCancelled("Process cancelled by user")
        finally:
            if user_id in batch_temp.DOWNLOAD_TASKS:
                del batch_temp.DOWNLOAD_TASKS[user_id]
        
        # Check cancel after download
        if batch_temp.CANCEL_TASKS.get(user_id, False):
            if file and os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    pass
            try:
                await smsg.delete()
            except:
                pass
            raise ProcessCancelled("Process cancelled by user")
        
        if file and os.path.exists(file):
            dir_name = os.path.dirname(file)
            old_filename = os.path.basename(file)
            
            cleaned_filename = clean_filename(old_filename)
            final_filename = apply_prefix_suffix(cleaned_filename)
            
            new_file_path = os.path.join(dir_name, final_filename)
            
            if old_filename != final_filename:
                os.rename(file, new_file_path)
                file = new_file_path
            
            # Check cancel before metadata processing
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                if file and os.path.exists(file):
                    try:
                        os.remove(file)
                    except:
                        pass
                try:
                    await smsg.delete()
                except:
                    pass
                raise ProcessCancelled("Process cancelled by user")
            
            file, metadata_added = await add_metadata_with_ffmpeg(file, final_filename)
        
    except ProcessCancelled:
        if file and os.path.exists(file):
            try:
                os.remove(file)
            except:
                pass
        try:
            await smsg.delete()
        except:
            pass
        raise
    except Exception as e:
        if file and os.path.exists(file):
            try:
                os.remove(file)
            except:
                pass
        if ERROR_MESSAGE:
            await client.send_message(
                message.chat.id,
                f"Error: {e}",
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML,
            )
        try:
            await smsg.delete()
        except:
            pass
        return False

    # Check cancel before upload
    if batch_temp.CANCEL_TASKS.get(user_id, False):
        if file and os.path.exists(file):
            try:
                os.remove(file)
            except:
                pass
        try:
            await smsg.delete()
        except:
            pass
        raise ProcessCancelled("Process cancelled by user")

    try:
        await smsg.edit("**📤 Uploading...**")
    except:
        pass
    
    caption = msg.caption if msg.caption else None
    upload_success = False
    
    perm_thumb = None
    if PERMANENT_THUMBNAIL_URL:
        perm_thumb = await download_thumbnail(client, PERMANENT_THUMBNAIL_URL)

    start_time = time.time()
    
    try:
        if msg_type == "Document":
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                raise ProcessCancelled("Process cancelled by user")
            
            if perm_thumb:
                ph_path = perm_thumb
            else:
                try:
                    ph_path = await acc.download_media(msg.document.thumbs[0].file_id)
                except:
                    ph_path = None
            
            await client.send_document(
                chat,
                file,
                thumb=ph_path,
                caption=caption,
                file_name=os.path.basename(file),
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML,
                progress=progress_callback,
                progress_args=(smsg, "upload", start_time),
            )
            upload_success = True
            
            if ph_path and ph_path != perm_thumb and os.path.exists(ph_path):
                os.remove(ph_path)

        elif msg_type == "Video":
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                raise ProcessCancelled("Process cancelled by user")
            
            if perm_thumb:
                ph_path = perm_thumb
            else:
                try:
                    ph_path = await acc.download_media(msg.video.thumbs[0].file_id)
                except:
                    ph_path = None
            
            await client.send_video(
                chat,
                file,
                duration=msg.video.duration,
                width=msg.video.width,
                height=msg.video.height,
                thumb=ph_path,
                caption=caption,
                file_name=os.path.basename(file),
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML,
                progress=progress_callback,
                progress_args=(smsg, "upload", start_time),
            )
            upload_success = True
            
            if ph_path and ph_path != perm_thumb and os.path.exists(ph_path):
                os.remove(ph_path)

        elif msg_type == "Animation":
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                raise ProcessCancelled("Process cancelled by user")
            
            await client.send_animation(
                chat, 
                file, 
                reply_to_message_id=message.id, 
                parse_mode=enums.ParseMode.HTML
            )
            upload_success = True

        elif msg_type == "Sticker":
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                raise ProcessCancelled("Process cancelled by user")
            
            await client.send_sticker(
                chat, 
                file, 
                reply_to_message_id=message.id, 
                parse_mode=enums.ParseMode.HTML
            )
            upload_success = True

        elif msg_type == "Voice":
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                raise ProcessCancelled("Process cancelled by user")
            
            await client.send_voice(
                chat,
                file,
                caption=caption,
                caption_entities=msg.caption_entities,
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML,
                progress=progress_callback,
                progress_args=(smsg, "upload", start_time),
            )
            upload_success = True

        elif msg_type == "Audio":
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                raise ProcessCancelled("Process cancelled by user")
            
            if perm_thumb:
                ph_path = perm_thumb
            else:
                try:
                    ph_path = await acc.download_media(msg.audio.thumbs[0].file_id)
                except:
                    ph_path = None
            
            await client.send_audio(
                chat,
                file,
                thumb=ph_path,
                caption=caption,
                file_name=os.path.basename(file),
                reply_to_message_id=message.id,
                parse_mode=enums.ParseMode.HTML,
                progress=progress_callback,
                progress_args=(smsg, "upload", start_time),
            )
            upload_success = True
            
            if ph_path and ph_path != perm_thumb and os.path.exists(ph_path):
                os.remove(ph_path)

        elif msg_type == "Photo":
            if batch_temp.CANCEL_TASKS.get(user_id, False):
                raise ProcessCancelled("Process cancelled by user")
            
            await client.send_photo(
                chat, 
                file, 
                caption=caption, 
                reply_to_message_id=message.id, 
                parse_mode=enums.ParseMode.HTML
            )
            upload_success = True

    except ProcessCancelled:
        raise
    except Exception as e:
        if ERROR_MESSAGE:
            await client.send_message(
                message.chat.id, 
                f"Error: {e}", 
                reply_to_message_id=message.id, 
                parse_mode=enums.ParseMode.HTML
            )

    # Cleanup
    if file and os.path.exists(file):
        try:
            os.remove(file)
        except:
            pass
    
    if perm_thumb and os.path.exists(perm_thumb):
        try:
            os.remove(perm_thumb)
        except:
            pass
    
    try:
        await client.delete_messages(message.chat.id, [smsg.id])
    except:
        pass
    
    # Remove from progress messages
    if user_id in batch_temp.PROGRESS_MESSAGES:
        del batch_temp.PROGRESS_MESSAGES[user_id]

    return upload_success


def get_message_type(msg: pyrogram.types.messages_and_media.message.Message):
    try:
        msg.document.file_id
        return "Document"
    except:
        pass
    try:
        msg.video.file_id
        return "Video"
    except:
        pass
    try:
        msg.animation.file_id
        return "Animation"
    except:
        pass
    try:
        msg.sticker.file_id
        return "Sticker"
    except:
        pass
    try:
        msg.voice.file_id
        return "Voice"
    except:
        pass
    try:
        msg.audio.file_id
        return "Audio"
    except:
        pass
    try:
        msg.photo.file_id
        return "Photo"
    except:
        pass
    try:
        msg.text
        return "Text"
    except:
        pass
