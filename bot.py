"""
Телеграм-бот регистрации участников турнира по Mortal Kombat 1.

Функции:
- Участникам:
  * /start («📝 Зарегистрироваться») — регистрация (Имя + Никнейм)
  * /rules («📜 Правила и время») — правила, условия и время турнира
  * /mystatus («👤 Мой статус») — статус своей регистрации
  * /unregister («❌ Отменить регистрацию») — удаление своей регистрации
  * /help («❓ Помощь») — помощь

- Администраторам (доступ только для ID из ADMIN_IDS в .env):
  * /admin — открыть панель администратора с кнопками
  * /participants («📊 Список участников») — полный список со статусами
  * /unconfirmed («⏳ Неподтверждённые») — кто ещё не подтвердился
  * /export («📁 Выгрузить CSV») — файл CSV для Excel/Challonge
  * /broadcast <текст> — рассылка всем участникам
  * /reset confirm — сбросить базу участников
"""
import os
import logging
from datetime import timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeChat,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
import database as db


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния диалога регистрации
NAME, NICKNAME = range(2)

CONFIRM_YES = "confirm_yes"
CONFIRM_NO = "confirm_no"


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


def get_main_keyboard(user_id: int = None):
    keyboard = [
        ["🌐 Турнирная сетка", "📜 Правила и время"],
        ["📝 Зарегистрироваться", "👤 Мой статус"],
        ["❌ Отменить регистрацию", "💬 Написать в техподдержку"],
        ["❓ Помощь"],
    ]
    if user_id and is_admin(user_id):
        keyboard.append(["⚙️ Админ-панель"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)




def get_admin_keyboard():
    keyboard = [
        ["📊 Список участников", "⏳ Неподтверждённые"],
        ["🎲 Заполнить недостающих игроков"],
        ["📁 Выгрузить CSV", "⬅️ Главное меню"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ---------- Регистрация ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    existing = db.get_participant(user_id)
    keyboard = get_main_keyboard(user_id)

    if existing:
        status_str = "✅ подтверждено" if existing["confirmed"] else "⏳ ожидает подтверждения"
        await update.message.reply_text(
            f"Вы уже зарегистрированы на {config.TOURNAMENT_NAME}!\n\n"
            f"👤 Имя: {existing['name']}\n"
            f"🎮 Никнейм: {existing['nickname']}\n"
            f"📌 Статус участия: {status_str}\n\n"
            f"Используйте меню ниже для просмотра информации.",
            reply_markup=keyboard,
        )
        return ConversationHandler.END

    if config.MAX_PARTICIPANTS and db.count_participants() >= config.MAX_PARTICIPANTS:
        await update.message.reply_text(
            "К сожалению, регистрация закрыта — набрано максимальное число участников.",
            reply_markup=keyboard,
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"🏆 Добро пожаловать на регистрацию: <b>{config.TOURNAMENT_NAME}</b>!\n\n"
        "Шаг 1 из 2: Как вас зовут? (Введите ваше имя)",
        parse_mode=ParseMode.HTML,
    )
    return NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("Имя слишком короткое. Введите ваше имя (от 2 символов):")
        return NAME
    context.user_data["reg_name"] = name
    await update.message.reply_text(
        f"Принято, {name}!\n\n"
        "Шаг 2 из 2: Укажите ваш игровой Никнейм (Gamertag / PSN ID / Steam / WB ID):"
    )
    return NICKNAME


async def receive_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nickname = update.message.text.strip()
    if len(nickname) < 2:
        await update.message.reply_text("Никнейм слишком короткий. Укажите ваш игровой никнейм:")
        return NICKNAME

    user = update.effective_user
    name = context.user_data.get("reg_name")
    db.add_participant(user.id, user.username or "", name, nickname)

    keyboard = get_main_keyboard(user.id)
    await update.message.reply_text(
        f"🎉 <b>Регистрация успешно завершена!</b>\n\n"
        f"👤 <b>Имя:</b> {name}\n"
        f"🎮 <b>Никнейм:</b> {nickname}\n\n"
        f"📜 Правила и время — кнопка «📜 Правила и время» или /rules.\n"
        f"⏰ За 24 часа до турнира я пришлю вам напоминание с кнопкой подтверждения участия!",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )

    # Уведомление админам
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"📥 <b>Новая регистрация!</b>\n"
                f"• Имя: {name}\n"
                f"• Никнейм: {nickname}\n"
                f"• Telegram: @{user.username or 'без username'} (ID: {user.id})",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            logger.exception("Не удалось уведомить админа %s", admin_id)

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = get_main_keyboard(update.effective_user.id)
    await update.message.reply_text("Регистрация отменена.", reply_markup=keyboard)
    return ConversationHandler.END


# ---------- Информационные команды ----------

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    when = (
        config.TOURNAMENT_DATETIME.strftime("%d.%m.%Y в %H:%M")
        if config.TOURNAMENT_DATETIME
        else "будет объявлено дополнительно"
    )
    rules_content = config.load_rules()
    text = (
        f"<b>{config.TOURNAMENT_NAME}</b>\n"
        f"📅 <b>Дата и время проведения:</b> {when}\n\n"
        f"{rules_content}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard(update.effective_user.id))


async def mystatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = db.get_participant(update.effective_user.id)
    if not p:
        await update.message.reply_text(
            "Вы ещё не зарегистрированы. Нажмите «📝 Зарегистрироваться» или отправьте /start",
            reply_markup=get_main_keyboard(update.effective_user.id),
        )
        return
    status = "подтверждено ✅" if p["confirmed"] else "ожидает подтверждения ⏳"
    await update.message.reply_text(
        f"📋 <b>Ваш профиль участника:</b>\n\n"
        f"👤 <b>Имя:</b> {p['name']}\n"
        f"🎮 <b>Никнейм:</b> {p['nickname']}\n"
        f"📌 <b>Статус участия:</b> {status}",
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_keyboard(update.effective_user.id),
    )


async def unregister(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    p = db.get_participant(user_id)
    if not p:
        await update.message.reply_text("Вы не зарегистрированы.", reply_markup=get_main_keyboard(user_id))
        return

    db.remove_participant(user_id)
    await update.message.reply_text(
        "Ваша регистрация удалена.",
        reply_markup=get_main_keyboard(user_id),
    )
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"🗑 <b>Участник отменил регистрацию:</b>\n{p['name']} ({p['nickname']})",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            logger.exception("Не удалось уведомить админа %s", admin_id)


# ---------- Подтверждение участия ----------

async def send_confirmation_request(context: ContextTypes.DEFAULT_TYPE):
    """Отправляется за REMINDER_HOURS_BEFORE до турнира."""
    participants = db.get_all_participants()
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Подтверждаю участие", callback_data=CONFIRM_YES),
                InlineKeyboardButton("❌ Не смогу прийти", callback_data=CONFIRM_NO),
            ]
        ]
    )
    when = (
        config.TOURNAMENT_DATETIME.strftime("%d.%m.%Y в %H:%M")
        if config.TOURNAMENT_DATETIME
        else ""
    )
    for p in participants:
        try:
            await context.bot.send_message(
                p["telegram_id"],
                f"⏰ <b>НАПОМИНАНИЕ О ТУРНИРЕ!</b>\n\n"
                f"Турнир <b>{config.TOURNAMENT_NAME}</b> состоится через 24 часа ({when}).\n\n"
                f"Пожалуйста, подтвердите ваше участие кнопкой ниже:",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )
        except Exception:
            logger.exception("Не удалось отправить напоминание %s", p["telegram_id"])


async def confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    p = db.get_participant(user_id)

    if query.data == CONFIRM_YES:
        db.set_confirmed(user_id, True)
        await query.edit_message_text("Отлично! Ваше участие подтверждено ✅ Ждём вас на турнире!")
        for admin_id in config.ADMIN_IDS:
            try:
                name_str = p['name'] if p else str(user_id)
                nick_str = p['nickname'] if p else ""
                await context.bot.send_message(
                    admin_id,
                    f"✅ <b>Участник подтвердил участие:</b> {name_str} ({nick_str})",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                logger.exception("Не удалось уведомить админа %s", admin_id)
    elif query.data == CONFIRM_NO:
        db.set_confirmed(user_id, False)
        await query.edit_message_text(
            "Ваш статус изменён: не сможет прийти ❌.\nЕсли планы изменятся, свяжитесь с организатором."
        )
        for admin_id in config.ADMIN_IDS:
            try:
                name_str = p['name'] if p else str(user_id)
                nick_str = p['nickname'] if p else ""
                await context.bot.send_message(
                    admin_id,
                    f"⚠️ <b>Участник отказался от участия:</b> {name_str} ({nick_str})",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                logger.exception("Не удалось уведомить админа %s", admin_id)



async def notify_admin_unconfirmed(context: ContextTypes.DEFAULT_TYPE):
    unconfirmed = db.get_unconfirmed()
    if not unconfirmed:
        text = "✅ Все зарегистрированные участники подтвердили участие!"
    else:
        lines = "\n".join(f"• {p['name']} ({p['nickname']}) — @{p['username'] or p['telegram_id']}" for p in unconfirmed)
        text = f"⚠️ <b>Участники, не подтвердившие участие ({len(unconfirmed)}):</b>\n\n{lines}"
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, text, parse_mode=ParseMode.HTML)
        except Exception:
            logger.exception("Не удалось уведомить админа %s", admin_id)


# ---------- Админ-команды ----------

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("У вас нет прав администратора.")
        return
    await update.message.reply_text(
        "⚙️ <b>Панель администратора:</b>\n\n Выберите нужное действие на клавиатуре:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_admin_keyboard(),
    )


async def main_menu_return(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Главное меню:",
        reply_markup=get_main_keyboard(update.effective_user.id),
    )


async def participants_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("У вас нет прав администратора.")
        return
    rows = db.get_all_participants()
    if not rows:
        await update.message.reply_text("Пока никто не зарегистрирован.")
        return
    lines = []
    for i, p in enumerate(rows, 1):
        status = "✅" if p["confirmed"] else "⏳"
        username_str = f" (@{p['username']})" if p["username"] else ""
        lines.append(f"{i}. {p['name']} | Ник: <b>{p['nickname']}</b>{username_str} — {status}")
    await update.message.reply_text(
        f"📊 <b>Зарегистрировано ({len(rows)}/{config.MAX_PARTICIPANTS}):</b>\n\n" + "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=get_admin_keyboard(),
    )


async def unconfirmed_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("У вас нет прав администратора.")
        return
    rows = db.get_unconfirmed()
    if not rows:
        await update.message.reply_text("Все участники подтвердили участие ✅")
        return
    lines = [f"• {p['name']} ({p['nickname']}) — @{p['username'] or p['telegram_id']}" for p in rows]
    await update.message.reply_text(
        "⏳ <b>Еще не подтвердили участие:</b>\n\n" + "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=get_admin_keyboard(),
    )


async def fill_random_players_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("У вас нет прав администратора.")
        return

    current_count = db.count_participants()
    max_p = config.MAX_PARTICIPANTS or 16
    needed = max_p - current_count

    if needed <= 0:
        await update.message.reply_text(
            f"ℹ️ <b>Турнирная сетка уже полностью укомплектована!</b>\n\n"
            f"Зарегистрировано участников: <b>{current_count} / {max_p}</b> ✅\n"
            f"Все слоты заняты. Добавление случайных игроков не требуется.",
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard(),
        )
        return

    added = db.fill_missing_participants(target_count=max_p)
    if not added:
        await update.message.reply_text(
            "Не удалось добавить участников или турнир уже заполнен.",
            reply_markup=get_admin_keyboard(),
        )
        return

    lines = []
    for i, p in enumerate(added, 1):
        username_part = f" (@{p['username']})" if p.get("username") else ""
        lines.append(f"{i}. {p['name']} | Ник: <b>{p['nickname']}</b>{username_part}")

    total_now = current_count + len(added)
    report_text = (
        f"🎲 <b>Успешно добавлено {len(added)} недостающих игроков!</b>\n"
        f"📊 Итого в турнире: <b>{total_now} / {max_p}</b> бойцов ✅\n\n"
        f"<b>Добавленные участники:</b>\n"
        + "\n".join(lines) + "\n\n"
        f"🏆 <b>Турнирная сетка сформирована!</b>\n"
        f"Все {max_p} участников распределены по парам Double Elimination.\n"
        f"🌐 Сетка доступна на сайте: {config.WEB_URL}"
    )

    await update.message.reply_text(
        report_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_admin_keyboard(),
    )


async def export_csv_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("У вас нет прав администратора.")
        return
    csv_file = db.export_to_csv()
    if os.path.exists(csv_file):
        with open(csv_file, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename="participants.csv",
                caption="📊 Экспорт всех участников турнира для Excel/Challonge",
                reply_markup=get_admin_keyboard(),
            )
    else:
        await update.message.reply_text("Ошибка при экспорте CSV.")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("У вас нет прав администратора.")
        return
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Использование: `/broadcast <текст сообщения>`", parse_mode=ParseMode.MARKDOWN)
        return
    rows = db.get_all_participants()
    sent = 0
    for p in rows:
        try:
            await context.bot.send_message(
                p["telegram_id"],
                f"📢 <b>Объявление от организаторов:</b>\n\n{text}",
                parse_mode=ParseMode.HTML,
            )
            sent += 1
        except Exception:
            logger.exception("Не удалось отправить %s", p["telegram_id"])
    await update.message.reply_text(f"📢 Сообщение отправлено {sent}/{len(rows)} участникам.")


async def reset_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("У вас нет прав администратора.")
        return
    if not context.args or context.args[0].lower() != "confirm":
        await update.message.reply_text(
            "⚠️ Это полностью удалит всех зарегистрированных участников!\n"
            "Чтобы подтвердить, отправьте: `/reset confirm`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    db.reset_all()
    await update.message.reply_text("🗑 База участников успешно очищена.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = (
        "<b>Команды участника:</b>\n"
        "🌐 /bracket — Турнирная сетка (Сайт)\n"
        "📝 /start — Регистрация на турнир\n"
        "📜 /rules — Правила, регламент и время\n"
        "👤 /mystatus — Ваш статус и профиль\n"
        "❌ /unregister — Отменить регистрацию\n"
        "💬 /support — Написать в техподдержку\n"
        "❓ /help — Справка\n"
    )
    if is_admin(user_id):
        text += (
            "\n<b>Команды организатора:</b>\n"
            "⚙️ /admin — Открыть админ-панель\n"
            "🎲 /fill_random — Заполнить недостающих игроков случайными именами\n"
            "📊 /participants — Список участников\n"
            "⏳ /unconfirmed — Список неподтверждённых\n"
            "📁 /export — Скачать список в CSV\n"
            "📢 /broadcast текст — Рассылка игрокам\n"
            "🗑 /reset confirm — Сбросить базу данных\n"
        )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard(user_id))


async def bracket_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = config.WEB_URL
    reply_markup = None
    if url and not ("localhost" in url or "127.0.0.1" in url):
        buttons = [[InlineKeyboardButton("🌐 Открыть сетку на сайте", url=url)]]
        reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        f"🏆 <b>Интерактивная сетка турнира {config.TOURNAMENT_NAME}:</b>\n\n"
        f"Смотрите результаты матчей, расписание и прогресс турнира в реальном времени на нашем сайте:\n"
        f"👉 <b>{url}</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
    )


async def support_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = []
    if config.ORGANIZER_USERNAME:
        url = f"https://t.me/{config.ORGANIZER_USERNAME}"
        buttons.append([InlineKeyboardButton("💬 Написать организатору", url=url)])
    elif config.ADMIN_IDS:
        url = f"tg://user?id={config.ADMIN_IDS[0]}"
        buttons.append([InlineKeyboardButton("💬 Написать организатору", url=url)])

    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
    await update.message.reply_text(
        "💬 <b>Техподдержка и связь с организатором:</b>\n\n"
        "Если у вас возникли вопросы по проведению турнира, правилам или вам нужно отредактировать ваши данные — "
        "нажмите кнопку ниже, чтобы перейти в личный диалог с организатором:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
    )


async def post_init(application: Application):
    """Настройка подсказок меню команд в Telegram для обычных юзеров и админа."""
    user_commands = [
        BotCommand("bracket", "Интерактивная сетка на сайте"),
        BotCommand("start", "Регистрация на турнир"),
        BotCommand("rules", "Правила и время турнира"),
        BotCommand("mystatus", "Мой статус участия"),
        BotCommand("unregister", "Отменить регистрацию"),
        BotCommand("support", "Написать в техподдержку"),
        BotCommand("help", "Справка"),
    ]


    await application.bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    admin_commands = user_commands + [
        BotCommand("admin", "⚙️ Панель администратора"),
        BotCommand("fill_random", "🎲 Заполнить недостающих игроков"),
        BotCommand("participants", "📊 Список участников"),
        BotCommand("unconfirmed", "⏳ Неподтверждённые"),
        BotCommand("export", "📁 Скачать CSV для Excel"),
        BotCommand("broadcast", "📢 Рассылка игрокам"),
        BotCommand("reset", "🗑 Сбросить участников"),
    ]
    for admin_id in config.ADMIN_IDS:
        try:
            await application.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception:
            logger.warning("Не удалось установить админ-команды для ID %s", admin_id)


# ---------- Планирование задач ----------

def schedule_jobs(application: Application):
    if not config.TOURNAMENT_DATETIME:
        logger.warning(
            "TOURNAMENT_DATETIME не задан в .env — автонапоминания не запланированы."
        )
        return

    reminder_time = config.TOURNAMENT_DATETIME - timedelta(
        hours=config.REMINDER_HOURS_BEFORE
    )
    check_time = reminder_time + timedelta(hours=config.CONFIRMATION_CHECK_HOURS_AFTER)

    application.job_queue.run_once(
        send_confirmation_request, when=reminder_time, name="send_confirmation_request"
    )
    application.job_queue.run_once(
        notify_admin_unconfirmed, when=check_time, name="notify_admin_unconfirmed"
    )
    logger.info("Напоминание запланировано на %s", reminder_time)
    logger.info("Проверка неподтверждённых запланирована на %s", check_time)


def main():
    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.warning("BOT_TOKEN не заполнен в файле .env!")

    db.init_db()

    application = ApplicationBuilder().token(config.BOT_TOKEN).post_init(post_init).build()

    reg_conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("^📝 Зарегистрироваться$"), start),
        ],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_nickname)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(reg_conv)
    application.add_handler(CommandHandler("bracket", bracket_handler))
    application.add_handler(MessageHandler(filters.Regex("^🌐 Турнирная сетка$"), bracket_handler))
    application.add_handler(CommandHandler("rules", rules))
    application.add_handler(MessageHandler(filters.Regex("^📜 Правила и время$"), rules))
    application.add_handler(CommandHandler("mystatus", mystatus))
    application.add_handler(MessageHandler(filters.Regex("^👤 Мой статус$"), mystatus))
    application.add_handler(CommandHandler("unregister", unregister))
    application.add_handler(MessageHandler(filters.Regex("^❌ Отменить регистрацию$"), unregister))
    application.add_handler(CommandHandler("support", support_handler))
    application.add_handler(MessageHandler(filters.Regex("^💬 Написать в техподдержку$"), support_handler))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.Regex("^❓ Помощь$"), help_command))



    # Админ-команды и кнопки
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(MessageHandler(filters.Regex("^⚙️ Админ-панель$"), admin_panel))
    application.add_handler(MessageHandler(filters.Regex("^⬅️ Главное меню$"), main_menu_return))

    application.add_handler(CommandHandler("fill_random", fill_random_players_cmd))
    application.add_handler(CommandHandler("seed_random", fill_random_players_cmd))
    application.add_handler(MessageHandler(filters.Regex("^🎲 Заполнить недостающих игроков$"), fill_random_players_cmd))
    application.add_handler(MessageHandler(filters.Regex("^🎲 Заполнить недостающих$"), fill_random_players_cmd))
    application.add_handler(MessageHandler(filters.Regex("^🎲 Залить рандомов$"), fill_random_players_cmd))

    application.add_handler(CommandHandler("participants", participants_list))
    application.add_handler(MessageHandler(filters.Regex("^📊 Список участников$"), participants_list))
    application.add_handler(CommandHandler("unconfirmed", unconfirmed_list))
    application.add_handler(MessageHandler(filters.Regex("^⏳ Неподтверждённые$"), unconfirmed_list))
    application.add_handler(CommandHandler("export", export_csv_cmd))
    application.add_handler(MessageHandler(filters.Regex("^📁 Выгрузить CSV$"), export_csv_cmd))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("reset", reset_db))

    application.add_handler(
        CallbackQueryHandler(confirmation_callback, pattern=f"^({CONFIRM_YES}|{CONFIRM_NO})$")
    )

    schedule_jobs(application)

    logger.info("Бот готовится к запуску...")
    application.run_polling()


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    main()
