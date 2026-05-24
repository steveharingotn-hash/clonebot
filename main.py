import discord
from discord import app_commands
import os
import json
import asyncio
from datetime import datetime

# Load config
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))  # Your Discord User ID
KEYS_FILE = "keys.json"

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Load or create keys file
if not os.path.exists(KEYS_FILE):
    with open(KEYS_FILE, "w") as f:
        json.dump([], f)

def load_keys():
    with open(KEYS_FILE, "r") as f:
        return json.load(f)

def save_keys(keys):
    with open(KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=2)

# ==================== CLONER FUNCTIONS ====================

async def clone_server(guild_from: discord.Guild, guild_to: discord.Guild):
    try:
        # Clone server name & icon
        await guild_to.edit(name=guild_from.name)
        if guild_from.icon:
            icon_bytes = await guild_from.icon.read()
            await guild_to.edit(icon=icon_bytes)

        # Delete existing channels & roles in target
        for channel in guild_to.channels:
            await channel.delete()
        for role in guild_to.roles:
            if role.name != "@everyone":
                await role.delete()

        # Create roles
        role_map = {}
        for role in reversed(guild_from.roles):
            if role.name == "@everyone":
                continue
            new_role = await guild_to.create_role(
                name=role.name,
                permissions=role.permissions,
                colour=role.colour,
                hoist=role.hoist,
                mentionable=role.mentionable
            )
            role_map[role.id] = new_role

        # Create channels & categories
        for channel in guild_from.channels:
            if isinstance(channel, discord.CategoryChannel):
                await guild_to.create_category(channel.name)
            elif isinstance(channel, discord.TextChannel):
                cat = discord.utils.get(guild_to.categories, name=channel.category.name) if channel.category else None
                await guild_to.create_text_channel(channel.name, category=cat)
            elif isinstance(channel, discord.VoiceChannel):
                cat = discord.utils.get(guild_to.categories, name=channel.category.name) if channel.category else None
                await guild_to.create_voice_channel(channel.name, category=cat)

        return True
    except Exception as e:
        print(f"Clone error: {e}")
        return False

# ==================== COMMANDS ====================

@tree.command(name="clone", description="Clone a server using a valid key")
@app_commands.describe(key="Your cloning key", source_id="Source Server ID", target_id="Target Server ID")
async def clone(interaction: discord.Interaction, key: str, source_id: str, target_id: str):
    await interaction.response.defer()

    if not key or not source_id or not target_id:
        await interaction.followup.send("❌ All fields are required: `key`, `source_id`, `target_id`")
        return

    try:
        source_id = int(source_id)
        target_id = int(target_id)
    except:
        await interaction.followup.send("❌ IDs must be valid numbers!")
        return

    keys = load_keys()
    if key not in keys:
        await interaction.followup.send("❌ Invalid or expired key!")
        return

    # Remove used key
    keys.remove(key)
    save_keys(keys)

    guild_from = client.get_guild(source_id)
    guild_to = client.get_guild(target_id)

    if not guild_from or not guild_to:
        await interaction.followup.send("❌ Bot must be in **both** source and target servers!")
        return

    if not guild_to.me.guild_permissions.administrator:
        await interaction.followup.send("❌ Bot needs **Administrator** permission in target server!")
        return

    msg = await interaction.followup.send("🔄 Cloning in progress... This may take a while.")

    success = await clone_server(guild_from, guild_to)

    if success:
        await msg.edit(content="✅ **Server cloned successfully!**")
    else:
        await msg.edit(content="❌ Something went wrong during cloning.")

@tree.command(name="generate_key", description="Generate a new cloning key (Owner only)")
async def generate_key(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ Owner only command!", ephemeral=True)
        return

    import secrets
    new_key = secrets.token_urlsafe(16)

    keys = load_keys()
    keys.append(new_key)
    save_keys(keys)

    await interaction.response.send_message(f"✅ **New key generated:**\n`{new_key}`\n(1 use only)", ephemeral=True)

@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot ready! Logged in as {client.user}")

client.run(TOKEN)
