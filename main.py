import os
import requests
import discord
from discord.ext import commands, tasks
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from keep_alive import keep_alive
import pytz
from datetime import datetime

# ====================================
# === SETUP ENV DAN DISCORD BOT
# ====================================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ====================================
# === VARIABEL GLOBAL
# ====================================
notified_idn_slugs = set()
notified_showroom_ids = set()


# ==========================================
# === SCRAPING DATA LIVE MEMBER JKT48 DI IDN
# ==========================================
def get_live_idn_via_scraping():
    try:
        url = "https://www.idn.app/"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        live_items = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.startswith("/jkt48/live/"):
                slug = href.split("/")[-1]
                full_url = "https://www.idn.app" + href
                name = link.get_text(strip=True)
                if not name:
                    continue
                if name.strip().split()[-1].lower() == "jkt48":
                    live_items.append({
                        "name": name,
                        "slug": slug,
                        "url": full_url
                    })
        return live_items
    except Exception as e:
        print(f"❌ Gagal scraping IDN: {e}")
        return []


# ==========================================
# === AMBIL DATA LIVE MEMBER JKT48 DI SHOWROOM
# ==========================================
def get_showroom_livestream_data():
    try:
        url = "https://www.showroom-live.com/api/live/onlives"
        response = requests.get(url)
        return response.json().get("onlives", [])
    except Exception as e:
        print(f"❌ Gagal ambil data SHOWROOM: {e}")
        return []


# ====================================
# === NOTIFIKASI DISCORD UNTUK IDN
# ====================================
@tasks.loop(seconds=15)
async def idn_scrape_notifier():
    lives = get_live_idn_via_scraping()
    if not lives:
        return

    guild = bot.guilds[0]
    ch = discord.utils.get(guild.text_channels, name="idn")
    if not ch:
        print("❗ Channel #idn tidak ditemukan.")
        return

    for stream in lives:
        slug = stream["slug"]
        name = stream["name"]
        url = stream["url"]
        if slug not in notified_idn_slugs:
            notified_idn_slugs.add(slug)
            print(f"📢 IDN LIVE terdeteksi: {name} - {url}")
            await ch.send(f"🔴 {name} sedang live di IDN LIVE\n{url}")


# ====================================
# === NOTIFIKASI DISCORD UNTUK SHOWROOM
# ====================================
@tasks.loop(seconds=15)
async def showroom_notification():
    lives = get_showroom_livestream_data()
    if not lives:
        return

    guild = bot.guilds[0]
    ch = discord.utils.get(guild.text_channels, name="idn")
    if not ch:
        print("❗ Channel #idn tidak ditemukan.")
        return

    for group in lives:
        for room in group.get("lives", []):
            name = room.get("main_name")
            room_url_key = room.get("room_url_key")
            if not name or not room_url_key:
                continue
            if name.strip().split()[-1].lower() == "jkt48":
                if room_url_key not in notified_showroom_ids:
                    notified_showroom_ids.add(room_url_key)
                    url = f"https://www.showroom-live.com/{room_url_key}"
                    print(f"📢 SHOWROOM LIVE terdeteksi: {name} - {url}")
                    await ch.send(f"🟣 {name} sedang live di SHOWROOM\n{url}")


# ====================================
# === PING STATUS BOT TIAP 5 MENIT
# ====================================
@tasks.loop(minutes=5)
async def status_notifier():
    guild = bot.guilds[0]
    ch = discord.utils.get(guild.text_channels, name="idn")
    if not ch:
        print("❗ Channel #idn tidak ditemukan untuk status check.")
        return

    # Gunakan timezone Asia/Jakarta (WIB)
    wib_time = datetime.now(pytz.timezone("Asia/Jakarta")).strftime("%H:%M:%S")
    await ch.send(f"✅ Bot masih aktif (waktu WIB: {wib_time})")


# ====================================
# === BOT READY EVENT
# ====================================
@bot.event
async def on_ready():
    print(f"✅ Bot siap sebagai {bot.user}")
    try:
        idn_scrape_notifier.start()
        print("✅ Loop IDN dimulai.")
    except RuntimeError as e:
        print(f"❌ Gagal start loop IDN: {e}")

    try:
        showroom_notification.start()
        print("✅ Loop SHOWROOM dimulai.")
    except RuntimeError as e:
        print(f"❌ Gagal start loop SHOWROOM: {e}")

    try:
        status_notifier.start()
        print("✅ Loop STATUS dimulai.")
    except RuntimeError as e:
        print(f"❌ Gagal start loop STATUS: {e}")


# ====================================
# === JALANKAN BOT
# ====================================
keep_alive()
bot.run(TOKEN)
