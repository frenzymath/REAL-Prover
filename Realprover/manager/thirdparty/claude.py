from anthropic import AsyncAnthropic
import asyncio

import conf.config
from manager.manage import PromptManage

claude_config = conf.config.CLAUDE_CONFIG


class Claude:
    """
    调用claude接口执行generate
    """
    def __init__(self):
        self.async_client = AsyncAnthropic(
            base_url=claude_config['base_url'],
            api_key=claude_config['api_key'],
        )

    @staticmethod
    async def get_single_response(async_client, claude_prompt):
        response = await async_client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=100,
            temperature=0.9,
            messages=[{"role": "user", "content": claude_prompt}]
        )
        return response.content[0].text if isinstance(response.content, list) else response.content  # type: ignore


    async def get_claude_tactics(self, state, related_theorems, num_samples=16):
        claude_prompt = PromptManage.build_claude_prompt_str(state, related_theorems)
        tasks = [Claude.get_single_response(self.async_client, claude_prompt)
                 for _ in range(num_samples)]
        responses = await asyncio.gather(*tasks)
        return responses
    

    async def get_claude_critics(self, state_tactic_states: list[tuple[str, str, str]]):
        tasks = [Claude.get_single_response(self.async_client, PromptManage.build_claude_critic_str(s, t, s))
                 for (s, t, s) in state_tactic_states]
        responses = await asyncio.gather(*tasks)
        return responses
