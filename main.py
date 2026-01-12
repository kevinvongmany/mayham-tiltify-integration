import asyncio
import logging
import random
import twitchio
from twitchio import eventsub
from twitchio.ext import commands
import requests
from pprint import pprint


LOGGER: logging.Logger = logging.getLogger("Bot")

# Consider using a .env or another form of Configuration file!
CLIENT_ID: str = "tkadbr2dtyn70ejbw1c77a9y0e74xg"  # The CLIENT ID from the Twitch Dev Console
CLIENT_SECRET: str = "fqu15drarbuk8ol8drudwzhpzukryt"  # The CLIENT SECRET from the Twitch Dev Console
BOT_ID = "1294742032"  # The Account ID of the bot user...
OWNER_ID = "38308931"  # Your personal User ID..
HEADERS = {
    'Authorization': 'Api-Key KPXq0lux.qgVXfvHAL2V4pkddfTAiwKL4F57zpIiu'
}

class Bot(commands.AutoBot):
    def __init__(self, *, subs: list[eventsub.SubscriptionPayload]) -> None:

        super().__init__(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            bot_id=BOT_ID,
            owner_id=OWNER_ID,
            prefix="~",
            subscriptions=subs,
            force_subscribe=True,
        )

    async def load_tokens(self) -> None:
        tokens_req = requests.get("https://bonkybot.kevinvongmany.com/api/tokens/", headers=HEADERS)
        tokens_json = tokens_req.json()
        tokens = [(token['token'], token['token_secret']) for token in tokens_json]
        for pair in tokens:
            await self.add_token(*pair)

    async def setup_hook(self) -> None:
        # Add our component which contains our commands...
        # await self.add_component(MyComponent(self))
        await self.load_module("mayhambot")
        

    async def event_oauth_authorized(self, payload: twitchio.authentication.UserTokenPayload) -> None:
        LOGGER.info(f"User: {payload.user_id}")
        LOGGER.info(f"Token: {payload.access_token}")
        LOGGER.info(f"Refresh: {payload.refresh_token}")
        await self.add_token(payload.access_token, payload.refresh_token)
        if not payload.user_id:
            return

        if payload.user_id == self.bot_id:
            # We usually don't want subscribe to events on the bots channel...
            return

        # A list of subscriptions we would like to make to the newly authorized channel...
        subs: list[eventsub.SubscriptionPayload] = [
            eventsub.ChatMessageSubscription(broadcaster_user_id=payload.user_id, user_id=self.bot_id),
        ]

        resp: twitchio.MultiSubscribePayload = await self.multi_subscribe(subs)
        if resp.errors:
            LOGGER.warning("Failed to subscribe to: %r, for user: %s", resp.errors, payload.user_id)

    async def event_ready(self) -> None:
        LOGGER.info("Successfully logged in as: %s", self.bot_id)

def fetch_subscriptions() -> list[eventsub.SubscriptionPayload]:
    # Here you can load any subscriptions you want to subscribe to on startup
    # This is useful if you want to subscribe to events on your own channel or other channels
    # without needing to re-authorize the bot.
    users_req = requests.get("https://bonkybot.kevinvongmany.com/api/users/", headers=HEADERS)
    users = users_req.json()
    subs = []
    for user in users:
        subs.append(eventsub.ChatMessageSubscription(broadcaster_user_id=user['uid'], user_id=BOT_ID))
        subs.append(eventsub.ChannelSubscribeSubscription(broadcaster_user_id=user['uid']))
        subs.append(eventsub.ChannelSubscribeMessageSubscription(broadcaster_user_id=user['uid']))
        subs.append(eventsub.ChannelSubscriptionGiftSubscription(broadcaster_user_id=user['uid']))
    return subs

def fetch_tokens() -> list[tuple[str, str]]:
    # Here you can load any tokens you have previously saved to a file or database
    # This is useful if you want to save tokens between restarts of the bot
    # and not need to re-authorize the bot.
    tokens_req = requests.get("https://bonkybot.kevinvongmany.com/api/tokens/", headers=HEADERS)
    tokens_json = tokens_req.json()
    tokens = [(token['token'], token['token_secret']) for token in tokens_json]
    return tokens

# Our main entry point for our Bot
# Best to setup_logging here, before anything starts
def main() -> None:
    twitchio.utils.setup_logging(level=logging.INFO)
    async def runner() -> None:
        subs = fetch_subscriptions()
        async with Bot(subs=subs) as bot:
            await bot.start()

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        LOGGER.warning("Shutting down due to KeyboardInterrupt")


if __name__ == "__main__":
    main()