import discord
import json
import traceback
import os
from flask import Flask
from threading import Thread

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise Exception("❌ TOKEN is missing!")

CHANNEL_1 = 1467897643471732980
CHANNEL_2 = 1499279455431032873

ALLOWED_CHANNEL_IDS = [CHANNEL_1, CHANNEL_2]

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
    return "Bot is running!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    Thread(target=run).start()

# =========================
# DATA (SEPARATED SYSTEM)
# =========================
data = {
    "channel1": {
        "counter": 0,
        "mini": 0,
        "small": 0,
        "mediant": 0,
        "vast": 0
    },
    "channel2": {
        "counter": 0,
        "mini": 0,
        "small": 0,
        "mediant": 0,
        "vast": 0
    },
    "users": {}
}

# =========================
# SAVE / LOAD
# =========================
def load_counter():
    global data
    try:
        with open("data.json", "r") as f:
            data.update(json.load(f))
    except:
        pass

def save_counter():
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)

# =========================
# USER DATA (CHANNEL 2 ONLY)
# =========================
def get_user_data(user_id):
    uid = str(user_id)

    if uid not in data["users"]:
        data["users"][uid] = {
            "counter": 0,
            "mini": 0,
            "small": 0,
            "mediant": 0,
            "vast": 0,
            "profit": 0.0
        }

    return data["users"][uid]

# =========================
# LOG SYSTEM
# =========================
async def send_live_log(channel, user, pack, value):

    system = "channel1" if channel.id == CHANNEL_1 else "channel2"
    ch = data[system]

    embed = discord.Embed(
        title="📊 Counter Update",
        description=f"✅ {user.mention} added **{value:,}** to **{pack}**",
        color=discord.Color.green()
    )

    embed.add_field(
        name="📊 Total",
        value=f"{ch['counter']:,}",
        inline=False
    )

    embed.add_field(
        name="📦 Breakdown",
        value=(
            f"🟢 Mini: {ch['mini']:,}\n"
            f"🔵 Small: {ch['small']:,}\n"
            f"🟡 Mediant: {ch['mediant']:,}\n"
            f"🔴 Vast: {ch['vast']:,}"
        ),
        inline=False
    )

    # ONLY CHANNEL 2 PROFIT
    if channel.id == CHANNEL_2:
        u = get_user_data(user.id)
        embed.add_field(
            name="💰 Profit(WL)",
            value=f"{u['profit']:.2f}",
            inline=False
        )

    await channel.send(embed=embed)

# =========================
# IMAGE VIEW (ONE TIME USE FIXED)
# =========================
class ImageView(discord.ui.View):
    def __init__(self, uploader_id):
        super().__init__(timeout=None)
        self.uploader_id = uploader_id
        self.used = False

    # 🔒 HARD BLOCK (runs BEFORE button logic)
    async def interaction_check(self, interaction: discord.Interaction):

        if self.used:
            await interaction.response.send_message("❌ Already used!", ephemeral=True)
            return False

        # ONLY uploader can use buttons
        if interaction.user.id != self.uploader_id:
            await interaction.response.send_message(
                "❌ Only the image uploader can use these buttons!",
                ephemeral=True
            )
            return False

        # channel lock
        if interaction.channel.id not in ALLOWED_CHANNEL_IDS:
            await interaction.response.send_message("❌ Wrong channel!", ephemeral=True)
            return False

        # role check
        member = interaction.guild.get_member(interaction.user.id)
        if not member or not any(role.id == ALLOWED_ROLE_ID for role in member.roles):
            await interaction.response.send_message("❌ No permission!", ephemeral=True)
            return False

        return True

    # 🔥 LOCK VIEW AFTER FIRST USE
    async def lock(self, interaction):
        self.used = True

        for item in self.children:
            item.disabled = True

        await interaction.message.edit(view=self)

    # =========================
    # BUTTONS (SAFE)
    # =========================
    @discord.ui.button(label="Mini", style=discord.ButtonStyle.success)
    async def mini(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.lock(interaction)
        await interaction.response.send_modal(AddModal("Mini", self))

    @discord.ui.button(label="Small", style=discord.ButtonStyle.primary)
    async def small(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.lock(interaction)
        await interaction.response.send_modal(AddModal("Small", self))

    @discord.ui.button(label="Mediant", style=discord.ButtonStyle.secondary)
    async def mediant(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.lock(interaction)
        await interaction.response.send_modal(AddModal("Mediant", self))

    @discord.ui.button(label="Vast", style=discord.ButtonStyle.danger)
    async def vast(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.lock(interaction)
        await interaction.response.send_modal(AddModal("Vast", self))

# =========================
# MODAL (FULL FIX)
# =========================
class AddModal(discord.ui.Modal):
    def __init__(self, pack, view):
        super().__init__(title=f"{pack} Input")
        self.pack = pack
        self.view = view

    number = discord.ui.TextInput(label="Enter number")

    async def on_submit(self, interaction: discord.Interaction):

        try:
            value = float(self.number.value.replace(",", ""))

            pack_key = self.pack.lower()

            # =========================
            # CHANNEL 1
            # =========================
            if interaction.channel.id == CHANNEL_1:

                ch = data["channel1"]
                ch["counter"] += value
                ch[pack_key] += value

                profit = 0

            # =========================
            # CHANNEL 2
            # =========================
            else:

                ch = data["channel2"]
                u = get_user_data(interaction.user.id)

                ch["counter"] += value
                ch[pack_key] += value

                u["counter"] += value
                u[pack_key] += value

                profit = (value / 100000) * 15
                u["profit"] += profit

            save_counter()

            await interaction.response.send_message(
                f"✅ Added {value:,}\n💰 Profit: {profit:.2f} WL",
                ephemeral=True
            )

            await send_live_log(interaction.channel, interaction.user, self.pack, value)
            await self.view.lock(interaction)

        except Exception as e:
            print(traceback.format_exc())
            await interaction.response.send_message(f"❌ Invalid number: {e}", ephemeral=True)

# =========================
# ON MESSAGE
# =========================
@client.event
async def on_message(message):

    if message.author.bot:
        return

    if message.channel.id not in ALLOWED_CHANNEL_IDS:
        return

    # IMAGE TRIGGER
    if message.attachments:
        if any(att.content_type and "image" in att.content_type for att in message.attachments):
            await message.channel.send(
                "🖼️ Image detected:",
                view=ImageView(message.author.id)
            )

    # =========================
    # CLEAR SYSTEM (FULLY SEPARATED)
    # =========================
    if message.content.startswith("!clear"):

        if message.author.id != OWNER_ID:
            return

        if message.channel.id == CHANNEL_1:
            data["channel1"] = {
                "counter": 0,
                "mini": 0,
                "small": 0,
                "mediant": 0,
                "vast": 0
            }
            save_counter()
            await message.channel.send("🧹 Channel 1 reset only!")

        elif message.channel.id == CHANNEL_2:
            data["channel2"] = {
                "counter": 0,
                "mini": 0,
                "small": 0,
                "mediant": 0,
                "vast": 0
            }
            data["users"] = {}
            save_counter()
            await message.channel.send("🧹 Channel 2 + users reset only!")
   
    # =========================
    # STATUS COMMAND (CHANNEL 2 ONLY)
    # =========================
    if message.content.lower() == "!status":

        if message.channel.id != CHANNEL_2:
            return

        ch = data["channel2"]

        embed = discord.Embed(
            title="📊 Channel 2 Status",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="📦 Total Counter",
            value=f"{ch['counter']:,}",
            inline=False
        )

        embed.add_field(
            name="📊 Breakdown",
            value=(
                f"🟢 Mini: {ch['mini']:,}\n"
                f"🔵 Small: {ch['small']:,}\n"
                f"🟡 Mediant: {ch['mediant']:,}\n"
                f"🔴 Vast: {ch['vast']:,}"
            ),
            inline=False
        )

        await message.channel.send(embed=embed)

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
if __name__ == "__main__":
    keep_alive()
    client.run(TOKEN)

