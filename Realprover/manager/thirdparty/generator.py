import asyncio
import logging
from typing import Any
from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest

from manager.manage import ModelManage, PromptManage
from manager.struct import Goal, state_repr
from manager.thirdparty import LeanSearch, Claude
import conf.config

logger = logging.getLogger(__name__)


class TacticGenerator:
    def __init__(self, 
                 model_list: list[str], 
                 gpu_id: int, 
                 local_model_path: str=conf.config.PROVER_MODEL_PATH,
                 sampling_params: dict['str', Any]=conf.config.PROVER_MODEL_PARAMS, # n excluded
                 max_calls: int=conf.config.MAX_CALLS):
        """
        model_list: 支持多个model
        """
        self.gpu_id = gpu_id
        self.model_list = model_list
        self.calls = []
        self.llm = None
        self.model_path = local_model_path
        self.sampling_params = sampling_params
        self.max_calls = max_calls

    def from_state_str(self, state_str: str, num_samples: int, incontext: str=None, template: str = 'deepseek', use_retrieval: bool=True) -> tuple[list[str], list[float]]:
        try:
            tactics, logprobs, prompt = self.get_lean_tactics(state_str, num_samples=num_samples, incontext=incontext, template=template, use_retrieval=use_retrieval)
            self.calls.append((state_str, tactics, logprobs, prompt))
        except Exception:
            logger.exception("message")
            
            tactics, logprobs = [], []
        return tactics, logprobs

    def from_state(self, state: list[Goal], num_samples: int, incontext: str=None, template: str = 'deepseek', use_retrieval: bool=True) -> tuple[list[str], list[float]]:
        return self.from_state_str(state_repr(state), num_samples, incontext, template, use_retrieval)

    def from_state_batch(self, states: list[list[Goal]], num_samples: int, incontext: list[str]=None) -> list[tuple[list[str], list[float]]]:
        state_strs = [state_repr(s) for s in states]
        related_theorems = LeanSearch.get_related_theorem_batch(state_strs)
        if incontext is None:
            prompts = [PromptManage.build_local_prompt_str(s, r)
                    for s, r in zip(state_strs, related_theorems)]
        else:
            prompts = [PromptManage.build_local_prompt_str(s, r, c)
                   for s, r, c in zip(state_strs, related_theorems, incontext)] 
        self._init_model()  # 懒加载，用到时才加载模型
        assert self.llm is not None
        sampling_params = SamplingParams(n=num_samples, **self.sampling_params)
        outputs = self.llm.generate(prompts, sampling_params)
        results = []
        
        for state, prompt, output in zip(states, prompts, outputs):
            response = [ot.text.strip() for ot in output.outputs]
            # 为完整记录，在此处不过滤不合法tactic
            # response = [i for i in response if not "sorry" in i]
            logprob = [output.cumulative_logprob / max(len(output.token_ids), 1) # type: ignore
                       for output in output.outputs]
            results.append((response, logprob))
            self.calls.append((state, prompt, (response, logprob)))
        return results
        

    def get_lean_tactics(self, state: str, num_samples: int, incontext: str=None, template: str = 'deepseek', use_retrieval: bool=True) -> tuple[list[str], list[float], str]:
        # 获取相关定理
        if use_retrieval:
            related_theorems = LeanSearch.get_related_theorem(state)
        else:
            related_theorems = None
        if incontext is None:
            prompt = PromptManage.build_local_prompt_str(state, related_theorems)
        else:
            prompt = PromptManage.build_local_incontext_prompt_str(incontext, state, related_theorems, template)
        responses = []
        logprobs = []
        sampling_params = SamplingParams(n=num_samples, **self.sampling_params)

        # Get tactics from Claude if requested
        if ModelManage.contain_gemini(self.model_list):
            claude_responses = asyncio.run(Claude().get_claude_tactics(state, related_theorems, num_samples))
            responses.extend(claude_responses)

        # Get tactics from local model if requested
        if ModelManage.contain_local(self.model_list):
            self._init_model()  # 懒加载，用到时才加载模型
            assert self.llm is not None
            sampling_params = SamplingParams(n=num_samples, **self.sampling_params)
            outputs = self.llm.generate([prompt], sampling_params, use_tqdm=False)
            # lora = LoRARequest("new_data", self.gpu_id, "/AI4M/users/nhhuang/LLaMA-Factory/ds_stepprover_algebra_together")
            # outputs = self.llm.generate([prompt], sampling_params, use_tqdm=False, lora_request=lora)
            local_responses = [output.text.strip() for output in outputs[0].outputs]
            local_responses = [i for i in local_responses if not "sorry" in i]
            local_logprobs = [output.cumulative_logprob / max(len(output.token_ids), 1) # type: ignore
                              for output in outputs[0].outputs]
            responses.extend(local_responses)
            logprobs.extend(local_logprobs)

        return responses, logprobs, prompt

    def has_quota(self) -> bool:
        return len(self.calls) < self.max_calls

    def reset_calls(self, formal_statement:str = None):
        """
        单进程只实例化一次generator, 每次执行时需重置calls
        """
        self.calls = []
        self.formal_statement = formal_statement

    def _init_model(self):
        if self.llm is None:
            self.llm = LLM(model=self.model_path) # Lora
    
    @property
    def info(self):
        return dict(
            model_path=self.model_path,
            max_calls=self.max_calls,
            sampling_params=self.sampling_params)