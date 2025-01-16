from discord.ext import commands, tasks
from discord.ui import Button, View
import datetime
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from difflib import SequenceMatcher
import json

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)
tree = bot.tree

@bot.event
async def on_ready():
    print(f"Bot1 is logged in as {bot.user}")


previous_channels = {}
spam_count = {}
whitelist = []
excluded_channels = []
whitelist_levels = {}

log_channel_id = 1328743530180378734
log_channel = None
ROLE_ID = 1329388146156372010
ALLOWED_CHANNEL_ID = 1294095145964273715
EVENT_CHANNEL_ID = 1329365475208990821

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def get_log_channel():
    global log_channel
    if log_channel is None:
        log_channel = bot.get_channel(log_channel_id)
    return log_channel

def save_excluded_channels():
    """Сохраняет список исключённых каналов в файл."""
    with open("excluded_channels.json", "w") as f:
        json.dump(excluded_channels, f, indent=4)

def load_excluded_channels():
    """Загружает список исключённых каналов из файла."""
    global excluded_channels
    try:
        with open("excluded_channels.json", "r") as f:
            excluded_channels = json.load(f)
    except FileNotFoundError:
        excluded_channels = []

load_excluded_channels()

def load_whitelist():
    global whitelist, whitelist_levels
    try:
        with open("whitelist.json", "r") as f:
            data = json.load(f)
            whitelist = data.get("whitelist", [])
            whitelist_levels = data.get("whitelist_levels", {})
    except FileNotFoundError:
        whitelist = []
        whitelist_levels = {}


def save_whitelist():
    with open("whitelist.json", "w") as f:
        json.dump({"whitelist": whitelist, "whitelist_levels": whitelist_levels}, f, indent=4)

@tree.command(name="excludechannel", description="Добавить или удалить канал из списка исключений")
@app_commands.describe(channel="Канал для добавления/удаления")
async def exclude_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    user_level = await check_whitelist_level(interaction.user.id)
    if user_level == 3:
        await interaction.response.send_message(
            "У вас недостаточно прав для использования этой команды. Требуется уровень 3 в вайтлисте.",
            ephemeral=True
        )
        return

    if channel.id in excluded_channels:
        excluded_channels.remove(channel.id)
        save_excluded_channels()
        await interaction.response.send_message(f"Канал {channel.mention} удалён из списка исключений.", ephemeral=True)
    else:
        excluded_channels.append(channel.id)
        save_excluded_channels()
        await interaction.response.send_message(f"Канал {channel.mention} добавлен в список исключений.", ephemeral=True)

@tree.command(name="whiteadd", description="Добавить пользователя в вайтлист")
@app_commands.describe(user="Пользователь, которого нужно добавить", level="Уровень доступа")
async def add_to_whitelist(interaction: discord.Interaction, user: discord.User, level: int):
    if interaction.user.guild_permissions.administrator:
        if user.id in whitelist:
            whitelist_levels[user.id] = max(whitelist_levels[user.id], level)
            await interaction.response.send_message(
                f"Пользователю {user} обновлён уровень доступа до {level}.", ephemeral=True
            )
        else:
            whitelist.append(user.id)
            whitelist_levels[user.id] = level
            await interaction.response.send_message(
                f"Пользователь {user} добавлен в вайтлист с уровнем {level}.", ephemeral=True
            )
        save_whitelist()
    else:
        await interaction.response.send_message(
            "У вас нет прав для использования этой команды.", ephemeral=True
        )


@tree.command(name="whiteremove", description="Удалить пользователя из вайтлиста")
@app_commands.describe(user="Пользователь, которого нужно удалить")
async def remove_from_whitelist(interaction: discord.Interaction, user: discord.User):
    if interaction.user.guild_permissions.administrator:
        if user.id in whitelist:
            whitelist.remove(user.id)
            if user.id in whitelist_levels:
                del whitelist_levels[user.id]
            save_whitelist()
            await interaction.response.send_message(
                f"Пользователь {user} удалён из вайтлиста.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Пользователь {user} не найден в вайтлисте.", ephemeral=True
            )
    else:
        await interaction.response.send_message(
            "У вас нет прав для использования этой команды.", ephemeral=True
        )


@tree.command(name="whiteshow", description="Показать вайтлист")
async def show_whitelist(interaction: discord.Interaction):
    if interaction.user.guild_permissions.administrator:
        if whitelist:
            whitelist_info = "\n".join(
                [f"{bot.get_user(user_id)} - Уровень {level}" for user_id, level in whitelist_levels.items()]
            )
            await interaction.response.send_message(f"Вайтлист:\n{whitelist_info}", ephemeral=True)
        else:
            await interaction.response.send_message("Вайтлист пуст.", ephemeral=True)
    else:
        await interaction.response.send_message(
            "У вас нет прав для использования этой команды.", ephemeral=True
        )


@tree.command(name="rolewhiteadd", description="Добавить пользователей с ролью в вайтлист")
@app_commands.describe(role="Роль для добавления", level="Уровень доступа")
async def add_role_to_whitelist(interaction: discord.Interaction, role: discord.Role, level: int):
    if interaction.user.guild_permissions.administrator:
        updated_users = []
        for member in role.members:
            if member.id in whitelist:
                old_level = whitelist_levels[member.id]
                whitelist_levels[member.id] = max(old_level, level)
                if old_level < level:
                    updated_users.append(member)
            else:
                whitelist.append(member.id)
                whitelist_levels[member.id] = level
                updated_users.append(member)
        save_whitelist()
        await interaction.response.send_message(
            f"Все участники ({len(updated_users)}) роли {role.name} добавлены в вайтлист с уровнем {level}.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message(
            "У вас нет прав для использования этой команды.", ephemeral=True
        )


@tree.command(name="rolewhiteremove", description="Удалить пользователей с ролью из вайтлиста")
@app_commands.describe(role="Роль для удаления из вайтлиста")
async def remove_role_from_whitelist(interaction: discord.Interaction, role: discord.Role):
    if interaction.user.guild_permissions.administrator:
        removed_users = []
        for member in role.members:
            if member.id in whitelist:
                whitelist.remove(member.id)
                whitelist_levels.pop(member.id, None)
                removed_users.append(member)
        save_whitelist()
        if removed_users:
            await interaction.response.send_message(
                f"Все участники ({len(removed_users)}) роли {role.name} удалены из вайтлиста.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Ни один пользователь с ролью {role.name} не находится в вайтлисте.", ephemeral=True
            )
    else:
        await interaction.response.send_message(
            "У вас нет прав для использования этой команды.", ephemeral=True
        )

async def check_whitelist_level(user_id):
    """Возвращает уровень доступа пользователя в вайтлисте или 0, если пользователя нет."""
    return whitelist_levels.get(user_id, 0)

load_whitelist()


def create_embed(action_title, user, reason, action, punishment, color, responsible_user=None):
    """Создание embed-сообщения для логов."""
    embed = discord.Embed(
        title=action_title,
        description=f"Причина: **{reason}**",
        color=color
    )
    embed.add_field(name="Действие", value=action, inline=False)
    if responsible_user:
        embed.add_field(name="Администратор", value=f"**{responsible_user}**", inline=True)
    embed.add_field(name="Наказание", value=punishment, inline=True)
    if user.avatar:
        embed.set_thumbnail(url=user.avatar.url)
    return embed


@tree.command(name="notify", description="Сделать рассылку всем участникам или определенной роли.")
@app_commands.describe(
    role="Роль для рассылки (необязательно, оставьте пустым для всех участников)",
    message="Сообщение для рассылки"
)
async def notify(interaction: discord.Interaction, message: str, role: discord.Role = None):
    user_level = whitelist_levels.get(interaction.user.id, 0)
    if user_level == 3:
        await interaction.response.send_message(
            "У вас недостаточно прав для выполнения этой команды. Требуется уровень 3 в вайтлисте.",
            ephemeral=True
        )
        return

    await interaction.response.send_message("Начинаю рассылку...", ephemeral=True)

    if role:
        members = role.members
    else:
        members = interaction.guild.members

    sent_count = 0

    embed = discord.Embed(
        title="Уведомление",
        description=message,
        color=discord.Color.blurple()
    )
    embed.set_footer(text=f"Отправлено: {interaction.user.name}", icon_url=interaction.user.avatar.url)

    # Рассылка сообщений
    for member in members:
        if not member.bot:
            try:
                await member.send(embed=embed)
                sent_count += 1
            except discord.Forbidden:
                continue

    # Отправляем итоговый результат
    await interaction.followup.send(
        f"Рассылка завершена. Сообщение было отправлено {sent_count} участникам.",
        ephemeral=True
    )


async def punish_user(member: discord.Member, reason: str, channel: discord.TextChannel, muted_role_name="Zamu4en"):
    """Применение наказания: снятие ролей (кроме исключенной) и мут на 1 день."""
    muted_role = discord.utils.get(member.guild.roles, name=muted_role_name)
    if not muted_role:
        muted_role = await member.guild.create_role(name=muted_role_name)
        for channel in member.guild.channels:
            await channel.set_permissions(muted_role, send_messages=False, speak=False)

    roles_to_remove = [role for role in member.roles if
                       role.id != 1318983350035153008 and role != member.guild.default_role]
    if roles_to_remove:
        await member.remove_roles(*roles_to_remove, reason=reason)

    await member.add_roles(muted_role, reason=reason)

    embed = discord.Embed(
        title="Наказание участника",
        description=f"Пользователь {member.mention} наказан.",
        color=discord.Color.red()
    )
    embed.add_field(name="Причина", value=reason, inline=False)
    embed.add_field(name="Наказание", value="Снятие всех ролей (кроме исключенной) и мут на 1 день", inline=False)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    await channel.send(embed=embed)

    # Снятие мута через 1 день
    await asyncio.sleep(86400)
    await member.remove_roles(muted_role, reason="Срок мута истек.")
    await channel.send(f"Мут для {member.mention} снят. Он может снова отправлять сообщения.")

@bot.event
async def on_member_ban(guild, user):
    channel = get_log_channel()
    if channel:
        level = await check_whitelist_level(user.id)
        if level == 3:
            return
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            responsible_user = entry.user
            reason = "Попытка сноса сервера"
            if level == 3 or responsible_user.id not in whitelist:
                await punish_user(user, reason, channel)
            else:
                embed = create_embed(
                    f"🛡️ Участник **{user}** был кикнут",
                    user,
                    reason,
                    "Пользователь был кикнут.",
                    "Кик.",
                    discord.Color.green(),
                    responsible_user
                )
                await channel.send(embed=embed)


@bot.event
async def on_member_remove(member):
    channel = get_log_channel()
    if channel:
        async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if entry.target.id == member.id:
                kicker = entry.user
                reason = "Кик участника без разрешения"
                level = await check_whitelist_level(kicker.id)
                if level == 3:
                    return
                if kicker.id not in whitelist:
                    await punish_user(kicker, reason, channel)
                else:
                    embed = create_embed(
                        f"🛡️ Участник **{member}** был кикнут",
                        member,
                        reason,
                        "Пользователь был кикнут.",
                        "Нет наказания.",
                        discord.Color.green(),
                        kicker
                    )
                    await channel.send(embed=embed)


@bot.event
async def on_guild_role_update(before, after):
    async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_update):
        if entry.target.id == after.id:
            changer = entry.user
            reason = "Изменение ролей с нарушением прав"
            level = await check_whitelist_level(changer.id)
            if level >= 2:
                return
            permissions_changed = [
                f"{'✅' if getattr(after.permissions, perm) else '❌'} {perm}"
                for perm in discord.Permissions.VALID_FLAGS
                if getattr(before.permissions, perm) != getattr(after.permissions, perm)
            ]
            if permissions_changed:
                if changer.id not in whitelist:
                    embed = create_embed(
                        f"🛑 Роль **{after.name}** была изменена",
                        changer,
                        reason,
                        "Роль была изменена без разрешения.",
                        "Роль изменена.",
                        discord.Color.red(),
                        changer
                    )
                    embed.add_field(name="Изменённые права", value="\n".join(permissions_changed), inline=False)
                    await changer.remove_roles(after)
                else:
                    embed = create_embed(
                        f"🛡️ Роль **{after.name}** была изменена",
                        changer,
                        reason,
                        "Роль была изменена с разрешения.",
                        "Нет наказания.",
                        discord.Color.green(),
                        changer
                    )
                    embed.add_field(name="Изменённые права", value="\n".join(permissions_changed), inline=False)
                channel = get_log_channel()
                await channel.send(embed=embed)
            break


@bot.event
async def on_guild_role_create(role):
    channel = get_log_channel()
    if channel:
        async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
            user = entry.user

            if user == bot.user:
                return

            reason = "Создание роли без разрешения"
            level = await check_whitelist_level(user.id)
            if level >= 2:
                return
            if user.id not in whitelist:
                embed = create_embed(
                    f"🛑 Была создана роль **{role}**",
                    user,
                    reason,
                    "Роль была создана без разрешения.",
                    "Роль создана.",
                    discord.Color.red(),
                    user
                )
                await role.guild.ban(user, reason=reason)
            else:
                embed = create_embed(
                    f"🛡️ Была создана роль **{role}**",
                    user,
                    reason,
                    "Роль была создана с разрешения.",
                    "Нет наказания.",
                    discord.Color.green(),
                    user
                )
            await channel.send(embed=embed)


@bot.event
async def on_guild_role_delete(role):
    channel = get_log_channel()
    if channel:
        async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            user = entry.user

            if user == bot.user:
                return

            reason = "Удаление роли без разрешения"
            level = await check_whitelist_level(user.id)
            if level >= 2:
                return
            if user.id not in whitelist:
                embed = create_embed(
                    f"🛑 Роль **{role.name}** была удалена",
                    user,
                    reason,
                    "Роль была удалена без разрешения.",
                    "Роль удалена.",
                    discord.Color.red(),
                    user
                )
                await role.guild.ban(user, reason=reason)
            else:
                embed = create_embed(
                    f"🛡️ Роль **{role.name}** была удалена",
                    user,
                    reason,
                    "Роль была удалена с разрешения.",
                    "Нет наказания.",
                    discord.Color.green(),
                    user
                )
            await channel.send(embed=embed)


@bot.event
async def on_member_update(before, after):
    channel = get_log_channel()
    added_roles = set(after.roles) - set(before.roles)
    for role in added_roles:
        if role.name and role.permissions.administrator:
            if channel:
                level = await check_whitelist_level(after.id)
                if level >= 2:
                    continue
                async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                    if entry.target.id == after.id:
                        admin_issuer = entry.user

                        if admin_issuer == bot.user:
                            return

                        reason = "Выдача роли с правами администратора без разрешения"
                        if level == 0 or admin_issuer.id not in whitelist:
                            embed = create_embed(
                                f"🛑 Была выдана роль с правами администратора **{role}** участнику **{after}**",
                                after,
                                reason,
                                "Роль была выдана без разрешения.",
                                "Роль снята.",
                                discord.Color.red(),
                                admin_issuer
                            )
                            await channel.send(embed=embed)
                            await after.remove_roles(role)
                        else:
                            embed = create_embed(
                                f"🛡️ Была выдана роль с правами администратора **{role}** участнику **{after}**",
                                after,
                                reason,
                                "Роль была выдана с разрешения.",
                                "Нет наказания.",
                                discord.Color.green(),
                                admin_issuer
                            )
                            await channel.send(embed=embed)


@bot.event
async def on_guild_channel_create(channel):
    channel1 = get_log_channel()
    if channel.guild:
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
            level = await check_whitelist_level(entry.user.id)
            if level == 3:
                return

            if entry.user.id not in whitelist:
                reason = "Создание канала без разрешения"
                embed = create_embed(
                    f"🛑 Был создан канал **{channel.name}**",
                    channel.guild.owner,
                    reason,
                    f"Создатель: **{entry.user}**",
                    "Канал удалён, бан.",
                    discord.Color.red(),
                    entry.user
                )
                await channel1.send(embed=embed)
                await channel.delete(reason="Создание канала без разрешения")
                await entry.user.ban(reason="Попытка сноса сервера!")
            else:
                embed = create_embed(
                    f"🛡️ Был создан канал **{channel.name}**",
                    channel.guild.owner,
                    "Создание канала с разрешения.",
                    f"Создатель: **{entry.user}**",
                    "Нет наказания.",
                    discord.Color.green(),
                    entry.user
                )
                await channel1.send(embed=embed)


@bot.event
async def on_guild_channel_delete(channel):
    channel1 = get_log_channel()
    if channel.guild:
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            previous_channels[channel.id] = {
                'name': channel.name,
                'position': channel.position,
                'overwrites': channel.overwrites,
                'category_id': channel.category_id
            }
            reason = "Удаление канала без разрешения"
            level = await check_whitelist_level(entry.user.id)
            if level == 3:
                return

            if entry.user.id not in whitelist:
                await punish_user(entry.user, reason, channel1, excluded_role_id=1318983350035153008)

                embed = create_embed(
                    f"🛑 Был удален канал **{channel.name}**",
                    channel.guild.owner,
                    reason,
                    f"Удалил: **{entry.user}**",
                    "Канал восстановлен, наказание применено.",
                    discord.Color.red(),
                    entry.user
                )
                await channel1.send(embed=embed)
                await restore_channel(channel.guild, previous_channels[channel.id])
            else:
                embed = create_embed(
                    f"🛡️ Был удален канал **{channel.name}**",
                    channel.guild.owner,
                    reason,
                    f"Удалил: **{entry.user}**",
                    "Нет наказания.",
                    discord.Color.green(),
                    entry.user
                )
                await channel1.send(embed=embed)


async def restore_channel(guild, channel_data):
    try:
        category = guild.get_channel(channel_data['category_id']) if channel_data['category_id'] else None
        restored_channel = await guild.create_text_channel(
            name=channel_data['name'],
            position=channel_data['position'],
            overwrites=channel_data['overwrites'],
            category=category
        )
        print(
            f'Канал {restored_channel.name} был восстановлен в категорию {category.name if category else "без категории"}.')
    except discord.HTTPException as e:
        print(f'Не удалось восстановить канал: {e}')


@bot.event
async def on_message(message):
    if message.author == bot.user or message.channel.id in excluded_channels:
        return

    author_id = message.author
    author_id1 = message.author.id
    muted_role_name = "Zamu4en"
    channel = get_log_channel()
    muted_role = discord.utils.get(message.guild.roles, name=muted_role_name)

    level = await check_whitelist_level(author_id1)
    if level >= 1:
        return

    if author_id1 in whitelist:
        return

    content = message.content.lower()
    banned_words = ["http", "https", ".com", ",com", ",gg", ".gg", ".ru", "ru", ".net", ",net", "gg/", "gg /", ".fun",
                    ",fun"]
    for word in banned_words:
        if word in content:
            reason = "Отправка ссылки"
            punishment = "Замучен+сняты роли"
            embed = create_embed(
                f"🛡️ **{author_id}** был замучен за отправку ссылок",
                message.author,
                reason,
                f"Сообщение: {message.content}",
                punishment,
                discord.Color.red()
            )
            await channel.send(embed=embed)
            await message.delete()
            await punish_user(message.author, reason, channel)  # Применение наказания
            break
        else:
            if not muted_role:
                muted_role = await message.guild.create_role(name=muted_role_name)
                for ch in message.guild.channels:
                    await ch.set_permissions(muted_role, send_messages=False)
            await message.author.add_roles(muted_role)

    if author_id1 not in whitelist:
        if author_id in spam_count:
            similarity = similar(message.content, spam_count[author_id]['last_message'])
            if similarity >= 0.75:
                spam_count[author_id]['count'] += 1
                if spam_count[author_id]['count'] > 2:
                    reason = "Спам"
                    punishment = "Забанен"
                    embed = create_embed(
                        f"🛡️ **{author_id}** был замучен за спам",
                        message.author,
                        reason,
                        f"Сообщение: {message.content}",
                        punishment,
                        discord.Color.red()
                    )
                    await channel.send(embed=embed)
                    await message.author.ban(reason='Попытка рейда')
                    async for hist_message in message.channel.history(limit=10):
                        if similar(hist_message.content, message.content) >= 0.75:
                            await hist_message.delete()
                    spam_count[author_id]['count'] = 0
                else:
                    spam_count[author_id] = {'count': 1, 'last_message': message.content}
            else:
                spam_count[author_id] = {'count': 1, 'last_message': message.content}
        else:
            spam_count[author_id] = {'count': 1, 'last_message': message.content}

    spam_count[author_id]['last_message'] = message.content
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"Bot is logged in as {bot.user}")
    await bot.tree.sync()
    print("Slash-команды синхронизированы.")



bot_token = ""

bot.run(bot_token)
