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
    raise Exception("❌ TOKEN is missing! Set it in environment variables.")

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
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)

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
# LIVE LOG
# =========================
async def send_live_log(channel, user, pack, value):
    try:
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

    except:
        print("⚠️ Failed to send live log")

# =========================
# MODAL
# =========================
class AddModal(discord.ui.Modal):
    def __init__(self, pack, message_id):
        super().__init__(title=f"{pack} Input")
        self.pack = pack
        self.message_id = message_id

    number = discord.ui.TextInput(label="Enter number")

    async def on_submit(self, interaction: discord.Interaction):
        global counter
        global mini_count, small_count, mediant_count, vast_count

        try:
            value = int(self.number.value)

            key = f"{self.message_id}-{interaction.user.id}"

            if key in used_images:
                return await interaction.response.send_message(
                    "❌ You already used this image!",
                    ephemeral=True
                )

            used_images.add(key)

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
                f"✅ Added **{value}** to **{self.pack}**!",
                ephemeral=True
            )

            await send_live_log(interaction.channel, interaction.user, self.pack, value)

        except:
            print(traceback.format_exc())
            await interaction.response.send_message("❌ Invalid number!", ephemeral=True)

# =========================
# VIEW (FIXED: ONLY UPLOADER CAN USE)
# =========================
class ImageView(discord.ui.View):
    def __init__(self, uploader_id, message_id):
        super().__init__(timeout=None)
        self.uploader_id = uploader_id
        self.message_id = message_id

    async def interaction_check(self, interaction: discord.Interaction):

        # ❌ ONLY uploader can use buttons
        if interaction.user.id != self.uploader_id:
            await interaction.response.send_message(
                "❌ Only the uploader of this image can use the buttons!",
                ephemeral=True
            )
            return False

        # ❌ role check
        if not any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("❌ No permission!", ephemeral=True)
            return False

        # ❌ channel check
        if interaction.channel.id != ALLOWED_CHANNEL_ID:
            await interaction.response.send_message("❌ Wrong channel!", ephemeral=True)
            return False

        return True

    @discord.ui.button(label="Mini", style=discord.ButtonStyle.success)
    async def mini(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddModal("Mini", self.message_id))

    @discord.ui.button(label="Small", style=discord.ButtonStyle.primary)
    async def small(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddModal("Small", self.message_id))

    @discord.ui.button(label="Mediant", style=discord.ButtonStyle.secondary)
    async def mediant(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddModal("Mediant", self.message_id))

    @discord.ui.button(label="Vast", style=discord.ButtonStyle.danger)
    async def vast(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddModal("Vast", self.message_id))

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
                "🖼️ Image detected — only uploader can use buttons:",
                view=ImageView(message.author.id, message.id)
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
        used_images.clear()

        save_counter()
        await message.channel.send("🧹 Counter reset!")

@client.event
async def on_ready():
    load_counter()
    client.add_view(ImageView(0, 0))  # persistent dummy
    print(f"Logged in as {client.user}")

# =========================
# START
# =========================
keep_alive()
client.run(TOKEN)
