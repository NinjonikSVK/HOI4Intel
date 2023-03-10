import datetime
import discord
from discord.ext import commands
from discord import app_commands
import config
import presets
from presets import _add_player
import pytz


class add_hoi_game(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.cursor, self.connection = config.setup()

    @app_commands.command(name="add_hoi_game", description="Schedule a new HOI4 Game with reservation!")
    @app_commands.describe(date_time="Example: Day.Month.Year Hours:Minutes, "
                                     'Example: "24.12.2023 23:56"',
                           time_zone='Example: "Europe/Berlin"',
                           announcement_channel='Channel into which announcement about this event will be posted.',
                           rating_required='Set a minimum rating required to reserve a nation.',
                           steam_required='Is steam verification required to reserve a nation?')
    async def add_hoi_game(self, interaction: discord.Interaction, date_time: str, time_zone: str, announcement_channel:
    discord.TextChannel, title: str, description: str, global_database: bool = False,
                           rating_required: int = 0, steam_required: bool = False):
        self.cursor, self.connection = config.setup()
        if interaction.user.guild_permissions.administrator:
            # Convert date_time string to datetime object
            formats = ["%d.%m.%Y %H:%M", "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M"]
            for fmt in formats:
                try:
                    datetime_obj = datetime.datetime.strptime(date_time, fmt)
                    break
                except ValueError:
                    pass
            else:
                await interaction.response.send_message("Invalid date/time format",
                                                        ephemeral=True)
                return

            # Convert time_zone string to timezone object
            try:
                timezone_obj = pytz.timezone(time_zone)
            except pytz.UnknownTimeZoneError:
                await interaction.response.send_message("Invalid time zone.\nList of all valid timezones: "
                                                        "https://en.wikipedia.org/wiki/List_of_tz_database_time_zones",
                                                        ephemeral=True)
                return

            if not (0 <= rating_required <= 100):
                await interaction.channel.send("Please only enter values in this interval: <0;100>",
                                               ephemeral=True)

            embed = discord.Embed(
                title=f"**New event: {title}**",
                description=description,
                colour=discord.Colour.green()
            )
            embed.set_thumbnail(url=interaction.guild.icon)
            embed.add_field(
                name="**Date & Time:**",
                value=f'<t:{int(datetime.datetime.timestamp(datetime_obj))}>',
                inline=False,
            )
            embed.add_field(
                name="Reserve a nation!",
                value='Click on the "Reserve" button to reserve a nation!',
                inline=True,
            )
            embed.add_field(
                name="Minimal rating:",
                value=f'{rating_required}%',
                inline=True,
            )
            embed.add_field(
                name="Steam verification required:",
                value=steam_required,
                inline=True,
            )

            message = await announcement_channel.send(embed=embed, view=presets.ReserveDialog(self.client))

            await interaction.response.send_message("Event added successfully!",
                                                    ephemeral=True)

            # Store datetime and timezone in MySQL database
            sql = "INSERT INTO events (guild_id, host_id, channel_id, event_start, timezone, rating_required, " \
                  "steam_required, message_id, global_database, title, description, created_at, updated_at) " \
                  "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())"
            values = (
                interaction.guild_id, interaction.user.id, announcement_channel.id,
                datetime_obj.astimezone(timezone_obj), timezone_obj.zone, rating_required / 100, steam_required,
                message.id, global_database, title, description)
            self.cursor.execute(sql, values)
            self.connection.commit()


async def setup(client: commands.Bot) -> None:
    await client.add_cog(add_hoi_game(client))
