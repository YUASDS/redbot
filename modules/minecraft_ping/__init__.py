#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ping mc服务器

获取指定mc服务器的信息

> 命令：/ping [mc服务器地址]
"""

import socket
from os.path import dirname, split

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from graia.ariadne.message.parser.twilight import RegexMatch, RegexResult, Twilight
from graia.ariadne.model import Group
from graia.saya import Channel
from graia.saya.builtins.broadcast import ListenerSchema
from loguru import logger

from util.config import RConfig
from util.control import DisableModule
from util.control.interval import MemberInterval
from util.control.permission import GroupPermission
from util.module_register import Module

from .ping_client import ping
from .utils import is_domain, is_ip

channel = Channel.current()
module_name = split(dirname(__file__))[-1]

Module(
    name='Ping 我的世界服务器',
    file_name=module_name,
    author=['Red_lnn'],
    description='获取指定mc服务器的信息',
    usage='[!！.]ping {mc服务器地址}',
).register()


class McServerPingConfig(RConfig):
    __filename__: str = 'mc_server_ping'
    servers: dict[int, str] = {123456789: 'localhost:25565'}


ping_cfg = McServerPingConfig()


@channel.use(
    ListenerSchema(
        listening_events=[GroupMessage],
        inline_dispatchers=[
            Twilight(
                [
                    RegexMatch(r'[!！.]ping'),
                    'ping_target' @ RegexMatch(r'\S+', optional=True),
                ],
            )
        ],
        decorators=[GroupPermission.require(), MemberInterval.require(10), DisableModule.require(module_name)],
    )
)
async def main(app: Ariadne, group: Group, ping_target: RegexResult):
    if ping_target.matched:
        server_address = ping_target.result.asDisplay().strip()
    else:
        if group.id not in ping_cfg.servers:
            await app.sendMessage(group, MessageChain.create(Plain('该群组没有设置默认服务器地址')))
            return
        server_address = ping_cfg.servers[group.id]

    if '://' in server_address:
        await app.sendMessage(group, MessageChain.create(Plain('不支持带有协议前缀的地址')))
        return
    elif '/' in server_address:
        await app.sendMessage(group, MessageChain.create(Plain('ping目标地址出现意外字符')))
        return

    if is_ip(server_address):
        kwargs = {'ip': server_address}
    elif ':' in server_address:
        host, port = server_address.split(':', 1)
        if is_ip(host) or is_domain(host):
            if port.isdigit():
                kwargs = {'url': host, 'port': port}
            else:
                await app.sendMessage(group, MessageChain.create(Plain('端口号格式不正确')))
                return
        else:
            await app.sendMessage(group, MessageChain.create(Plain('目标地址不是一个有效的域名或IP（不支持中文域名）')))
            return
    elif is_domain(server_address):
        kwargs = {'url': server_address}
    else:
        await app.sendMessage(group, MessageChain.create(Plain('目标地址不是一个有效的域名或IP（不支持中文域名）')))
        return

    try:
        ping_result = await ping(**kwargs)
    except ConnectionRefusedError:
        await app.sendMessage(group, MessageChain.create(Plain('连接被目标拒绝，该地址（及端口）可能不存在 Minecraft 服务器')))
        logger.warning(f'连接被目标拒绝，该地址（及端口）可能不存在Minecraft服务器，目标地址：{server_address}')
        return
    except socket.timeout:
        await app.sendMessage(group, MessageChain.create(Plain('连接超时')))
        logger.warning(f'连接超时，目标地址：{server_address}')
        return
    except Exception as e:  # noqa
        await app.sendMessage(group, MessageChain.create(Plain(f'发生错误：{e}')))
        logger.exception(e)
        return

    if not ping_result:
        await app.sendMessage(group, MessageChain.create(Plain('无法解析目标地址')))
        return

    if ping_result['motd'] is not None and ping_result['motd'] != '':
        motd_list: list[str] = ping_result['motd'].split('\n')
        motd = f' | {motd_list[0].strip()}'
        if len(motd_list) == 2:
            motd += f'\n | {motd_list[1].strip()}'
    else:
        motd = None
    msg_send = f'咕？咕咕？咕咕咕！！\n服务器版本: [{ping_result["protocol"]}] {ping_result["version"]}\n'
    msg_send += f'MOTD:\n{motd}\n' if motd is not None else ''
    msg_send += f'延迟: {ping_result["delay"]}ms\n在线人数: {ping_result["online_player"]}/{ping_result["max_player"]}'
    if ping_result['online_player'] != '0' and ping_result['player_list']:
        players_list = ''
        for _ in ping_result['player_list']:
            players_list += f' | {_["name"]}\n'
        if int(ping_result['online_player']) <= 10:
            msg_send += f'\n在线列表（不完整）：\n{players_list.rstrip()}'
        else:
            msg_send += f'\n在线列表：\n{players_list.rstrip()}'

    await app.sendMessage(group, MessageChain.create(Plain(msg_send)))
