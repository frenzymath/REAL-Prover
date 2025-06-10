import asyncio
from manager.thirdparty import Claude

class Critic:
    def __init__(self, model='claude'):
        if model == 'claude':
            self.client = Claude()
        else:
            raise NotImplementedError
    
    def get_critics(self, sass: list[tuple[str, str, str]]) -> list[bool]:
        results = asyncio.run(self.client.get_claude_critics(sass))
        return [False if r=="FALSE" else True for r in results]


    def get_critic(self, s1: str, t: str, s2: str) -> bool:
        return self.get_critics([(s1, t, s2)])[-1]