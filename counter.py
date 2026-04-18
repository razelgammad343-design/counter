import discord
import json
from flask import Flask
from threading import Thread

TOKEN = "YOUR_BOT_TOKEN"

ALLOWED_CHANNEL_ID = 1491725404501708810
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
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run).start()

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
    embed = discord.Embed(
        title="📊 LIVE COUNTER LOG",
        color=discord.Color.green()
    )

    embed.add_field(name="👤 User", value=user.mention, inline=True)
    embed.add_field(name="📦 Type", value=pack, inline=True)
    embed.add_field(name="➕ Added", value=str(value), inline=True)

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

    await channel.send(embed=embed)

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

            channel = interaction.channel

            # ✅ FIXED: PUBLIC MESSAGE (VISIBLE TO EVERYONE)
            await interaction.response.defer()

            await interaction.followup.send(
                f"✅ {interaction.user.mention} added **{value}** to **{self.pack}**!"
            )

            # LIVE LOG
            await send_live_log(channel, interaction.user, self.pack, value)

        except:
            await interaction.response.send_message("❌ Invalid number!", ephemeral=True)

# =========================
# VIEW
# =========================
class ImageView(discord.ui.View):
    def __init__(self, message_id):
        super().__init__(timeout=None)
        self.message_id = message_id

    async def already_used(self, interaction):
        if self.message_id in used_images:
            await interaction.response.send_message("❌ Already used!", ephemeral=True)
            return True
        return False

    @discord.ui.button(label="Mini", style=discord.ButtonStyle.success)
    async def mini(self, interaction, button):
        if await self.already_used(interaction):
            return
        await interaction.response.send_modal(AddModal("Mini", self.message_id))

    @discord.ui.button(label="Small", style=discord.ButtonStyle.primary)
    async def small(self, interaction, button):
        if await self.already_used(interaction):
            return
        await interaction.response.send_modal(AddModal("Small", self.message_id))

    @discord.ui.button(label="Mediant", style=discord.ButtonStyle.secondary)
    async def mediant(self, interaction, button):
        if await self.already_used(interaction):
            return
        await interaction.response.send_modal(AddModal("Mediant", self.message_id))

    @discord.ui.button(label="Vast", style=discord.ButtonStyle.danger)
    async def vast(self, interaction, button):
        if await self.already_used(interaction):
            return
        await interaction.response.send_modal(AddModal("Vast", self.message_id))

# =========================
# MESSAGE EVENT
# =========================
@client.event
async def on_message(message):
    if message.author.bot:
        return

    # IMAGE DETECT
    if message.attachments:
        for att in message.attachments:
            if att.content_type and att.content_type.startswith("image"):

                await message.reply(
                    "🖼️ Image detected — choose option:",
                    view=ImageView(message.id)
                )

    # RESET COMMAND
    if message.content.startswith("!clear"):
        if message.author.id != OWNER_ID:
            return await message.reply("❌ Owner only!")

        global counter, mini_count, small_count, mediant_count, vast_count

        counter = 0
        mini_count = small_count = mediant_count = vast_count = 0

        save_counter()
        await message.channel.send("🧹 Counter reset!")

# =========================
# READY
# =========================
@client.event
async def on_ready():
    load_counter()
    print(f"Logged in as {client.user}")

# =========================
# START BOT
# =========================
keep_alive()
client.run(TOKEN)
