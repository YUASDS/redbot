#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from os.path import basename

from graia.ariadne import get_running
from graia.ariadne.adapter import Adapter
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, AtAll, Image, Plain, Source
from graia.ariadne.message.parser.twilight import RegexMatch, Twilight
from graia.ariadne.model import Group, Member
from graia.broadcast.interrupt import InterruptControl
from graia.broadcast.interrupt.waiter import Waiter
from graia.saya import Channel, Saya
from graia.saya.builtins.broadcast import ListenerSchema

from util.control import DisableModule
from util.control.interval import GroupInterval
from util.control.permission import GroupPermission
from util.module_register import Module
from util.text2img import async_generate_img

saya = Saya.current()
channel = Channel.current()
inc = InterruptControl(saya.broadcast)

module_name = basename(__file__)[:-3]

Module(
    name='消息转图片',
    file_name=module_name,
    author=['Red_lnn'],
    description='仿锤子便签样式的消息转图片，支持纯文本与图像',
    usage='[!！.](文本转图片|消息转图片)',
).register()


@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[Twilight([RegexMatch(r'[!！.](文本转图片|消息转图片)')])],
        decorators=[GroupPermission.require(), GroupInterval.require(15), DisableModule.require(module_name)],
    )
)
async def main(app: Ariadne, group: Group, member: Member, source: Source):
    @Waiter.create_using_function([GroupMessage])
    async def waiter(waiter_group: Group, waiter_member: Member, waiter_message: MessageChain):
        if waiter_group.id == group.id and waiter_member.id == member.id:
            return waiter_message.include(Plain, At, Image)

    await app.sendMessage(group, MessageChain.create(Plain('请发送要转换的内容')), quote=source)
    try:
        answer: MessageChain = await inc.wait(waiter, timeout=10)
    except asyncio.exceptions.TimeoutError:
        await app.sendMessage(group, MessageChain.create(Plain('已超时取消')), quote=source)
        return

    if len(answer) == 0:
        await app.sendMessage(group, MessageChain.create(Plain('你所发送的消息的类型错误')), quote=source)
        return

    img_list: list[str | bytes] = []
    session = get_running(Adapter).session
    for ind, elem in enumerate(answer[:]):
        if type(elem) in (At, AtAll):
            answer.__root__[ind] = Plain(elem.asDisplay())
    for i in answer[:]:
        if isinstance(i, Image):
            async with session.get(i.url) as resp:
                img_list.append(await resp.content.read())
        else:
            img_list.append(i.asDisplay())

    if img_list:
        img_bytes = await async_generate_img(img_list)
        await app.sendMessage(group, MessageChain.create(Image(data_bytes=img_bytes)))
