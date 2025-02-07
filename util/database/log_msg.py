#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from sqlalchemy import select

# from sqlmodel import select
from sqlmodel import and_, col, func, or_

from . import Database
from .models import MsgLog


async def log_msg(group: str, qq: str, timestamp: int, msg_id: int, msg_chain: str) -> None:
    # 此处的 msg_chain 需要的是 MessageChain().asPersistentString()
    await Database.add(MsgLog(group_id=group, member_id=qq, timestamp=timestamp, msg_id=msg_id, msg_chain=msg_chain))


async def get_member_talk_count(group: str, qq: str, timestamp: int = 0) -> int:
    result = await Database.select_first(
        select(func.count())
        .select_from(MsgLog)
        .where(and_(col(MsgLog.group_id) == group, col(MsgLog.member_id) == qq, col(MsgLog.timestamp) >= timestamp))
    )
    return result[0]


async def get_group_talk_count(group: str, timestamp: int = 0) -> int:
    result = await Database.select_first(
        select(func.count())
        .select_from(MsgLog)
        .where(and_(col(MsgLog.group_id) == group, col(MsgLog.timestamp) >= timestamp))
    )
    return result[0]


async def get_member_last_message(group: str, qq: str) -> tuple[str | None, int | None]:
    result = await Database.select_first(
        select(func.max(MsgLog.timestamp)).where(and_(col(MsgLog.group_id) == group, col(MsgLog.member_id) == qq))
    )
    if result is None or result[0] is None:
        return None, None
    max_timestamp = result[0]
    result = await Database.select_first(
        select(MsgLog).where(
            and_(col(MsgLog.group_id) == group, col(MsgLog.member_id) == qq, col(MsgLog.timestamp) == max_timestamp)
        )
    )
    record: MsgLog = result[0]
    return record.msg_chain, record.msg_id


async def get_group_last_message(group: str) -> tuple[str | None, str | None, int | None]:
    result = await Database.select_first(select(func.max(MsgLog.timestamp)).where(col(MsgLog.group_id) == group))
    if result is None or result[0] is None:
        return None, None, None
    max_timestamp = result[0]
    result = await Database.select_first(
        select(MsgLog).where(and_(col(MsgLog.group_id) == group, col(MsgLog.timestamp) == max_timestamp))
    )
    record: MsgLog = result[0]
    return record.member_id, record.msg_chain, record.timestamp


async def get_member_last_message_id(group: str, qq: str) -> int | None:
    result = await Database.select_first(
        select(func.max(MsgLog.msg_id)).where(and_(col(MsgLog.group_id) == group, col(MsgLog.member_id) == qq))
    )
    return result[0]


async def get_group_last_message_id(group: str) -> int | None:
    result = await Database.select_first(select(func.max(MsgLog.msg_id)).where(col(MsgLog.group_id) == group))
    return result[0]


async def get_member_last_time(group: str, qq: str) -> int | None:
    result = await Database.select_first(
        select(func.max(MsgLog.timestamp)).where(and_(col(MsgLog.group_id) == group, col(MsgLog.member_id) == qq))
    )
    return result[0]


async def get_group_last_time(group: str) -> int | None:
    result = await Database.select_first(select(func.max(MsgLog.timestamp)).where(col(MsgLog.group_id) == group))
    return result[0]


async def get_group_msg_by_id(group: str) -> str | None:
    result = await Database.select_first(select(MsgLog).where(col(MsgLog.group_id) == group))
    return None if result is None else result[0].msg_chain


async def get_member_msg(group: str, qq: str, timestamp: int = 0) -> list[str]:
    result = await Database.select_all(
        select(MsgLog).where(
            and_(col(MsgLog.group_id) == group, col(MsgLog.member_id) == qq, col(MsgLog.timestamp) >= timestamp)
        )
    )
    record: list[MsgLog] = [i[0] for i in result]
    if record[0] is None:
        return []
    return [i.msg_chain for i in record]


async def get_group_msg(group: str, timestamp: int = 0) -> list[str]:
    result = await Database.select_all(
        select(MsgLog).where(and_(col(MsgLog.group_id) == group, col(MsgLog.timestamp) >= timestamp))
    )
    record: list[MsgLog] = [i[0] for i in result]
    if record[0] is None:
        return []
    return [i.msg_chain for i in record]


async def del_member_msg(group: str, qq: str, timestamp: int) -> bool:
    result = await Database.select_all(
        select(MsgLog).where(
            and_(col(MsgLog.group_id) == group, col(MsgLog.member_id) == qq, col(MsgLog.timestamp) >= timestamp)
        )
    )
    record: list[MsgLog] = [i[0] for i in result]
    if record[0] is None:
        return True
    return await Database.delete_many_exist(*record)


async def del_group_msg(group: str, timestamp: int):
    result = await Database.select_all(
        select(MsgLog).where(and_(col(MsgLog.group_id) == group, col(MsgLog.timestamp) >= timestamp))
    )
    record: list[MsgLog] = [i[0] for i in result]
    if record[0] is None:
        return True
    return await Database.delete_many_exist(*record)
