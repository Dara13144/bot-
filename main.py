"""
Telegram Bot: Voice to Khmer Voice Converter
FIXED for Python 3.14+ - Full working system
"""

import os
import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
import requests

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Speech to Text (offline)
import whisper

# Text to Speech (Khmer)
from gtts import gTTS

# ================= CONFIGURATION =================
# ⚠️ REPLACE WITH YOUR BOT TOKEN
BOT_TOKEN = "8824304522:AAEmGYkq0xYWZWs4u1QnwUWkfHlnA_ACejs"

# Create necessary folders
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load Whisper model
logger.info("Loading Whisper model...")
try:
    whisper_model = whisper.load_model("base")  # Using "base" for better compatibility
    logger.info("Whisper model loaded!")
except Exception as e:
    logger.error(f"Error loading Whisper: {e}")
    whisper_model = None

# ============== AUDIO PROCESSING FUNCTIONS (No pydub) ==============
def convert_audio_ffmpeg(input_path, output_path, output_format="wav"):
    """Convert audio using ffmpeg directly (no pydub)"""
    try:
        cmd = ["ffmpeg", "-i", input_path, "-y", output_path]
        if output_format == "ogg":
            cmd = ["ffmpeg", "-i", input_path, "-c:a", "libopus", "-y", output_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"Converted: {input_path} -> {output_path}")
            return True
        else:
            logger.error(f"FFmpeg error: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Conversion error: {e}")
        return False

def get_audio_duration_ffmpeg(file_path):
    """Get audio duration using ffmpeg"""
    try:
        cmd = ["ffmpeg", "-i", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        # Parse duration from stderr
        for line in result.stderr.split('\n'):
            if "Duration" in line:
                time_str = line.split("Duration: ")[1].split(",")[0]
                h, m, s = time_str.split(":")
                duration = int(float(h)) * 3600 + int(float(m)) * 60 + float(s)
                return duration
        return 0
    except:
        return 0

# ============== BOT COMMANDS ==============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    welcome_text = """
🤖 *Welcome to Khmer Voice Bot!*

I can:
✅ Convert your voice message to TEXT
✅ Generate KHMER voice from that text
✅ Send it back as a voice message

*How to use:*
Simply send me a voice message or audio file

*Commands:*
/start - Show this menu
/help - Get help

*Note:* Works with any language, I'll convert to Khmer voice!
"""
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message"""
    help_text = """
📖 *Help Guide*

*Supported formats:*
• Voice messages (OGG/Opus)
• Audio files (MP3, M4A, WAV, AAC)

*Processing steps:*
1️⃣ Download your audio
2️⃣ Transcribe speech to text
3️⃣ Generate Khmer voice from text
4️⃣ Send back as voice message

*Tips:*
• Speak clearly for better transcription
• Keep messages under 2 minutes
• Reduce background noise

*Requirements:* FFmpeg must be installed
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")

# ============== MAIN PROCESSING ==============
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process voice message and convert to Khmer voice"""
    if whisper_model is None:
        await update.message.reply_text("❌ *Bot is initializing...*\nPlease wait a moment and try again.", parse_mode="Markdown")
        return
    
    user = update.effective_user
    msg = update.message
    user_id = user.id
    
    # Send typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Initialize status message
    status_msg = await msg.reply_text("🎯 *Processing your audio...*\n\n⏳ Step 1/5: Downloading file...", parse_mode="Markdown")
    
    temp_files = []  # Track files for cleanup
    
    try:
        # ========== STEP 1: Download file ==========
        file = None
        file_ext = None
        
        if msg.voice:
            file = await msg.voice.get_file()
            file_ext = ".ogg"
        elif msg.audio:
            file = await msg.audio.get_file()
            file_ext = ".mp3" if not msg.audio.file_name else Path(msg.audio.file_name).suffix
        elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("audio/"):
            file = await msg.document.get_file()
            file_ext = Path(msg.document.file_name).suffix
        else:
            await status_msg.edit_text("❌ *Error:* Please send a voice message or audio file.\n\nSupported: Voice notes, MP3, M4A, WAV", parse_mode="Markdown")
            return
        
        # Download file
        input_path = os.path.join(DOWNLOAD_FOLDER, f"input_{user_id}{file_ext}")
        await file.download_to_drive(input_path)
        temp_files.append(input_path)
        logger.info(f"Downloaded: {input_path}")
        
        # Check duration
        duration = get_audio_duration_ffmpeg(input_path)
        if duration > 120:  # 2 minutes max
            await status_msg.edit_text("❌ *Audio too long!*\nPlease send audio under 2 minutes for processing.", parse_mode="Markdown")
            return
        
        await status_msg.edit_text("✅ *Step 1/5: Downloaded!*\n🔄 *Step 2/5: Converting audio format...*", parse_mode="Markdown")
        
        # ========== STEP 2: Convert to WAV for Whisper ==========
        wav_path = os.path.join(DOWNLOAD_FOLDER, f"temp_{user_id}.wav")
        if not convert_audio_ffmpeg(input_path, wav_path, "wav"):
            await status_msg.edit_text("❌ *Error:* Could not process audio file. Make sure FFmpeg is installed.", parse_mode="Markdown")
            return
        temp_files.append(wav_path)
        
        await status_msg.edit_text("✅ *Step 2/5: Audio converted!*\n🎙️ *Step 3/5: Transcribing speech...*", parse_mode="Markdown")
        
        # ========== STEP 3: Transcribe ==========
        try:
            # Try Khmer first
            result = whisper_model.transcribe(wav_path, language="km", task="transcribe")
            transcribed_text = result["text"].strip()
            
            # If no text, try auto-detect
            if not transcribed_text or len(transcribed_text) < 3:
                result = whisper_model.transcribe(wav_path, task="transcribe")
                transcribed_text = result["text"].strip()
            
            logger.info(f"Transcribed ({len(transcribed_text)} chars): {transcribed_text[:100]}...")
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            await status_msg.edit_text("❌ *Error:* Failed to transcribe audio. Please try again with clearer speech.", parse_mode="Markdown")
            return
        
        if not transcribed_text or len(transcribed_text) < 2:
            await status_msg.edit_text("⚠️ *No speech detected!*\n\nPlease try:\n• Speak clearly\n• Reduce background noise\n• Keep audio length reasonable", parse_mode="Markdown")
            return
        
        await status_msg.edit_text(f"✅ *Step 3/5: Transcription complete!*\n📝 *Text:* \"{transcribed_text[:150]}...\"\n\n🔊 *Step 4/5: Generating Khmer voice...*", parse_mode="Markdown")
        
        # ========== STEP 4: Generate Khmer TTS ==========
        output_mp3 = os.path.join(DOWNLOAD_FOLDER, f"khmer_{user_id}.mp3")
        output_ogg = os.path.join(DOWNLOAD_FOLDER, f"khmer_{user_id}.ogg")
        
        try:
            # Generate Khmer speech using gTTS
            tts = gTTS(text=transcribed_text, lang="km", slow=False)
            tts.save(output_mp3)
            temp_files.append(output_mp3)
            logger.info(f"Generated Khmer TTS: {output_mp3}")
            
            # Convert to OGG/Opus for Telegram voice note
            if not convert_audio_ffmpeg(output_mp3, output_ogg, "ogg"):
                await status_msg.edit_text("❌ *Error:* Failed to convert to voice format.", parse_mode="Markdown")
                return
            temp_files.append(output_ogg)
            
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            await status_msg.edit_text("❌ *Error:* Failed to generate Khmer voice. Please try again.", parse_mode="Markdown")
            return
        
        await status_msg.edit_text("✅ *Step 4/5: Khmer voice generated!*\n📤 *Step 5/5: Sending...*", parse_mode="Markdown")
        
        # ========== STEP 5: Send back ==========
        try:
            # Check file size
            file_size = os.path.getsize(output_ogg)
            if file_size > 50 * 1024 * 1024:  # 50MB limit
                await status_msg.edit_text("⚠️ *File too large!*\nThe generated voice is too big. Please try shorter text.", parse_mode="Markdown")
                return
            
            # Send voice message
            with open(output_ogg, "rb") as voice_file:
                await msg.reply_voice(
                    voice=voice_file,
                    caption=f"🎤 *Khmer Voice Message*\n\n📝 *Text:* \"{transcribed_text[:200]}\"",
                    parse_mode="Markdown"
                )
            logger.info(f"Sent Khmer voice to user {user_id}")
            
            await status_msg.delete()
            
            # Send full transcription if long
            if len(transcribed_text) > 200:
                await msg.reply_text(f"📝 *Full transcription:*\n{transcribed_text}", parse_mode="Markdown")
                
        except Exception as e:
            logger.error(f"Send error: {e}")
            await status_msg.edit_text(f"❌ *Error:* Failed to send voice message.\n\nError: {str(e)[:100]}", parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await status_msg.edit_text(f"❌ *Unexpected Error:* {str(e)[:200]}\n\nPlease try again.", parse_mode="Markdown")
    
    finally:
        # Cleanup temporary files
        for file_path in temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up: {file_path}")
            except Exception as e:
                logger.error(f"Cleanup error for {file_path}: {e}")

async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ *An error occurred!*\n\nPlease try again later.",
            parse_mode="Markdown"
        )

def check_ffmpeg():
    """Check if FFmpeg is installed"""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except:
        return False

# ============== MAIN FUNCTION ==============
async def main():
    """Start the bot"""
    # Check FFmpeg
    if not check_ffmpeg():
        print("\n" + "="*50)
        print("❌ FFmpeg NOT FOUND!")
        print("="*50)
        print("\nPlease install FFmpeg:\n")
        print("Windows:")
        print("  1. Download from: https://ffmpeg.org/download.html")
        print("  2. Add to System PATH")
        print("  OR run: choco install ffmpeg (if you have Chocolatey)")
        print("\nMac:")
        print("  brew install ffmpeg")
        print("\nLinux:")
        print("  sudo apt install ffmpeg")
        print("="*50)
        return
    
    # Create Application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_error_handler(handle_error)
    
    # Start bot
    print("\n" + "="*50)
    print("🤖 KHMER VOICE CONVERTER BOT")
    print("="*50)
    print("✅ FFmpeg found!")
    print("✅ Bot is starting...")
    print("✅ Ready to process messages!")
    print("="*50 + "\n")
    
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
