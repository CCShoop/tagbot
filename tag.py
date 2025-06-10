'''Written by Cael Shoop.'''

import os
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta
from discord import (app_commands, Interaction, Intents, Client, Embed, Status,
                     TextChannel, ActivityType, SelectOption, Activity,
                     PrivacyLevel, Member, Color)
from discord.ui import View, Select

from persistence import Persistence
from countdown_timer import CountdownTimer

# .env
load_dotenv()

# Logger setup
logger = logging.getLogger("Tag Bot")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(fmt='[%(asctime)s] [%(levelname)s\t] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

file_handler = logging.FileHandler('tag.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Persistence
persist = Persistence('data.json')

# Globals
TAGBACK_COOLDOWN_SECONDS = 300


def get_time_str_from_seconds(seconds: int) -> str:
    if seconds < 0:
        seconds *= -1
    output = []
    weeks = int(seconds // 60 // 60 // 24 // 7)
    if weeks != 0:
        output.append(f"{weeks} weeks" if weeks != 1 else "1 week")
    days = int(seconds // 60 // 60 // 24 % 7)
    if days != 0:
        output.append(f"{days} days" if days != 1 else "1 day")
    hours = int(seconds // 60 // 60 % 24)
    if hours != 0:
        output.append(f"{hours} hours" if hours != 1 else "1 hour")
    minutes = int(seconds // 60 % 60)
    if minutes != 0:
        output.append(f"{minutes} minutes" if minutes != 1 else "1 minute")
    if minutes == 0 and hours == 0 and days == 0 and weeks == 0:
        output.append("0 minutes")
    secs = int(seconds % 60)
    if secs != 0:
        output.append(f"{secs} seconds" if secs != 1 else "1 second")
    if secs == 0 and minutes == 0 and hours == 0 and days == 0 and weeks == 0:
        output.append("0 seconds")
    return ", ".join(output)


class TagClient(Client):
    def __init__(self, intents) -> None:
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.loaded_json: bool = False
        self.tagged_id: int = 0
        self.prev_tagged_id: int = 0
        self.tagged_datetime: datetime
        self.prev_tagged_time_seconds: int = 0
        self.tagback_timer: CountdownTimer = CountdownTimer(duration_seconds=TAGBACK_COOLDOWN_SECONDS)

    async def handle_tag(self, channel: TextChannel, tagger_id: int, tagged_id: int):
        success = self.tag(tagged_id)
        if success:
            await channel.send_message(embed=self.get_tag_success_embed(channel, tagger_id, tagged_id))
        else:
            await channel.send_message(embed=self.get_tag_fail_embed(channel, tagger_id, tagged_id))

    def tag(self, tagged_id):
        if (tagged_id != self.prev_tagged_id) or (tagged_id == self.prev_tagged_id and self.tagback_eligible):
            self.prev_tagged_id = self.tagged_id
            self.tagged_id = tagged_id
            return True
        else:
            return False

    def get_tag_success_embed(self, channel: TextChannel, tagger_id: int, tagged_id: int):
        tagger_name = tagger_id
        tagged_name = tagged_id
        tagger = channel.get_member(tagger_id)
        tagged = channel.get_member(tagged_id),
        if tagger:
            tagger_name = tagger.name
            if tagger.nick:
                tagger_name = tagger.nick
        if tagged:
            tagged_name = tagged.name
            if tagged.nick:
                tagged_name = tagged.nick
        embed = Embed(title=f"{tagged_name} has been tagged!",
                      color=Color.green())
        embed.add_field(name=f"Tagged by {tagger_name}",
                        value=f"{tagger_name} was it for {self.prev_tagged_time_string}",
                        inline=False)
        return embed

    def get_tag_fail_embed(self, channel: TextChannel, tagger_id: int, tagged_id: int):
        tagger_name = tagger_id
        tagged_name = tagged_id
        tagger = channel.get_member(tagger_id)
        tagged = channel.get_member(tagged_id)
        if tagger:
            tagger_name = tagger.name
            if tagger.nick:
                tagger_name = tagger.nick
        if tagged:
            tagged_name = tagged.name
            if tagged.nick:
                tagged_name = tagged.nick
        embed = Embed(title="Tagback Cooldown in Effect",
                      color=Color.red())
        embed.add_field(name=f"{self.tagback_time_remaining_string} remaining",
                        value=f"{tagger_name} tried to tag {tagged_name}",
                        inline=False)
        return embed

    def start_tagback_timer(self):
        self.tagback_timer.start()

    def stop_tagback_timer(self):
        self.tagback_timer.stop()

    @property
    def tagged_time_seconds(self):
        return (datetime.now() - self.tagged_datetime).total_seconds()

    @property
    def tagged_time_string(self):
        return get_time_str_from_seconds(self.tagged_time_seconds)

    @property
    def prev_tagged_time_string(self):
        return get_time_str_from_seconds(self.prev_tagged_time_seconds)

    @property
    def tagback_timer_running(self):
        return not client.tagback_timer.finished

    @property
    def tagback_time_remaining_seconds(self):
        return self.tagback_timer.remaining_time

    @property
    def tagback_time_remaining_string(self):
        return get_time_str_from_seconds(self.tagback_timer.remaining_time)

    @property
    def tagback_eligible(self):
        return self.tagback_timer.finished

    # Load the data file
    async def from_dict(self) -> None:
        if not self.loaded_json:
            self.loaded_json = True
            data = persist.read()
            if data:
                self.tagged_id = data["tagged_id"]
                self.tagged_id = data["prev_tagged_id"]
                self.tagged_datetime = datetime.fromisoformat(data["tagged_datetime"])
                self.prev_tagged_time_seconds = data["prev_tagged_time_seconds"]
            else:
                logger.info('No json data found')

    # Return dict
    def to_dict(self) -> dict:
        payload = {}
        payload["tagged_id"] = self.tagged_id
        payload["prev_tagged_id"] = self.prev_tagged_id
        payload["tagged_datetime"] = self.tagged_datetime.isoformat()
        payload["prev_tagged_time_seconds"] = self.prev_tagged_time_seconds
        return payload

    async def setup_hook(self):
        await self.tree.sync()


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
client = TagClient(intents=Intents.all())


# Save wrapper
def save() -> None:
    persist.write(client.to_dict())


class PlayerSelect(Select):
    def __init__(self, channel: TextChannel, tagger_id: int, tagged_id: int):
        self.channel: TextChannel = channel
        self.tagger_id: int = tagger_id
        self.tagged_id: int = tagged_id
        options = []
        for member in self.channel.members:
            if member.id != self.tagged_id:
                options.append(SelectOption(label=member.name, description=member.name, value=str(member.id)))
        super().__init__(placeholder="Player Select", options=options)

    async def callback(self, interaction: Interaction):
        selected_member = self.channel.get_member(int(self.values[0]))
        if selected_member:
            await client.handle_tag(self.channel, self.tagger_id, selected_member.id)
        else:
            logger.error(f"Failed to tag member with id {self.values[0]}")
            await interaction.response.send_message("There was an internal error while tagging this person.", ephemeral=True)


class PlayerSelectView(View):
    def __init__(self, channel: TextChannel, tagger_id: int, tagged_id: int):
        super().__init__()
        self.add_item(PlayerSelect(channel, tagger_id, tagged_id))


@client.event
async def on_ready():
    logger.info(f"{client.user} has connected to Discord!")
    await client.from_dict()
    logger.info(f"{client.user} is ready!")
    await client.change_presence(activity=Activity(type=ActivityType.watching, state="Online", name="for tagging"), status=Status.online)


@client.tree.command(name="tag", description="Tag a user.")
async def tag_command(interaction: Interaction):
    logger.info(f"{interaction.user.name} is tagging someone")
    view = PlayerSelectView(interaction.text_channel, interaction.user.id)
    await interaction.response.send_message(content="Select a player to tag.", view=view, ephemeral=True)
    save()


@client.tree.command(name="timetagged", description="How long the currently tagged user has been it.")
async def timetagged_command(interaction: Interaction):
    await interaction.response.send_message(content=f"{client.currently_tagged} has been it for {client.tagged_time_string}.", ephemeral=True)


@client.tree.command(name="cooldown", description="How much longer the tagback cooldown will last.")
async def cooldown_command(interaction: Interaction):
    if client.tagback_timer_running:
        await interaction.response.send_message(content=f"The cooldown has {client.tagback_time_remaining_string} remaining.", ephemeral=True)
    else:
        await interaction.response.send_message(content="The cooldown has expired.", ephemeral=True)


client.run(DISCORD_TOKEN)
