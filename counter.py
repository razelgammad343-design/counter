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

status_message_id = None

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
# DATA
# =========================
data = {
    "channel1": {"counter": 0, "mini": 0, "small": 0, "mediant": 0, "vast": 0},
    "channel2": {"counter": 0, "mini": 0, "small": 0, "mediant": 0, "vast": 0},
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
# USER DATA
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
# STATUS PANEL BUILDER
# =========================
async def build_user_status(user_id):
    u = get_user_data(user_id)

    embed = discord.Embed(
        title="📊 Your Channel 2 Status",
        color=discord.Color.gold()
    )

    embed.add_field(name="📦 Total", value=f"{u['counter']:,}", inline=False)

    embed.add_field(
        name="📦 Breakdown",
        value=(
            f"🟢 Mini: {u['mini']:,}\n"
            f"🔵 Small: {u['small']:,}\n"
            f"🟡 Mediant: {u['mediant']:,}\n"
            f"🔴 Vast: {u['vast']:,}"
        ),
        inline=False
    )

    embed.add_field(name="💰 Profit (WL)", value=f"{u['profit']:.2f}", inline=False)

    embed.set_footer(text="📡 Auto-updating system")

    return embed

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

    embed.add_field(name="📊 Total", value=f"{ch['counter']:,}", inline=False)

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

    if channel.id == CHANNEL_2:
        u = get_user_data(user.id)
        embed.add_field(name="💰 Profit", value=f"{u['profit']:.2f} WL", inline=False)

    await channel.send(embed=embed)

# =========================
# IMAGE VIEW (SINGLE USE ONLY)
# =========================
class ImageView(discord.ui.View):
    def __init__(self, uploader_id):
        super().__init__(timeout=None)
        self.uploader_id = uploader_id
        self.used = False

    async def interaction_check(self, interaction: discord.Interaction):

        if self.used:
            return False

        if interaction.user.id != self.uploader_id:
            await interaction.response.send_message("❌ Only uploader can use!", ephemeral=True)
            return False

        if interaction.channel.id not in ALLOWED_CHANNEL_IDS:
            return False

        member = interaction.guild.get_member(interaction.user.id)
        if not member or not any(role.id == ALLOWED_ROLE_ID for role in member.roles):
            await interaction.response.send_message("❌ No permission!", ephemeral=True)
            return False

        return True

    async def lock(self, interaction):
        self.used = True
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Mini", style=discord.ButtonStyle.success)
    async def mini(self, interaction, button):
        await self.lock(interaction)
        await interaction.response.send_modal(AddModal("Mini", self))

    @discord.ui.button(label="Small", style=discord.ButtonStyle.primary)
    async def small(self, interaction, button):
        await self.lock(interaction)
        await interaction.response.send_modal(AddModal("Small", self))

    @discord.ui.button(label="Mediant", style=discord.ButtonStyle.secondary)
    async def mediant(self, interaction, button):
        await self.lock(interaction)
        await interaction.response.send_modal(AddModal("Mediant", self))

    @discord.ui.button(label="Vast", style=discord.ButtonStyle.danger)
    async def vast(self, interaction, button):
        await self.lock(interaction)
        await interaction.response.send_modal(AddModal("Vast", self))

# =========================
# MODAL
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
            key = self.pack.lower()

            if interaction.channel.id == CHANNEL_1:

                ch = data["channel1"]
                ch["counter"] += value
                ch[key] += value
                profit = 0

            else:

                ch = data["channel2"]
                u = get_user_data(interaction.user.id)

                ch["counter"] += value
                ch[key] += value

                u["counter"] += value
                u[key] += value

                profit = (value / 100000) * 15
                u["profit"] += profit

                # =========================
                # UPDATE STATUS PANEL
                # =========================
                global status_message_id

                try:
                    channel = interaction.channel
                    msg = await channel.fetch_message(status_message_id)

                    embed = await build_user_status(interaction.user.id)

                    await msg.edit(
                        content=f"📡 Updated: {interaction.user.mention}",
                        embed=embed
                    )
                except:
                    pass

            save_counter()

            await interaction.response.send_message(
                f"✅ Added {value:,}\n💰 Profit: {profit:.2f} WL",
                ephemeral=True
            )

            await send_live_log(interaction.channel, interaction.user, self.pack, value)
            await self.view.lock(interaction)

        except:
            await interaction.response.send_message("❌ Invalid number!", ephemeral=True)
            print(traceback.format_exc())

# =========================
# ON MESSAGE
# =========================
@client.event
async def on_message(message):

    if message.author.bot:
        return

    if message.channel.id not in ALLOWED_CHANNEL_IDS:
        return

    if message.attachments:
        if any(att.content_type and "image" in att.content_type for att in message.attachments):
            await message.channel.send(
                "🖼️ Image detected:",
                view=ImageView(message.author.id)
            )

    if message.content.startswith("!clear"):

        if message.author.id != OWNER_ID:
            return

        if message.channel.id == CHANNEL_1:
            data["channel1"] = {"counter": 0, "mini": 0, "small": 0, "mediant": 0, "vast": 0}
            await message.channel.send("🧹 Channel 1 reset!")

        elif message.channel.id == CHANNEL_2:
            data["channel2"] = {"counter": 0, "mini": 0, "small": 0, "mediant": 0, "vast": 0}
            data["users"] = {}
            await message.channel.send("🧹 Channel 2 reset + users cleared!")

        save_counter()

# =========================
# READY
# =========================
@client.event
async def on_ready():
    load_counter()
    print(f"Logged in as {client.user}")

    global status_message_id

    channel = client.get_channel(CHANNEL_2)

    if channel:
        embed = discord.Embed(
            title="📊 Channel 2 Status Panel",
            description="Live user tracking system",
            color=discord.Color.blue()
        )

        msg = await channel.send(embed=embed)
        status_message_id = msg.id

# =========================
# START
# =========================
if __name__ == "__main__":
    keep_alive()
    client.run(TOKEN)
