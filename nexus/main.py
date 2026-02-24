import discord
import os
import asyncio
import time
import pytz
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from datetime import datetime, timedelta
from dotenv import load_dotenv
from agent import run_agent_with_history
from notion_task_manager import NotionTaskManager, DigestFormatter
from nexus_pipeline import init_pipeline

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

executor = ThreadPoolExecutor(max_workers=5)
conversation_history = defaultdict(list)
MAX_HISTORY = 20
EDIT_THROTTLE = 12

AEST = pytz.timezone("Australia/Melbourne")
DIGEST_CHANNEL_ID = int(os.getenv("DISCORD_DIGEST_CHANNEL_ID", "0"))
SUMIT_USER_ID     = int(os.getenv("DISCORD_SUMIT_USER_ID", "0"))
MORNING_HOUR      = 8
EVENING_HOUR      = 18


class DigestScheduler:
    def __init__(self, bot_client):
        self.client = bot_client
        self.formatter = DigestFormatter()

    async def _get_channel(self):
        if DIGEST_CHANNEL_ID:
            channel = self.client.get_channel(DIGEST_CHANNEL_ID)
            if channel:
                return channel
        if SUMIT_USER_ID:
            try:
                user = await self.client.fetch_user(SUMIT_USER_ID)
                return await user.create_dm()
            except Exception:
                pass
        return None

    async def send(self, message: str):
        channel = await self._get_channel()
        if channel:
            if len(message) > 1900:
                for i in range(0, len(message), 1900):
                    await channel.send(message[i:i+1900])
            else:
                await channel.send(message)
        else:
            print(f"⚠️  Digest: no channel configured.\n{message}")

    async def send_morning_digest(self):
        print("📬 Sending morning digest...")
        ntm = NotionTaskManager()
        try:
            data = await ntm.get_morning_digest_data()
            await self.send(self.formatter.format_morning_digest(data))
            print("✅ Morning digest sent")
        except Exception as e:
            print(f"❌ Morning digest error: {e}")
            await self.send(f"⚠️ Morning digest failed: {str(e)[:200]}")
        finally:
            await ntm.close()

    async def send_evening_digest(self):
        print("📬 Sending evening digest...")
        ntm = NotionTaskManager()
        try:
            data = await ntm.get_evening_digest_data()
            await self.send(self.formatter.format_evening_digest(data))
            print("✅ Evening digest sent")
        except Exception as e:
            print(f"❌ Evening digest error: {e}")
            await self.send(f"⚠️ Evening digest failed: {str(e)[:200]}")
        finally:
            await ntm.close()

    async def check_urgent_nudges(self):
        ntm = NotionTaskManager()
        try:
            overdue = await ntm.get_overdue_tasks()
            all_overdue = [t for items in overdue.values() for t in items]
            urgent = [t for t in all_overdue
                      if any(p in (t.get("priority") or "") for p in ["P1", "P2"])]
            if urgent:
                lines = [f"🚨 **{len(urgent)} high-priority overdue item(s)**"]
                for t in urgent[:4]:
                    lines.append(f"  ❗ **{t['title']}** — was due {t.get('due_date', '?')}")
                await self.send("\n".join(lines))
        except Exception as e:
            print(f"⚠️  Nudge check failed: {e}")
        finally:
            await ntm.close()

    def _seconds_until(self, hour: int) -> float:
        now = datetime.now(AEST)
        target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        return (target - now).total_seconds()

    async def _nudge_loop(self):
        while True:
            await asyncio.sleep(1800)
            await self.check_urgent_nudges()

    async def run(self):
        print(f"⏰ Digest scheduler started — {MORNING_HOUR}:00 AM & {EVENING_HOUR}:00 PM AEST")
        asyncio.create_task(self._nudge_loop())
        while True:
            secs_m = self._seconds_until(MORNING_HOUR)
            secs_e = self._seconds_until(EVENING_HOUR)
            next_secs, next_type = (secs_m, "morning") if secs_m <= secs_e else (secs_e, "evening")
            next_time = (datetime.now(AEST) + timedelta(seconds=next_secs)).strftime("%H:%M AEST")
            print(f"⏳ Next digest: {next_type} at {next_time}")
            await asyncio.sleep(next_secs)
            if next_type == "morning":
                await self.send_morning_digest()
            else:
                await self.send_evening_digest()
            await asyncio.sleep(61)


@client.event
async def on_ready():
    print(f"Skyler is online as {client.user}")
    scheduler = DigestScheduler(client)
    asyncio.create_task(scheduler.run())

    # Wire the article pipeline to Skyler's Discord channel.
    # pipeline.run() executes in a ThreadPoolExecutor (asyncio.run on a worker
    # thread), so we cannot call channel.send() directly from inside it —
    # aiohttp's timeout manager requires a real asyncio Task on the correct loop.
    # Solution: capture the main Discord event loop here (on_ready runs on it),
    # then use run_coroutine_threadsafe() to safely post from the worker thread.
    main_loop = asyncio.get_event_loop()

    async def _send_to_channel(message: str):
        """Coroutine that runs on the main Discord loop."""
        channel = await scheduler._get_channel()
        if channel:
            if len(message) > 1900:
                for i in range(0, len(message), 1900):
                    await channel.send(message[i:i+1900])
            else:
                await channel.send(message)

    def pipeline_discord_notify(message: str):
        """
        Thread-safe Discord notifier for the article pipeline.
        Can be called from any thread (including ThreadPoolExecutor workers).
        Schedules the coroutine on the main Discord event loop.
        """
        asyncio.run_coroutine_threadsafe(_send_to_channel(message), main_loop)

    init_pipeline(discord_notify_callback=pipeline_discord_notify)
    print("✅ Nexus pipeline wired to Discord")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    is_dm = isinstance(message.channel, discord.DMChannel)
    is_agent_channel = getattr(message.channel, 'name', None) == "agent"
    is_mentioned = client.user.mentioned_in(message)
    name_trigger = "skyler" in message.content.lower()

    if not (is_mentioned or is_agent_channel or is_dm or name_trigger):
        return

    user_input = message.content
    user_input = user_input.replace(f"<@{client.user.id}>", "").strip()
    if user_input.lower().startswith("skyler"):
        user_input = user_input[6:].strip()

    if user_input.lower() in ["clear", "reset", "forget", "clear history"]:
        conversation_history[message.author.id].clear()
        await message.channel.send("🧹 Memory cleared. Starting fresh.")
        return

    if not user_input:
        await message.channel.send("Hey! How can I help you?")
        return

    history = conversation_history[message.author.id]
    loop = asyncio.get_event_loop()
    status_msg = await message.channel.send("🧠 Starting...")
    last_edit_time = {"t": 0.0}
    msg_alive = {"v": True}
    edit_lock = asyncio.Lock()

    async def do_edit(text: str):
        if not msg_alive["v"]:
            return
        async with edit_lock:
            if not msg_alive["v"]:
                return
            now = time.monotonic()
            elapsed = now - last_edit_time["t"]
            if elapsed < EDIT_THROTTLE:
                await asyncio.sleep(EDIT_THROTTLE - elapsed)
            if not msg_alive["v"]:
                return
            try:
                await status_msg.edit(content=text[:1900])
                last_edit_time["t"] = time.monotonic()
            except discord.NotFound:
                msg_alive["v"] = False
            except Exception as e:
                print(f"Edit error: {e}")

    def progress_cb(event_type: str, text: str):
        asyncio.run_coroutine_threadsafe(do_edit(text), loop)

    try:
        result, updated_history = await loop.run_in_executor(
            executor, run_agent_with_history, user_input, history, progress_cb
        )
        conversation_history[message.author.id] = updated_history[-MAX_HISTORY:]
        msg_alive["v"] = False
        try:
            await status_msg.delete()
        except Exception:
            pass
        if len(result) > 1900:
            for i in range(0, len(result), 1900):
                await message.channel.send(result[i:i+1900])
        else:
            await message.channel.send(result)
    except Exception as e:
        try:
            await status_msg.edit(content=f"❌ Error: {str(e)[:1800]}")
        except Exception:
            await message.channel.send(f"❌ Error: {str(e)[:1800]}")


client.run(os.getenv("DISCORD_TOKEN"))
