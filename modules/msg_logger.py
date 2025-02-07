#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import time
from os.path import basename

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Plain, Source
from graia.ariadne.message.parser.twilight import (
    ArgResult,
    ArgumentMatch,
    ElementMatch,
    MatchResult,
    RegexMatch,
    RegexResult,
    SpacePolicy,
    Twilight,
)
from graia.ariadne.model import Group, Member, MemberPerm
from graia.saya import Channel
from graia.saya.builtins.broadcast import ListenerSchema

from util.control import DisableModule
from util.control.permission import GroupPermission
from util.database.log_msg import (
    get_group_talk_count,
    get_member_last_message,
    get_member_talk_count,
    log_msg,
)
from util.module_register import Module

channel = Channel.current()
module_name = basename(__file__)[:-3]

Module(
    name='历史聊天数据记录',
    file_name=module_name,
    author=['Red_lnn'],
    description='记录聊天数据到数据库',
    usage=(
        '[!！.]msgcount —— 【管理】获得目标最近n天内的发言次数\n'
        '  参数：\n'
        '    --type   member/group 目标类型，本群成员或群\n'
        '    --target 【可选】群号/本群成员的QQ号/At群成员\n'
        '    --day    【可选，默认7天】天数（含今天）\n'
        '[!！.]getlast <At/QQ号> —— 【管理】获取某人的最后一条发言'
    ),
).register()


@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage], decorators=[GroupPermission.require(), DisableModule.require(module_name)]
    )
)
async def main(group: Group, member: Member, message: MessageChain, source: Source):
    for ind, elem in enumerate(message[:]):
        if not isinstance(elem, Plain):
            message.__root__[ind] = Plain(elem.asDisplay())
    await log_msg(
        str(group.id),
        str(member.id),
        int(time.mktime(source.time.timetuple())) - time.timezone,
        source.id,
        message.asPersistentString(),
    )


# 获取某人指定天数内的发言条数
@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[
            Twilight(
                [
                    RegexMatch(r'[!！.]msgcount').space(SpacePolicy.FORCE),
                    'arg_type' @ ArgumentMatch("--type", optional=False),
                    'arg_target' @ ArgumentMatch("--target", optional=True),
                    'arg_day' @ ArgumentMatch("--day", optional=True, default='7'),
                ],
            )
        ],
        decorators=[GroupPermission.require(MemberPerm.Administrator), DisableModule.require(module_name)],
    )
)
async def get_msg_count(
    app: Ariadne,
    group: Group,
    member: Member,
    arg_type: ArgResult,
    arg_target: ArgResult,
    arg_day: ArgResult,
):
    if not arg_day.result.asDisplay().isdigit():
        await app.sendMessage(group, MessageChain.create(Plain('参数错误，天数不全为数字')))
        return
    today_timestamp = int(time.mktime(datetime.date.today().timetuple()))
    target_timestamp = today_timestamp - (86400 * (int(arg_day.result.asDisplay()) - 1))
    target: int | None = None
    if arg_type.result.asDisplay() == 'member':
        if arg_target.matched:
            if arg_target.result.onlyContains(At):
                target = arg_target.result.getFirst(At).target
            else:
                if arg_target.result.asDisplay().isdigit():
                    target = int(arg_target.result.asDisplay())
        else:
            target = member.id
    elif arg_type.result.asDisplay() == 'group':
        if arg_target.matched:
            if arg_target.result.asDisplay().isdigit():
                target = int(arg_target.result.asDisplay())
        else:
            target = group.id
    else:
        await app.sendMessage(group, MessageChain.create(Plain('参数错误，目标类型不存在')))
        return

    if arg_type.result.asDisplay() == 'member':
        if not target:
            await app.sendMessage(group, MessageChain.create(Plain('参数错误，目标不是QQ号或At对象')))
            return
        count = await get_member_talk_count(str(group.id), str(target), target_timestamp)
        if not count:
            await app.sendMessage(
                group,
                MessageChain.create(
                    At(target),
                    Plain(f' 还木有说过话，或者是他说话了但没被记录到，又或者他根本不在这个群啊喂'),
                ),
            )
            return
        await app.sendMessage(
            group,
            MessageChain.create(
                At(target),
                Plain(f' 最近{arg_day.result.asDisplay()}天的发言条数为 {count} 条'),
            ),
        )
    else:
        if not target:
            await app.sendMessage(group, MessageChain.create(Plain('参数错误，目标不是群号')))
            return
        count = await get_group_talk_count(str(group.id), target_timestamp)
        if not count:
            await app.sendMessage(group, MessageChain.create(Plain(f'群 {target} 木有过发言')))
            return
        if target == group.id:
            await app.sendMessage(
                group,
                MessageChain.create(
                    Plain(f'本群最近{arg_day.result.asDisplay()}天的发言条数为 {count} 条'),
                ),
            )
        else:
            await app.sendMessage(
                group,
                MessageChain.create(
                    Plain(f'该群最近{arg_day.result.asDisplay()}天的发言条数为 {count} 条'),
                ),
            )


# 获取某人的最后一条发言
@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[
            Twilight(
                [
                    RegexMatch(r'[!！.]getlast').space(SpacePolicy.FORCE),
                    'qq' @ RegexMatch(r'\d+', optional=True),
                    'at' @ ElementMatch(At, optional=True),
                ],
            )
        ],
        decorators=[GroupPermission.require(MemberPerm.Administrator), DisableModule.require(module_name)],
    )
)
async def get_last_msg(app: Ariadne, group: Group, message: MessageChain, qq: RegexResult, at: MatchResult):
    if qq.matched and not at.matched:
        target = int(qq.result.asDisplay())
    elif at.matched and not qq.matched:
        target = message.getFirst(At).target
    else:
        await app.sendMessage(group, MessageChain.create(Plain('无效的指令，参数过多')))
        return
    msg, send_time = await get_member_last_message(str(group.id), str(target))
    if not msg:
        await app.sendMessage(group, MessageChain.create(Plain(f'{target} 木有说过话')))
        return
    chain = MessageChain.fromPersistentString(msg)
    send = MessageChain.create(At(target), Plain(f' 在 {send_time} 说过最后一句话：\n')).extend(chain)
    await app.sendMessage(group, send)
