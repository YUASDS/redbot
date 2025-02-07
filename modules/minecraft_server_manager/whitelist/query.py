#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from uuid import UUID

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Plain
from sqlalchemy import select
from sqlmodel import col, or_

from util.database import Database

from ..model import PlayerInfo
from ..utils import format_time, get_mc_id, get_uuid


async def query_whitelist_by_uuid(mc_uuid: str) -> PlayerInfo | None:
    query_target = UUID(mc_uuid)
    result = await Database.select_first(
        select(PlayerInfo).where(
            or_(col(PlayerInfo.uuid1) == query_target.hex), col(PlayerInfo.uuid2) == query_target.hex
        )
    )
    if result is None or result[0]:
        return None
    else:
        return result[0]


async def query_whitelist_by_id(mc_id: str) -> tuple[dict[str, int | str], PlayerInfo | None]:
    real_mc_id, mc_uuid = await get_uuid(mc_id)
    if not isinstance(real_mc_id, str):
        if real_mc_id.status != 200:
            return {'status': 'error', 'code': real_mc_id.status, 'msg': await real_mc_id.text()}, None

    return {'status': 'success', 'code': 200, 'msg': ''}, await query_whitelist_by_uuid(mc_uuid)


async def query_uuid_by_qq(
    qq: int,
) -> PlayerInfo | None:
    result = await Database.select_first(select(PlayerInfo).where(PlayerInfo.qq == str(qq)))
    if result is None or result[0]:
        return None
    else:
        return result[0]


async def query_qq_by_uuid(mc_uuid: str) -> PlayerInfo | None:
    target = UUID(mc_uuid)
    result = await Database.select_first(
        select(PlayerInfo).where(or_(col(PlayerInfo.uuid1) == target.hex, col(PlayerInfo.uuid2) == target.hex))
    )
    if result is None or result[0]:
        return None
    else:
        return result[0]


async def gen_query_info_text(player: PlayerInfo) -> MessageChain:
    if player.blocked:
        return MessageChain.create(At(int(player.qq)), Plain(f' 已被封禁，封禁原因：{player.block_reason}'))
    if player.uuid1 is None and player.uuid2 is None:
        return MessageChain.create(At(int(player.qq)), Plain(f' 一个白名单都没有呢'))
    info_text = f'({player.qq}) 的白名单信息如下：\n | 入群时间: {player.join_time}\n'
    if player.leave_time:
        info_text += f' | 退群时间: {player.leave_time}\n'
    if player.uuid1 is not None and player.uuid2 is None:
        try:
            mc_id = await get_mc_id(player.uuid1)
        except:  # noqa
            info_text += f' | UUID: {player.uuid1}\n'
        else:
            if not isinstance(mc_id, str):
                info_text += f' | UUID: {player.uuid1}\n'
            else:
                info_text += f' | ID: {mc_id}\n'
        info_text += f' | 添加时间：{format_time(player.uuid1_add_time)}\n'
    elif player.uuid2 is not None and player.uuid1 is None:
        try:
            mc_id = await get_mc_id(player.uuid2)
        except:  # noqa
            info_text += f' | UUID: {player.uuid2}\n'
        else:
            if not isinstance(mc_id, str):
                info_text += f' | UUID: {player.uuid2}\n'
            else:
                info_text += f' | ID: {mc_id}\n'
        info_text += f' | 添加时间：{format_time(player.uuid2_add_time)}'
    elif player.uuid1 is not None and player.uuid2 is not None:
        try:
            mc_id1 = await get_mc_id(player.uuid1)
        except:  # noqa
            info_text += f' | UUID 1: {player.uuid1}\n'
        else:
            if not isinstance(mc_id1, str):
                info_text += f' | UUID 1: {player.uuid1}\n'
            else:
                info_text += f' | ID 1: {mc_id1}\n'
        info_text += f' | ID 1添加时间：{format_time(player.uuid1_add_time)}\n'
        try:
            mc_id2 = await get_mc_id(player.uuid2)
        except:  # noqa
            info_text += f' | UUID 2: {player.uuid2}\n'
        else:
            if not isinstance(mc_id2, str):
                info_text += f' | UUID 2: {player.uuid2}\n'
            else:
                info_text += f' | ID 2: {mc_id2}\n'
        info_text += f' | ID 2添加时间：{format_time(player.uuid2_add_time)}'

    return MessageChain.create(At(int(player.qq)), Plain(info_text))
