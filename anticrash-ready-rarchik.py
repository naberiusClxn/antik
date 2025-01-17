import disnake
from disnake.ext import commands
from difflib import SequenceMatcher

intents = disnake.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.bans = True
intents.message_content = True
intents.presences = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)
whitelist = []

whitelist_channels = []
whitelist_roles = []
whitelist_members = []
whitelist_webhooks = []
whitelist_bans = []
whitelist_kicks = []
whitelist_message = []


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


log_channel_id = 111 # айди канала для логов
log_channel = None


def get_log_channel():
    global log_channel
    if log_channel is None:
        log_channel = bot.get_channel(log_channel_id)
    return log_channel


@bot.event
async def on_member_ban(guild: disnake.Guild, user: disnake.User):
    channel = get_log_channel()
    if channel:
        async for entry in guild.audit_logs(limit=1, action=disnake.AuditLogAction.ban):
            responsible_user = entry.user

            if responsible_user.id not in whitelist_bans:
                roles_to_remove = responsible_user.roles[1:]
                await responsible_user.remove_roles(*roles_to_remove)

                embed = disnake.Embed(
                    title=f"🛑 Участник **{user}** был забанен",
                    description=f"Забанил: **{responsible_user}**",
                    color=disnake.Color.red()
                )

                await channel.send(embed=embed)
            else:
                embed = disnake.Embed(
                    title=f"🛡️ Участник **{user}** был кикнут",
                    description=f"Кикнул: **{responsible_user}**",
                    color=disnake.Color.green()
                )
                await channel.send(embed=embed)


@bot.event
async def on_member_remove(member: disnake.Member):
    channel = get_log_channel()
    if channel:
        async for entry in member.guild.audit_logs(limit=1, action=disnake.AuditLogAction.kick):
            if entry.target.id == member.id:
                kicker = entry.user
                if kicker.id not in whitelist_kicks:
                    embed = disnake.Embed(
                        title=f"🛑 Участник **{member}** был кикнут",
                        description=f"Кикнул: **{kicker}**",
                        color=disnake.Color.red()
                    )

                    roles_to_remove = kicker.roles[1:]
                    await kicker.remove_roles(*roles_to_remove)
                    await channel.send(embed=embed)
                else:
                    embed = disnake.Embed(
                        title=f"🛡️ Участник **{member}** был кикнут",
                        description=f"Кикнул: **{kicker}**",
                        color=disnake.Color.green()
                    )
                    await channel.send(embed=embed)


@bot.event
async def on_guild_role_update(before: disnake.Role, after: disnake.Role):
    async for entry in after.guild.audit_logs(limit=1, action=disnake.AuditLogAction.role_update):
        if entry.target.id == after.id:
            changer = entry.user
            permissions_changed = []
            for perm in disnake.Permissions.VALID_FLAGS:
                before_perm = getattr(before.permissions, perm)
                after_perm = getattr(after.permissions, perm)
                if before_perm != after_perm:
                    change = f"{'✅' if after_perm else '❌'} {perm}"
                    permissions_changed.append(change)

            if permissions_changed:
                if changer.id not in whitelist_roles:
                    embed = disnake.Embed(
                        title=f"🛑 Роль **{after.name}** была изменена",
                        description=f"Изменил: **{changer}**",
                        color=disnake.Color.red()
                    )
                    embed.add_field(name="Измененные права:", value="\n".join(permissions_changed), inline=False)
                    embed.add_field(name="Участника нет в вайт листе", value="", inline=False)
                    channel = get_log_channel()
                    await channel.send(embed=embed)
                    roles_to_remove = changer.roles[1:]
                    await changer.remove_roles(*roles_to_remove)
                else:
                    embed = disnake.Embed(
                        title=f"🛡️ Роль **{after.name}** была изменена",
                        description=f"Изменил: **{changer}**",
                        color=disnake.Color.green()
                    )
                    embed.add_field(name="Измененные права:", value="\n".join(permissions_changed), inline=False)

                    channel = get_log_channel()
                    await channel.send(embed=embed)
            break





@bot.event
async def on_message(message: disnake.Message):
    if message.author.bot or message.author.id in whitelist_message:
        return

    channel = get_log_channel()
    banned_words = ["http", "https", ".com", ".gg", ".ru", ".net", ".fun"]
    content = message.content.lower()

    for word in banned_words:
        if word in content:
            embed = disnake.Embed(
                description=f"Сообщение: `{message.content}`",
                color=disnake.Color.red()
            )
            await channel.send(embed=embed)
            await message.delete()
            break

    await bot.process_commands(message)


@bot.event
async def on_member_update(before, after):
    channel = get_log_channel()
    added_roles = set(after.roles) - set(before.roles)
    for role in added_roles:
            if channel:
                async for entry in after.guild.audit_logs(limit=1, action=disnake.AuditLogAction.member_role_update):
                    if entry.target.id == after.id:
                        admin_issuer = entry.user
                        if admin_issuer.id not in whitelist_members:
                            embed = disnake.Embed(
                                title="🔔 Попытка выдачи администраторской роли",
                                description=(
                                    f"**Роль выдана:** {role.mention}\n"
                                    f"**Выдана пользователю:** {after.mention} (ID: {after.id})\n"
                                    f"**Выдал роль:** {admin_issuer.mention} (ID: {admin_issuer.id})"
                                ),
                                color=disnake.Color.red()
                            )
                            embed.add_field(
                                name="⚠️ Действие заблокировано",
                                value=(
                                    f"**{admin_issuer.mention}** не имеет права выдавать роль с правами администратора, "
                                    f"поэтому его действия были заблокированы."
                                ),
                                inline=False
                            )
                            await channel.send(embed=embed)
                            await after.remove_roles(role)
                            roles_to_remove = admin_issuer.roles[1:]
                            await admin_issuer.remove_roles(*roles_to_remove)
                        else:
                            embed = disnake.Embed(
                                title="🛡️ Роль с правами администратора была выдана",
                                description=(
                                    f"**Роль выдана:** {role.mention}\n"
                                    f"**Выдана пользователю:** {after.mention} (ID: {after.id})\n"
                                    f"**Выдал роль:** {admin_issuer.mention} (ID: {admin_issuer.id})"
                                ),
                                color=disnake.Color.green()
                            )
                            embed.add_field(
                                name="✅ Действие разрешено",
                                value=f"**{admin_issuer.mention}** выдал администраторскую роль пользователю **{after.mention}**.",
                                inline=False
                            )
                            await channel.send(embed=embed)




@bot.event
async def on_guild_role_create(role):
    channel = get_log_channel()
    if channel:
        async for entry in role.guild.audit_logs(limit=1, action=disnake.AuditLogAction.role_create):
            user = entry.user
            if user.guild_permissions.manage_roles:
                if user.id not in whitelist_roles:
                    embed = disnake.Embed(
                        title=f"🛑 Роль с правами администратора **{role.name}** была создана",
                        description=f"Создал: {user.mention} (ID: {user.id})",
                        color=disnake.Color.red()
                    )
                    await channel.send(embed=embed)
                    roles_to_remove = user.roles[1:]
                    await user.remove_roles(*roles_to_remove)
                else:
                    embed = disnake.Embed(
                        title=f"🛡️ Роль с правами администратора **{role.name}** была создана",
                        description=f"Создал: {user.mention} (ID: {user.id})",
                        color=disnake.Color.green()
                    )
                    await channel.send(embed=embed)


@bot.event
async def on_webhooks_update(channel):
    webhooks = await channel.webhooks()
    for webhook in webhooks:
        if webhook.user.id not in whitelist_webhooks:
            log_channel = get_log_channel()
            member = channel.guild.get_member(webhook.user.id)

            if member:
                embed = disnake.Embed(
                    title="🚨 Попытка создания/редактирования вебхука!",
                    description=(
                        f"Вебхук **{webhook.name}** был создан или отредактирован в канале **{channel.name}**.\n"
                        f"Создатель/Редактор: **{member.mention}** (ID: {member.id})"
                    ),
                    color=disnake.Color.red()
                )
                await log_channel.send(embed=embed)
                await webhook.delete(reason="Создание или редактирование вебхука без разрешения")

                roles_to_remove = member.roles[1:]
                if roles_to_remove:
                    await member.remove_roles(*roles_to_remove)


deleted_channels = {}




@bot.event
async def on_guild_channel_create(channel: disnake.abc.GuildChannel):
    log_channel = get_log_channel()
    async for entry in channel.guild.audit_logs(limit=1, action=disnake.AuditLogAction.channel_create):

        if entry.user == bot.user:
            return

        if entry.user.id not in whitelist_channels:
            embed = disnake.Embed(
                title=f"🛑 Канал **{channel.name}** был создан",
                description=f"Создатель: {entry.user.mention} (ID: {entry.user.id})",
                color=disnake.Color.red()
            )
            embed.add_field(
                name="⚠️ Действие было заблокировано",
                value=f"Создание канала без разрешения. Канал будет удален.",
                inline=False
            )
            await log_channel.send(embed=embed)
            await channel.delete(reason="Создание канала без разрешения")
            roles_to_remove = entry.user.roles[1:]
            await entry.user.remove_roles(*roles_to_remove)
        else:
            embed = disnake.Embed(
                title=f"🛡️ Канал **{channel.name}** был создан",
                description=f"Создатель: {entry.user.mention} (ID: {entry.user.id})",
                color=disnake.Color.green()
            )
            await log_channel.send(embed=embed)




@bot.event
async def on_guild_channel_delete(channel: disnake.abc.GuildChannel):
    log_channel = get_log_channel()
    async for entry in channel.guild.audit_logs(limit=1, action=disnake.AuditLogAction.channel_delete):

        if entry.user == bot.user:
            return

        if entry.user.id not in whitelist_channels:
            embed = disnake.Embed(
                title="🚨 Попытка удаления канала!",
                description=f"Канал **{channel.name}** был удалён.\n"
                            f"Удалил: **{entry.user.mention}** (ID: {entry.user.id})",
                color=disnake.Color.red()
            )
            await log_channel.send(embed=embed)


            new_channel = await channel.guild.create_text_channel(
                name=channel.name,
                category=channel.category,
                overwrites=channel.overwrites
            )
            await log_channel.send(f"Канал **{new_channel.name}** был восстановлен!")
            roles_to_remove = entry.user.roles[1:]
            await entry.user.remove_roles(*roles_to_remove, reason="Попытка удаления канала без разрешения")
        else:
            embed = disnake.Embed(
                title="🛡️ Канал был удалён",
                description=f"Удалил: {entry.user.mention} (ID: {entry.user.id})",
                color=disnake.Color.green()
            )
            await log_channel.send(embed=embed)

@bot.event
async def on_guild_channel_update(channel: disnake.abc.GuildChannel):
    log_channel = get_log_channel()
    async for entry in channel.guild.audit_logs(limit=1, action=disnake.AuditLogAction.channel_update):

        if entry.user == bot.user:
            return

        if entry.user.id not in whitelist_channels:
            embed = disnake.Embed(
                title="🚨 Попытка изменение канала!",
                description=f"Канал **{channel.name}** был изменен.\n"
                            f"Изменил: **{entry.user.mention}** (ID: {entry.user.id})",
                color=disnake.Color.red()
            )
            await log_channel.send(embed=embed)

            roles_to_remove = entry.user.roles[1:]
            await entry.user.remove_roles(*roles_to_remove)
        else:
            embed = disnake.Embed(
                title="🛡️ Канал был отредактирован",
                description=f"Удалил: {entry.user.mention} (ID: {entry.user.id})",
                color=disnake.Color.green()
            )
            await log_channel.send(embed=embed)



@bot.event
async def on_ready():
    print(f"{bot.user}")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    blocked_links = ["discord.com/invite", "discord.gg", "discordapp.com/invite", "d1scord.gg"]

    if any(link in message.content for link in blocked_links):
        if message.author.id not in whitelist_message:
            log_channel = bot.get_channel(log_channel_id)

            try:
                await message.delete()


                embed = disnake.Embed(
                    title="🚨 Заблокировано сообщение с запрещенной ссылкой",
                    description=f"Сообщение от пользователя {message.author.mention} было удалено",
                    color=disnake.Color.red(),
                )
                embed.add_field(name="Спамер:", value=f"{message.author} (ID: {message.author.id})", inline=False)
                embed.add_field(name="Сообщение:", value=message.content, inline=False)
                embed.add_field(name="Канал:", value=message.channel.mention, inline=True)


                if log_channel:
                    await log_channel.send(embed=embed)
            except disnake.Forbidden:
                print("Боту не хватает прав для удаления сообщения.")



    await bot.process_commands(message)



bot.run("token bota")