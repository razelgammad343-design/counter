import discord
from discord import ui
import json
from flask import Flask
from threading import Thread
import traceback
import os
import asyncio

# =========================
# CONFIG
# =========================
ALLOWED_CHANNEL_ID = 1467897643471732980
ALLOWED_ROLE_ID = 1466987521987711047
OWNER_ID = 923096413934616596

# =========================
# INTENTS
# =========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

# =========================
# FLASK KEEP ALIVE
# =========================
app = Flask("")

@app.route("/")
def home():
    return "Bot is alive!"

def run():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    Thread(target=run, daemon=True).start()

# =========================
# DATA
# =========================
counter = 0
used_images = set()

mini_count = 0
small_count = 0
mediant_count = 0
vast_count = 0

live_message_id = None

# lock system (prevents double click abuse)
image_locks = {}

# =========================
# SAVE / LOAD
# =========================
def load_counter():
    global counter, used_images
    global mini_count, small_count, mediant_count, vast_count

    try:
        with open("data.json", "r") as f:
            data = json.load(f)

            counter = data.get("count", 0)
            used_images = set(data.get("used_images", []))

            mini_count = data.get("mini", 0)
            small_count = data.get("small", 0)
            mediant_count = data.get("mediant", 0)
            vast_count = data.get("vast", 0)
    except:
        pass


def save_counter():
    with open("data.json", "w") as f:
        json.dump({
            "count": counter,
            "used_images": list(used_images),
            "mini": mini_count,
            "small": small_count,
            "mediant": mediant_count,
            "vast": vast_count
        }, f)

# =========================
# LIVE BOARD
# =========================
async def update_live_board(channel):
    global live_message_id

    embed = discord.Embed(
        title="📊 LIVE COUNTER BOARD",
        color=discord.Color.green()
    )

    embed.add_field(name="📊 Total Counter", value=str(counter), inline=False)

    embed.add_field(
        name="📦 Breakdown",
        value=(
            f"🟢 Mini: {mini_count}\n"
            f"🔵 Small: {small_count}\n"
            f"🟡 Mediant: {mediant_count}\n"
            f"🔴 Vast: {vast_count}"
        ),
        inline=False
    )

    if live_message_id:
        try:
            msg = await channel.fetch_message(live_message_id)
            await msg.edit(embed=embed)
            return
        except:
            pass

    msg = await channel.send(embed=embed)
    live_message_id = msg.id

# =========================
# MODAL
# =========================
class AddModal(ui.Modal):
    def __init__(self, pack, message_id):
        super().__init__(title=f"{pack} Input")
        self.pack = pack
        self.message_id = message_id

    number = ui.TextInput(label="Enter number")

    async def on_submit(self, interaction: discord.Interaction):
        global counter, mini_count, small_count, mediant_count, vast_count

        try:
            value = int(self.number.value)

            counter += value

            if self.pack == "Mini":
                mini_count += value
            elif self.pack == "Small":
                small_count += value
            elif self.pack == "Mediant":
                mediant_count += value
            elif self.pack == "Vast":
                vast_count += value

            used_images.add(self.message_id)
            save_counter()

            await interaction.response.send_message(
                f"✅ {interaction.user.mention} added **{value}** to **{self.pack}**!"
            )

            await update_live_board(interaction.channel)

        except:
            print(traceback.format_exc())
            await interaction.response.send_message("❌ Invalid number!", ephemeral=True)

# =========================
# VIEW
# =========================
class ImageView(ui.View):
    def __init__(self, message_id):
        super().__init__(timeout=None)
        self.message_id = message_id

    async def interaction_check(self, interaction: discord.Interaction):
        if not any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("❌ No permission!", ephemeral=True)
            return False

        if interaction.channel.id != ALLOWED_CHANNEL_ID:
            await interaction.response.send_message("❌ Wrong channel!", ephemeral=True)
            return False

        return True

    async def use_button(self, interaction, size):

        # LOCK (prevents double click spam)
        if image_locks.get(self.message_id):
            return await interaction.response.send_message("❌ Already processing!", ephemeral=True)

        image_locks[self.message_id] = True

        try:
            if self.message_id in used_images:
                return await interaction.response.send_message("❌ Already processed!", ephemeral=True)

            used_images.add(self.message_id)

            self.clear_items()
            await interaction.response.edit_message(view=self)

            await interaction.followup.send_modal(AddModal(size, self.message_id))

        finally:
            await asyncio.sleep(1)
            image_locks.pop(self.message_id, None)

    @discord.ui.button(label="Mini", style=discord.ButtonStyle.success)
    async def mini(self, interaction, button):
        await self.use_button(interaction, "Mini")

    @discord.ui.button(label="Small", style=discord.ButtonStyle.primary)
    async def small(self, interaction, button):
        await self.use_button(interaction, "Small")

    @discord.ui.button(label="Mediant", style=discord.ButtonStyle.secondary)
    async def mediant(self, interaction, button):
        await self.use_button(interaction, "Mediant")

    @discord.ui.button(label="Vast", style=discord.ButtonStyle.danger)
    async def vast(self, interaction, button):
        await self.use_button(interaction, "Vast")

# =========================
# MESSAGE EVENT
# =========================
@client.event
async def on_message(message):
    global counter, mini_count, small_count, mediant_count, vast_count

    if message.author.bot:
        return

    if message.channel.id != ALLOWED_CHANNEL_ID:
        return

    # IMAGE DETECTION
    if message.attachments:
        for att in message.attachments:
            if att.content_type and att.content_type.startswith("image"):
                await message.reply("🖼️ Choose option:", view=ImageView(message.id))
                await update_live_board(message.channel)

    # RESET COMMAND
    if message.content.startswith("!clear"):
        if message.author.id != OWNER_ID:
            return await message.reply("❌ Owner only!")

        counter = 0
        mini_count = 0
        small_count = 0
        mediant_count = 0
        vast_count = 0

        used_images.clear()
        save_counter()

        await message.channel.send("🧹 Reset done!")
        await update_live_board(message.channel)

# =========================
# READY EVENT
# =========================
@client.event
async def on_ready():
    load_counter()
    print(f"Logged in as {client.user}")

# =========================
# START BOT
# =========================
TOKEN = os.getenv("TOKEN")

if TOKEN is None:
    raise Exception("❌ TOKEN is missing!")

keep_alive()
client.run(TOKEN)
