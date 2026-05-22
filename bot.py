# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import asyncio
import os
import sys
import logging
from aiohttp import web
from pyrogram import Client, idle
from pyrogram.errors import FloodWait
from config import API_ID, API_HASH, BOT_TOKEN, STRING_SESSION, LOGIN_SYSTEM


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# OPTIMIZATION: 1MB Chunk-size + Connection Stability
# ============================================================================

_MAX_CHUNK_SIZE = 1024 * 1024  # 1 MB
_INTER_CHUNK_DELAY = 5


def _apply_chunk_size_patch():
    """Apply chunk-size optimization and connection handling"""
    try:
        import pyrogram.utils as _putils

        _original_get_file = _putils.get_file

        async def _throttled_get_file(
            client,
            id,
            access_hash,
            file_reference,
            offset,
            limit=_MAX_CHUNK_SIZE,
            *args,
            **kwargs,
        ):
            first_chunk = True
            retry_count = 0
            max_retries = 3

            while retry_count < max_retries:
                try:
                    async for chunk in _original_get_file(
                        client,
                        id,
                        access_hash,
                        file_reference,
                        offset,
                        limit,
                        *args,
                        **kwargs,
                    ):
                        if not first_chunk:
                            await asyncio.sleep(_INTER_CHUNK_DELAY)
                        first_chunk = False
                        yield chunk
                    break

                except (ConnectionError, OSError, TimeoutError) as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = (2 ** retry_count)
                        logger.warning(
                            f"Connection error (retry {retry_count}/{max_retries}), "
                            f"waiting {wait_time}s: {e}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"Max retries exceeded: {e}")
                        raise

        _putils.get_file = _throttled_get_file
        logger.info(
            f"✅ CHUNK-SIZE OPTIMIZATION APPLIED\n"
            f"   • Chunk size: {_MAX_CHUNK_SIZE // 1024} KB\n"
            f"   • Inter-chunk delay: {_INTER_CHUNK_DELAY}s\n"
            f"   • Connection retry: Enabled (3 retries with exponential backoff)"
        )
        return True

    except Exception as patch_err:
        logger.warning(f"⚠️ Could not apply chunk-size patch: {patch_err}")
        return False


# ============================================================================
# CLIENT INITIALIZATION
# ============================================================================

if STRING_SESSION is not None and LOGIN_SYSTEM is False:
    TechVJUser = Client(
        "TechVJ",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=STRING_SESSION,
    )
else:
    TechVJUser = None


class Bot(Client):
    """Main bot client"""

    def __init__(self):
        super().__init__(
            "techvj_login",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins=dict(root="TechVJ"),
            workers=25,
            sleep_threshold=60,
        )

    async def start(self):
        try:
            await super().start()
            logger.info("✅ Bot Started Successfully")
            logger.info("   Powered By @VJ_Botz")
        except Exception as e:
            logger.error(f"❌ Failed to start bot: {e}")
            raise

    async def stop(self, *args):
        try:
            await super().stop()
            logger.info("✅ Bot Stopped Gracefully")
        except Exception as e:
            logger.error(f"⚠️ Error during shutdown: {e}")


# ============================================================================
# WEB SERVER (Keep-Alive)
# ============================================================================


async def health_check_handler(request):
    return web.Response(
        text="Bot is alive and running ✅",
        status=200,
        content_type="text/plain",
    )


async def run_web_server():
    try:
        app = web.Application()
        app.router.add_get("/", health_check_handler)
        app.router.add_get("/health", health_check_handler)

        runner = web.AppRunner(app)
        await runner.setup()

        port = int(os.environ.get("PORT", 8080))

        try:
            site = web.TCPSite(runner, "0.0.0.0", port)
            await site.start()
            logger.info(f"🌐 Web Server Running on Port {port}")

        except OSError:
            if port == 8080:
                port = 8081
                site = web.TCPSite(runner, "0.0.0.0", port)
                await site.start()
                logger.info(f"⚠️ Switched to Port {port} (8080 busy)")
            else:
                raise

    except Exception as e:
        logger.warning(f"⚠️ Web Server Error: {e}")
        logger.info("   Bot will continue without web server")


# ============================================================================
# CONNECTION MONITORING
# ============================================================================


async def monitor_connection(client, interval=60):
    while True:
        try:
            await asyncio.sleep(interval)
            try:
                await client.get_me()
                logger.debug("✅ Connection healthy")
            except Exception as e:
                logger.warning(f"⚠️ Connection issue: {e}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Monitor error: {e}")


# ============================================================================
# MAIN APPLICATION
# ============================================================================


async def main():
    logger.info("=" * 70)
    logger.info("🚀 STARTING BOT APPLICATION")
    logger.info("=" * 70)

    config_ok = True
    if not API_ID:
        logger.error("❌ API_ID not set in config")
        config_ok = False
    if not API_HASH:
        logger.error("❌ API_HASH not set in config")
        config_ok = False
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN not set in config")
        config_ok = False

    if not config_ok:
        logger.error("❌ Missing required configuration!")
        return

    logger.info("✅ Configuration verified")

    _apply_chunk_size_patch()

    bot = Bot()
    monitor_task = None
    user_monitor_task = None

    try:
        logger.info("📡 Connecting Bot Client...")
        await bot.start()
        logger.info("✅ Bot Client Connected")

        monitor_task = asyncio.create_task(monitor_connection(bot, interval=60))
        logger.info("📊 Connection Monitor Started")

        if TechVJUser is not None:
            logger.info("👤 Connecting User Client...")
            try:
                await TechVJUser.start()
                logger.info("✅ User Client Connected")
                user_monitor_task = asyncio.create_task(
                    monitor_connection(TechVJUser, interval=60)
                )
                logger.info("📊 User Client Monitor Started")
            except Exception as e:
                logger.error(f"❌ Failed to connect User Client: {e}")
                logger.info("   Bot will continue without user client")
        else:
            logger.warning("⚠️ No User Client (STRING_SESSION not set)")

        logger.info("🔧 Initializing Web Server...")
        asyncio.create_task(run_web_server())

        logger.info("=" * 70)
        logger.info("✅ ALL SYSTEMS OPERATIONAL")
        logger.info("=" * 70)
        logger.info("🤖 Bot is ready to receive messages...")

        await idle()

    except KeyboardInterrupt:
        logger.info("\n⏹️ Shutdown signal received...")

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        logger.info("🛑 Shutting down all systems...")

        if monitor_task:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        if user_monitor_task:
            user_monitor_task.cancel()
            try:
                await user_monitor_task
            except asyncio.CancelledError:
                pass

        try:
            await bot.stop()
            logger.info("✅ Bot Client Stopped")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")

        if TechVJUser is not None:
            try:
                await TechVJUser.stop()
                logger.info("✅ User Client Stopped")
            except Exception as e:
                logger.error(f"Error stopping user client: {e}")

        logger.info("✅ Shutdown complete")
        logger.info("=" * 70)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        logger.info("\n" + "=" * 70)
        logger.info("BOT CONFIGURATION")
        logger.info("=" * 70)
        logger.info(f"API ID: {'✅ Set' if API_ID else '❌ Not Set'}")
        logger.info(f"API Hash: {'✅ Set' if API_HASH else '❌ Not Set'}")
        logger.info(f"Bot Token: {'✅ Set' if BOT_TOKEN else '❌ Not Set'}")
        logger.info(f"Login System: {'Enabled' if LOGIN_SYSTEM else 'Disabled'}")
        logger.info(f"String Session: {'✅ Set' if STRING_SESSION else '❌ Not Set'}")
        logger.info("=" * 70 + "\n")

        asyncio.run(main())

    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            logger.warning("⚠️ Event loop already running, using get_event_loop()...")
            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
        else:
            raise

    except KeyboardInterrupt:
        logger.info("\n✅ Bot terminated by user")
        sys.exit(0)

    except Exception as e:
        logger.error(f"\n❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
