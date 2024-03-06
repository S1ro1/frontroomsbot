import os
import discord
from traceback import print_exc
from io import StringIO
import httpx

from discord.ext import commands
import motor.motor_asyncio as ma

from consts import TOKEN, GUILD, DB_CONN, COGS_DIR, ERROR_WH

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

guild = discord.Object(id=GUILD)


class BackroomsBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        db_client = ma.AsyncIOMotorClient(DB_CONN)
        self.db = db_client.bot_database
        self.backrooms = guild

    def list_extensions(self):
        for filename in os.listdir(COGS_DIR):
            if filename.endswith("py") and not filename.startswith("_"):
                yield f"{'.'.join(COGS_DIR.split('/'))}.{filename[:-3]}"

    async def setup_hook(self):
        # make sure aaa_extensions is first
        for name in sorted(self.list_extensions()):
            try:
                await self.load_extension(name)
            except Exception:
                content = StringIO()
                print_exc(file=content)
                print(content.getvalue())
                await self.send_wh(f"extension {name} failed", content.getvalue())

    async def send_wh(self, title: str, msg: str = ""):
        if not ERROR_WH:
            print("No webhook set, not sending")
            return
        data = {
            "content": title,
            "allowed_mentions": {"parse": []},
            "embeds": [
                {
                    "title": "Traceback",
                    "description": "```" + msg[-3950:] + "```",
                }
            ],
        }
        if not msg:
            del data["embeds"]
        async with httpx.AsyncClient() as cl:
            # use a webhook instead of the discord connection in
            # case the error is caused by being disconnected from discord
            # also prevents error reporting from breaking API limits
            await cl.post(ERROR_WH, json=data)

    async def on_error(self, event: str, *args, **kwargs):
        content = StringIO()
        print_exc(file=content)
        print(content.getvalue())
        await self.send_wh(
            f"Bot ran into an error in event {event!r} with \n`{args=!r}`\n`{kwargs=!r}`",
            content.getvalue(),
        )


client = BackroomsBot(command_prefix="!", intents=intents)

if __name__ == "__main__":
    client.run(TOKEN)
