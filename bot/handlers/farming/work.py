from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from bot.database.crud import get_user_by_id, get_all_jobs, get_available_jobs, get_user_job_cooldown
from bot.services.farming_service import process_work
from bot.keyboards.inline import jobs_list_keyboard
from bot.utils.formatting import format_money, format_time, format_job_info
from bot.filters.chat_type import GroupFilter


router = Router(name="work")


@router.message(Command("work"), GroupFilter)
async def cmd_work(message: Message, session: AsyncSession):
    """Show available jobs."""
    user = await get_user_by_id(session, message.from_user.id)
    if not user:
        await message.reply("❌ Ты не зарегистрирован. Напиши /start в группе.")
        return

    # Check if in jail
    if user.jail_until and user.jail_until > datetime.utcnow():
        await message.reply("⛓ Ты в тюрьме! Не можешь работать.")
        return

    jobs = await get_available_jobs(session, user.level)
    if not jobs:
        await message.reply("😔 Нет доступных работ для твоего уровня.")
        return

    text = (
        f"💼 <b>Биржа труда</b>\n\n"
        f"Твой уровень: <b>{user.level}</b>\n"
        f"Текущая работа: <b>{user.job.name if user.job else 'Безработный'}</b>\n\n"
        f"Выбери работу:"
    )
    await message.reply(text, reply_markup=jobs_list_keyboard(jobs, user.job_id), parse_mode="HTML")


@router.callback_query(F.data.startswith("work_select:"))
async def cb_work_select(callback: CallbackQuery, session: AsyncSession):
    """Handle job selection."""
    job_id = int(callback.data.split(":")[1])
    user = await get_user_by_id(session, callback.from_user.id)
    if not user:
        await callback.answer("❌ Не зарегистрирован", show_alert=True)
        return

    success, msg, money, exp = await process_work(session, user, job_id)
    if success:
        # Show job info with result
        from bot.database.crud import get_job
        job = await get_job(session, job_id)
        await callback.message.edit_text(
            f"✅ <b>Работа выполнена!</b>\n\n"
            f"💼 {job.name}\n"
            f"💰 +{format_money(money)}$\n"
            f"⭐ +{exp} XP\n\n"
            f"💰 Баланс: {format_money(user.balance)}$\n"
            f"⭐ Опыт: {user.exp} XP",
            parse_mode="HTML",
        )
    else:
        await callback.answer(msg, show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "work_cancel")
async def cb_work_cancel(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.message(Command("jobinfo"), GroupFilter)
async def cmd_jobinfo(message: Message, session: AsyncSession, command: CommandObject):
    """Show job info: /jobinfo <job_id>"""
    if not command.args or not command.args.isdigit():
        await message.reply("❌ Укажи ID работы: /jobinfo <id>")
        return

    from bot.database.crud import get_job
    job = await get_job(session, int(command.args))
    if not job:
        await message.reply("❌ Работа не найдена")
        return

    await message.reply(format_job_info(job), parse_mode="HTML")