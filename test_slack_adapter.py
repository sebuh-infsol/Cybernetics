import asyncio
import os
from cybernetics.adapters.slack import SlackAdapter
from dotenv import load_dotenv

async def test_slack_adapter():
    load_dotenv() # Load environment variables from .env file

    slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
    slack_channel_id = os.getenv("SLACK_CHANNEL_ID") # e.g., "C1234567890"

    if not slack_bot_token:
        print("Error: SLACK_BOT_TOKEN environment variable not set.")
        return
    if not slack_channel_id:
        print("Error: SLACK_CHANNEL_ID environment variable not set.")
        return

    print("Initializing SlackAdapter...")
    adapter = SlackAdapter()

    try:
        print(f"Attempting to post message to channel {slack_channel_id}...")
        result = await adapter.slack_post_message(
            channel=slack_channel_id,
            text="Hello from Cybernetics SlackAdapter! This is an isolated test."
        )
        print("Message posted successfully:")
        print(result)
    except Exception as e:
        print(f"Error posting message: {e}")

if __name__ == "__main__":
    asyncio.run(test_slack_adapter())
