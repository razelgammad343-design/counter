import discord
import json
from flask import Flask
from threading import Thread
import traceback
import os

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise Exception("❌ TOKEN is missing!")

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
app = Flask(__name__)

@app.route('/')
def home():
    return "I'm alive"

def run():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# =========================
# DATA
# =========================
counter = 0
mini_count = 0
small_count = 0
mediant_count = 0
vast_count = 0

# =========================
# SAVE / LOAD
# =========================
def load_counter():
    global counter, mini_count, small_count, mediant_count, vast_count

    try:
        with open("data.json", "r") as f:
            data = json.load(f)
            counter = data.get("count", 0)
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
            "mini": mini_count,
            "small": small_count,
            "mediant": mediant_count,
            "vast": vast_count
        }, f)

# =========================
# LIVE LOG
# =========================
async def send_live_log(channel, user, pack, value):
    embed = discord.Embed(
        title="📊 Counter Update",
        description=f"✅ {user.mention} added **{value}** to **{pack}**",
        color=discord.Color.green()
    )

    embed.add_field(name="📊 Total", value=f"**{counter}**", inline=False)
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

    await channel.send(embed=embed)

# =========================
# VIEW (CORE FIX)
# =========================
class ImageView(discord.ui.View):
    def __init__(self, uploader_id):
        super().__init__(timeout=None)
        self.uploader_id = uploader_id
        self.used = False

    async def interaction_check(self, interaction: discord.Interaction):

        if self.used:
            await interaction.response.send_message("❌ Already used!", ephemeral=True)
            return False

        if interaction.user.id != self.uploader_id:
            await interaction.response.send_message("❌ Only uploader!", ephemeral=True)
            return False

        if not any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("❌ No permission!", ephemeral=True)
            return False

        if interaction.channel.id != ALLOWED_CHANNEL_ID:
            await interaction.response.send_message("❌ Wrong channel!", ephemeral=True)
            return False

        return True

    async def disable_all(self, interaction: discord.Interaction):
        self.used = True

        for item in self.children:
            item.disabled = True

        await interaction.message.edit(view=self)

    @discord.ui.button(label="Mini", style=discord.ButtonStyle.success)
    async def mini(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddModal("Mini", self))

    @discord.ui.button(label="Small", style=discord.ButtonStyle.primary)
    async def small(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddModal("Small", self))

    @discord.ui.button(label="Mediant", style=discord.ButtonStyle.secondary)
    async def mediant(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddModal("Mediant", self))

    @discord.ui.button(label="Vast", style=discord.ButtonStyle.danger)
    async def vast(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddModal("Vast", self))

# =========================
# MODAL
# =========================
class AddModal(discord.ui.Modal):
    def __init__(self, pack, view: ImageView):
        super().__init__(title=f"{pack} Input")
        self.pack = pack
        self.view = view

    number = discord.ui.TextInput(label="Enter number")

    async def on_submit(self, interaction: discord.Interaction):
        global counter, mini_count, small_count, mediant_count, vast_count

        try:
            if self.view.used:
                return await interaction.response.send_message(
                    "❌ Already used!",
                    ephemeral=True
                )

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

            save_counter()

            await interaction.response.send_message(
                f"✅ Added {value} to {self.pack}",
                ephemeral=True
            )

            await send_live_log(interaction.channel, interaction.user, self.pack, value)

            # 🔥 Disable buttons safely
            await self.view.disable_all(interaction)

        except:
            print(traceback.format_exc())
            await interaction.response.send_message("❌ Invalid number!", ephemeral=True)

# =========================
# EVENTS
# =========================
@client.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id != ALLOWED_CHANNEL_ID:
        return

    if message.attachments:
        if any(att.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")) for att in message.attachments):
            await message.reply(
                "🖼️ Image detected — only uploader can use:",
                view=ImageView(message.author.id)
            )

    if message.content.startswith("!clear"):
        if message.author.id != OWNER_ID:
            return await message.reply("❌ Owner only!")

        global counter, mini_count, small_count, mediant_count, vast_count

        counter = 0
        mini_count = 0
        small_count = 0
        mediant_count = 0
        vast_count = 0

        save_counter()
        await message.channel.send("🧹 Reset done!")

@client.event
async def on_ready():
    load_counter()
    print(f"Logged in as {client.user}")

# =========================
# START
# =========================
keep_alive()
bot.run(TOKEN)
