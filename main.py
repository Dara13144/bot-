import os
import logging
import io
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import speech_recognition as sr
from googletrans import Translator
from pydub import AudioSegment
import tempfile
import asyncio

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Your bot token - PLEASE REGENERATE THIS TOKEN IMMEDIATELY!
BOT_TOKEN = "8824304522:AAEmGYkq0xYWZWs4u1QnwUWkfHlnA_ACejs"

# Initialize recognizer and translator
recognizer = sr.Recognizer()
translator = Translator()

# Dictionary of Khmer sound files (add your MP3 files)
KHMER_SOUNDS = {
    'សួស្តី': {'filename': 'suosdey.mp3', 'description': 'សួស្តី'},
    'អរគុណ': {'filename': 'arkun.mp3', 'description': 'អរគុណ'},
    'បាទ': {'filename': 'bat.mp3', 'description': 'បាទ'},
    'ទេ': {'filename': 'te.mp3', 'description': 'ទេ'},
    'សុខសប្បាយ': {'filename': 'sok_sabbay.mp3', 'description': 'សុខសប្បាយ'},
    'លាហើយ': {'filename': 'lea_hy.mp3', 'description': 'លាហើយ'}
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued."""
    welcome_text = (
        "🌟 **សូមស្វាគមន៍មកកាន់ Bot បកប្រែសំឡេងអង់គ្លេសទៅខ្មែរ!** 🌟\n\n"
        "ខ្ញុំអាច៖\n"
        "✅ បកប្រែសារសំឡេងអង់គ្លេសទៅជាអត្ថបទខ្មែរ\n"
        "✅ បកប្រែអត្ថបទអង់គ្លេសទៅខ្មែរ\n"
        "✅ ផ្ញើសំឡេងខ្មែរតាមពាក្យបញ្ជា\n"
        "✅ ទទួលឯកសារសំឡេង\n\n"
        "**📝 ពាក្យបញ្ជា:**\n"
        "• `/start` - ចាប់ផ្តើម\n"
        "• `/help` - ជំនួយ\n"
        "• `/khmer_sounds` - សំឡេងខ្មែរ\n"
        "• `/translate_text <text>` - បកប្រែអត្ថបទ\n\n"
        "**🎤 សាកល្បងផ្ញើសារសំឡេងជាភាសាអង់គ្លេស!**"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message."""
    help_text = (
        "🤖 **របៀបប្រើប្រាស់ Bot**\n\n"
        "**1️⃣ បកប្រែសារសំឡេងអង់គ្លេស → ខ្មែរ**\n"
        "• ចុចប៊ូតុង 🎤 (Microphone)\n"
        "• និយាយជាភាសាអង់គ្លេស\n"
        "• Bot នឹងបកប្រែជាអត្ថបទខ្មែរ\n\n"
        "**2️⃣ បកប្រែអត្ថបទអង់គ្លេស → ខ្មែរ**\n"
        "• ប្រើ `/translate_text Hello how are you?`\n"
        "• Bot នឹងបកប្រែជាខ្មែរ\n\n"
        "**3️⃣ ស្តាប់សំឡេងខ្មែរ**\n"
        "• ផ្ញើពាក្យខ្មែរដូចជា: សួស្តី, អរគុណ\n"
        "• ប្រើ `/khmer_sounds` មើលបញ្ជីទាំងអស់\n\n"
        "**4️⃣ ផ្ញើឯកសារសំឡេង**\n"
        "• ផ្ញើឯកសារ MP3/WAV\n"
        "• Bot នឹងរក្សាទុកជូន\n\n"
        "**💡 ឧទាហរណ៍:**\n"
        "និយាយថា \"Hello\" → បកប្រែជា \"សួស្តី\"\n"
        "និយាយថា \"Thank you\" → បកប្រែជា \"អរគុណ\""
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def list_sounds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all available Khmer sounds."""
    sound_list = "🎵 **សំឡេងខ្មែរដែលមាន:**\n\n"
    for word, info in KHMER_SOUNDS.items():
        sound_list += f"🔊 {word} - {info['description']}\n"
    sound_list += "\nគ្រាន់តែផ្ញើពាក្យខាងលើមក ខ្ញុំនឹងផ្ញើសំឡេងជូន!"
    await update.message.reply_text(sound_list, parse_mode='Markdown')

async def translate_text_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Translate English text to Khmer."""
    if not context.args:
        await update.message.reply_text(
            "❌ សូមបញ្ចូលអត្ថបទដែលចង់បកប្រែ!\n\n"
            "ឧទាហរណ៍: `/translate_text Hello how are you?`",
            parse_mode='Markdown'
        )
        return
    
    english_text = ' '.join(context.args)
    
    # Send processing message
    processing_msg = await update.message.reply_text("⏳ កំពុងបកប្រែ...")
    
    try:
        # Translate to Khmer
        translation = translator.translate(english_text, src='en', dest='km')
        khmer_text = translation.text
        
        # Send result
        result_text = (
            f"**🇬🇧 អង់គ្លេស:**\n{english_text}\n\n"
            f"**🇰🇭 ខ្មែរ:**\n{khmer_text}\n\n"
            f"✅ បកប្រែដោយ Google Translate"
        )
        
        await processing_msg.delete()
        await update.message.reply_text(result_text, parse_mode='Markdown')
        
        logger.info(f"Translated text for user {update.message.from_user.id}: {english_text} -> {khmer_text}")
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
        await processing_msg.delete()
        await update.message.reply_text(
            "❌ មានបញ្ហាក្នុងការបកប្រែ! សូមព្យាយាមម្តងទៀត។"
        )

async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages and translate English to Khmer."""
    try:
        # Get voice message
        voice = update.message.voice
        voice_file = await voice.get_file()
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            "🎤 **កំពុងស្តាប់សារសំឡេងរបស់អ្នក...**\n\n"
            "⏳ សូមមេត្តារង់ចាំបន្តិច",
            parse_mode='Markdown'
        )
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_ogg:
            temp_ogg_path = temp_ogg.name
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            temp_wav_path = temp_wav.name
        
        # Download voice message
        await voice_file.download_to_drive(temp_ogg_path)
        
        # Convert OGG to WAV
        await processing_msg.edit_text(
            "🔄 **កំពុងបំប្លែងទ្រង់ទ្រាយសំឡេង...**",
            parse_mode='Markdown'
        )
        
        audio = AudioSegment.from_ogg(temp_ogg_path)
        audio.export(temp_wav_path, format='wav')
        
        # Recognize speech
        await processing_msg.edit_text(
            "📝 **កំពុងបកប្រែសំឡេងទៅជាអត្ថបទ...**",
            parse_mode='Markdown'
        )
        
        with sr.AudioFile(temp_wav_path) as source:
            audio_data = recognizer.record(source)
            
            try:
                # Recognize English speech
                english_text = recognizer.recognize_google(audio_data, language='en-US')
                
                # Translate to Khmer
                await processing_msg.edit_text(
                    "🌐 **កំពុងបកប្រែទៅជាភាសាខ្មែរ...**",
                    parse_mode='Markdown'
                )
                
                translation = translator.translate(english_text, src='en', dest='km')
                khmer_text = translation.text
                
                # Prepare result
                result_text = (
                    f"🎙️ **សារសំឡេងរបស់អ្នកបានបកប្រែរួចរាល់!**\n\n"
                    f"**🇬🇧 អង់គ្លេស:**\n{english_text}\n\n"
                    f"**🇰🇭 ខ្មែរ:**\n{khmer_text}\n\n"
                    f"⏱️ រយៈពេល: {voice.duration} វិនាទី\n"
                    f"✅ បកប្រែដោយ Google Speech Recognition & Translate"
                )
                
                # Also speak the Khmer translation if sound exists
                if khmer_text in KHMER_SOUNDS:
                    sound_path = os.path.join('sounds', KHMER_SOUNDS[khmer_text]['filename'])
                    if os.path.exists(sound_path):
                        with open(sound_path, 'rb') as audio_file:
                            await update.message.reply_audio(
                                audio=InputFile(audio_file),
                                caption=f"🔊 សំឡេងបកប្រែ: {khmer_text}"
                            )
                
                await processing_msg.delete()
                await update.message.reply_text(result_text, parse_mode='Markdown')
                
                logger.info(f"Voice translated for user {update.message.from_user.id}: {english_text} -> {khmer_text}")
                
            except sr.UnknownValueError:
                await processing_msg.delete()
                await update.message.reply_text(
                    "❌ **មិនអាចស្គាល់សំឡេងបានទេ!**\n\n"
                    "សូមព្យាយាម៖\n"
                    "• និយាយឲ្យច្បាស់ជាងនេះ\n"
                    "• និយាយជាភាសាអង់គ្លេស\n"
                    "• កាត់បន្ថយសំលេងរំខាន",
                    parse_mode='Markdown'
                )
            except sr.RequestError as e:
                await processing_msg.delete()
                await update.message.reply_text(
                    f"❌ **បញ្ហាបច្ចេកទេស!**\n\n"
                    f"មិនអាចភ្ជាប់ទៅកាន់សេវាកម្ម Google បានទេ។\n"
                    f"សូមព្យាយាមម្តងទៀតក្រោយពីពីរបីនាទី។",
                    parse_mode='Markdown'
                )
        
        # Clean up temporary files
        os.unlink(temp_ogg_path)
        os.unlink(temp_wav_path)
        
    except Exception as e:
        logger.error(f"Error processing voice: {e}")
        await update.message.reply_text(
            "❌ **មានបញ្ហាក្នុងការដំណើរការសារសំឡេង!**\n\n"
            "សូមព្យាយាមម្តងទៀត។"
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages (Khmer sounds or English translation)."""
    text = update.message.text.strip()
    
    # Check if it's a Khmer sound command
    if text in KHMER_SOUNDS:
        sound_file = KHMER_SOUNDS[text]['filename']
        sound_path = os.path.join('sounds', sound_file)
        
        if os.path.exists(sound_path):
            try:
                with open(sound_path, 'rb') as audio:
                    await update.message.reply_audio(
                        audio=InputFile(audio),
                        title=f"{text} - សំឡេងខ្មែរ",
                        performer="Khmer Sound Bot",
                        caption=f"🎵 {KHMER_SOUNDS[text]['description']}"
                    )
            except Exception as e:
                logger.error(f"Error sending audio: {e}")
                await update.message.reply_text("❌ មានបញ្ហាក្នុងការផ្ញើសំឡេង!")
        else:
            await update.message.reply_text(
                f"❌ ឯកសារសំឡេងសម្រាប់ '{text}' មិនទាន់មានទេ!\n"
                f"សូមប្រើ `/khmer_sounds` ដើម្បីមើលបញ្ជីដែលមាន។",
                parse_mode='Markdown'
            )
    else:
        # Check if text is English and translate
        await update.message.reply_text(
            f"💡 **សាកល្បងប្រើ៖**\n\n"
            f"• `/translate_text {text}` - បកប្រែអត្ថបទនេះ\n"
            f"• ផ្ញើសារសំឡេងជាភាសាអង់គ្លេស\n"
            f"• ឬផ្ញើពាក្យខ្មែរដូចជា: {', '.join(list(KHMER_SOUNDS.keys())[:3])}",
            parse_mode='Markdown'
        )

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded audio files."""
    try:
        audio = update.message.audio
        audio_file = await audio.get_file()
        
        os.makedirs('uploaded_sounds', exist_ok=True)
        
        original_filename = audio.file_name if audio.file_name else f"audio_{audio.file_unique_id}.mp3"
        filename = f"{update.message.from_user.id}_{update.message.message_id}_{original_filename}"
        filepath = os.path.join('uploaded_sounds', filename)
        
        processing_msg = await update.message.reply_text("⏳ កំពុងទាញយកឯកសារ...")
        
        await audio_file.download_to_drive(filepath)
        
        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        
        confirmation_text = (
            f"✅ **ទទួលបានឯកសារសំឡេងជោគជ័យ!**\n\n"
            f"📁 **ឈ្មោះ:** `{original_filename}`\n"
            f"📏 **ទំហំ:** {file_size_mb:.2f} MB\n"
            f"⏱️ **រយៈពេល:** {audio.duration} វិនាទី\n\n"
            f"💾 រក្សាទុកដោយជោគជ័យ!"
        )
        
        await processing_msg.delete()
        await update.message.reply_text(confirmation_text, parse_mode='Markdown')
        
        logger.info(f"Saved audio from user {update.message.from_user.id}: {filepath}")
        
    except Exception as e:
        logger.error(f"Error handling audio: {e}")
        await update.message.reply_text("❌ មានបញ្ហាក្នុងការទទួលឯកសារ!")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ **មានបញ្ហាបច្ចេកទេស!**\n\n"
            "សូមអភ័យទោសចំពោះភាពមិនស្រួល។\n"
            "សូមព្យាយាមម្តងទៀតក្រោយពីពីរបីនាទី។",
            parse_mode='Markdown'
        )

def main():
    """Start the bot."""
    # Create directories
    os.makedirs('sounds', exist_ok=True)
    os.makedirs('uploaded_sounds', exist_ok=True)
    
    # Create sample sound files info
    readme_path = os.path.join('sounds', 'README.txt')
    if not os.path.exists(readme_path):
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write("Place your Khmer sound files here\n")
            f.write("=" * 40 + "\n\n")
            f.write("Required sound files:\n")
            for word, info in KHMER_SOUNDS.items():
                f.write(f"- {info['filename']} → {word}\n")
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("khmer_sounds", list_sounds))
    application.add_handler(CommandHandler("translate_text", translate_text_command))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the Bot
    print("=" * 60)
    print("🤖 Voice Translation Bot (English → Khmer) is starting...")
    print("=" * 60)
    print(f"Bot Token: {BOT_TOKEN[:15]}...")
    print("Features:")
    print("  ✅ Voice message translation (English → Khmer)")
    print("  ✅ Text translation (English → Khmer)")
    print("  ✅ Khmer sound playback")
    print("  ✅ Audio file upload")
    print("=" * 60)
    print("Bot is running! Press Ctrl+C to stop.")
    print("=" * 60)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
