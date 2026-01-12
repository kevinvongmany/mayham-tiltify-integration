import logging
import twitchio
from twitchio.ext import commands

import asyncio
import json
import websockets
from datetime import datetime
from random import choice
import requests
from pprint import pprint
from main import Bot, HEADERS

BASE_URL = "https://bonkybot.kevinvongmany.com"
# BASE_URL = "http://localhost:8000"

async def send_ws_message(message):
    uri = "wss://l0axmgjep7.execute-api.ap-southeast-2.amazonaws.com/beta"

    message = {
        "action": "sendmessage",
        "message": message
    }

    async with websockets.connect(uri) as websocket:
        # Send the message as a JSON string
        await websocket.send(json.dumps(message))
        print(f"Sent: {message}")

        # Optionally receive a reply
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=3)
            print("Received:", response)
        except asyncio.TimeoutError:
            print("No reply received (timeout or no server response)")

LOGGER: logging.Logger = logging.getLogger("BonkyBot")

class BotComponent(commands.Component):
    def __init__(self, bot: Bot) -> None:
        # Load database files into memory
        self.bot = bot
        self.tier_scale = {
            '1000': 1,
            '2000': 2,
            '3000': 5
        }
    

    async def _invoke_override(self, tier: str) -> None:
        override_tiers = {
            "tier_1": [
                "pull_ghost",
                "open_inventory",
                "jump_and_ability",
                "class_ability",
                "powered_melee",
            ],
            "tier_2": [
                "throw_grenade",
                "super",
                "transcendence",
                "jumpscare",
                "hold_forward",
            ],
            "tier_3": [
                "look_down",
                "turn_around",
                "ttt",
            ],
            "tier_4": [
                "dump_heavy",
                "dump_kinetic",
                "random_loadout",
            ],
            "tier_5": ["alt_f4"]
        }
        print(f"Invoking a {tier} command")
        selected_override = override_tiers[tier]
        random_command = choice(selected_override)
        print(f"Command triggered: {random_command}")
        await send_ws_message(random_command)


    async def _global_override(self, user_subs, old_total_subs: int, new_total_subs: int, global_tiers: dict[str|int]) -> None:
            tier_5_threshold = global_tiers['tier_5']
            current_count = old_total_subs % tier_5_threshold
            new_count = current_count + user_subs
            if new_count >= tier_5_threshold:
                await self._invoke_override('tier_5')
                return
            random_pool = []
            if new_total_subs >= global_tiers['tier_4']:
                random_pool.append('tier_4')
            if new_total_subs >= global_tiers['tier_3']:
                random_pool.append('tier_3')
            if new_total_subs >= global_tiers['tier_2']:
                random_pool.append('tier_2')
            if new_total_subs >= global_tiers['tier_1']:
                random_pool.append('tier_1')
            if len(random_pool) > 0:
                selected_tier = choice(random_pool)
                print(f"Sending Global Override Tier: {selected_tier}")
                await self._invoke_override(selected_tier)

    async def _handle_user_override(self, user_subs: int, user_tiers:dict[str|int]) -> None:
        eligible = [(k, v) for k, v in user_tiers.items() if v <= user_subs]
        # Get the key with the maximum value <= val
        tier = max(eligible, key=lambda x: x[1])[0]
        await self._invoke_override(tier)

    async def _update_sub_count(self, user: str, total: int)-> None:
        login = user.lower()
        print(user)
        req = requests.post(f"{BASE_URL}/api/subs/{login}/", json={"subs": total}, headers=HEADERS)
        data = req.json()
        await self._global_override(
            user_subs=total,
            old_total_subs=data['old_sub_total'], 
            new_total_subs=data['new_sub_total'],
            global_tiers=data['global_tiers']
        )
        await self._handle_user_override(
            user_subs=total, 
            user_tiers=data['user_tiers'],
        )
        pprint(data['global_tiers'])

    # Message events
    @commands.Component.listener()
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        # display all messages in the terminal
        timestamp = datetime.now().strftime("%H:%M:%S.%f")
        print(f"[{timestamp}] [{payload.broadcaster.name}] - {payload.chatter.name}: {payload.text}")

    
    # @commands.command(aliases=["sub"])
    # async def subscribe(self, ctx: commands.Context, *args) -> None:
    #     print(f"Sub command invoked")
    #     login = ctx.broadcaster.name
    #     await self._update_sub_count(login, 1)

    # @commands.command(alias="resub")
    # async def resubscribe(self, ctx: commands.Context, *args) -> None:
    #     login = ctx.broadcaster.name
    #     print(f"Resub command invoked")
    #     await self._update_sub_count(login, 1)
    
    # @commands.command(aliases=["gift_sub"])
    # async def gift(self, ctx: commands.Context, number: str, *args) -> None:
    #     input_number = int(number)
    #     print(f"Gift command invoked with args: {input_number}")
    #     login = ctx.broadcaster.name
    #     await self._update_sub_count(login, input_number)

    @commands.Component.listener("subscription")
    async def event_new_subscription(self, payload: twitchio.ChannelSubscribe) -> None:
        if payload.gift:
            return
        print(f"New tier {payload.tier} sub!")
        login = payload.broadcaster.name
        tier = self.tier_scale.get(payload.tier, 1)
        await self._update_sub_count(login, tier)


    @commands.Component.listener("subscription_message")
    async def event_new_subscription_message(self, payload: twitchio.ChannelSubscriptionMessage) -> None:
        login = payload.broadcaster.name
        print(f"A tier {payload.tier} resub!")
        tier = self.tier_scale.get(payload.tier, 1)
        await self._update_sub_count(login, tier)

    @commands.Component.listener("subscription_gift")
    async def event_subscription_gift(self, payload: twitchio.ChannelSubscriptionGift) -> None:
        login = payload.broadcaster.name
        print(f"A tier {payload.tier} gift sub!")
        tier = self.tier_scale.get(payload.tier, 1)
        total = payload.total * tier
        await self._update_sub_count(login, total)



async def setup(bot: commands.AutoBot) -> None:
    setup_message =f"Starting up the bot for {bot.user.name}"
    print(setup_message)
    LOGGER.info(setup_message)
    await bot.add_component(BotComponent(bot))

async def teardown(bot: commands.AutoBot) -> None:
    teardown_message =f"Bot for {bot.user.name} has been shutdown"
    print(teardown_message)
    LOGGER.info(teardown_message)
    await bot.remove_component(BotComponent(bot))
    
# if __name__ == "__main__":
#     main()