import os
import copy
import platform
from pathlib import Path

import conf.config
from manager.thirdparty import Interactive, TacticGenerator
from manager.struct import Node
from manager.search import BestFirstSearch, BeamSearch, MCTSSearch
from manager.manage import ProofParseManage


class BaseService(object):
    """

    """

    def __init__(self,
                num_samples: int = conf.config.NUM_SAMPLES,
                max_nodes: int = conf.config.MAX_NODES,
                max_depth: int = conf.config.MAX_DEPTH,
                use_beam_search: bool = conf.config.USE_BEAM_SEARCH,
                use_mcts_search: bool = conf.config.USE_MCTS_SEARCH,
                simulation_depth: int = conf.config.SIM_DEPTH,
                c_puct: float = conf.config.C_PUCT,
                beam_width: int = conf.config.BEAM_WIDTH,
                root: Path = Path(conf.config.LEAN_TEST_PATH),
                lean_env: str = conf.config.LEAN_ENV_PATH,
                model_list: list = conf.config.DEFAULT_MODEL_LIST,
                local_model_path: str = conf.config.PROVER_MODEL_PATH,
                sampling_params: dict = conf.config.PROVER_MODEL_PARAMS,
                max_calls: int = conf.config.MAX_CALLS,
                max_root_expansion: int = conf.config.MAX_ROOT_EXPANSION,
                c_score: float = conf.config.C_SCORE,
                c_expansion_fail_penalty: float = conf.config.C_EXPANSION_FAIL_PENALTY,
                abandon_if_contain: list[str] = conf.config.ABANDON_IF_CONTAIN,
                is_incontext: bool = conf.config.IS_INCONTEXT,
                template: str = 'deepseek',
                use_retrieval: bool = conf.config.USE_RETRIEVAL
                ):
        """

        """
        self.num_samples = num_samples
        self.max_nodes = max_nodes
        self.max_depth = max_depth
        self.use_beam_search = use_beam_search
        self.use_mcts_search = use_mcts_search
        self.simulation_depth = simulation_depth
        self.c_puct = c_puct
        self.c_score = c_score
        self.c_expansion_fail_penalty = c_expansion_fail_penalty
        self.max_root_expansion = max_root_expansion
        self.beam_width = beam_width
        self.lean_env = lean_env
        self.root = root
        self.model_list = model_list
        self.local_model_path = local_model_path
        self.sampling_params = sampling_params
        self.max_calls = max_calls
        self.single_generator = None   # 此处初始化一个generator变量的原因是：防止部署的server重复加载模型
        self.abandon_if_contain = abandon_if_contain
        self.info: dict = {}
        self.is_incontext = is_incontext
        self.template = template
        self.use_retrieval = use_retrieval

    def process_one(self, 
                    source: str, 
                    generator: TacticGenerator) -> list[tuple[str, BestFirstSearch, list]]:
        os.environ["PATH"] += ":" + str(self.lean_env)
        interactive = Interactive(self.root, Path("Header.lean"))
        
        
        test_file = self.root / f"TestOne_{platform.node()}_{os.getpid()}.lean"  # 添加节点id和进程Id，防止多进程操作同一个文件引起的error
        with test_file.open("w") as fp:
            fp.write(source)
        interactive.open_file(test_file, [None])
        
        results = []
        while True:
            generator.reset_calls(source)
            decl = interactive.get_next_problem()
            if decl is None:
                break
            if self.use_beam_search:
                search = BeamSearch(max_nodes=self.max_nodes,
                                    max_depth=self.max_depth,
                                    beam_width=self.beam_width,
                                    num_samples=self.num_samples,
                                    abandon_if_contain = self.abandon_if_contain)
            elif self.use_mcts_search:
                search = MCTSSearch(max_nodes=self.max_nodes,
                                    max_depth=self.max_depth,
                                    num_samples=self.num_samples,
                                    simulation_depth=self.simulation_depth,
                                    c_puct=self.c_puct,
                                    c_score=self.c_score,
                                    c_expansion_fail_penalty=self.c_expansion_fail_penalty,
                                    max_root_expansion=self.max_root_expansion,
                                    max_calls=self.max_calls,
                                    abandon_if_contain = self.abandon_if_contain)
            else:
                search = BestFirstSearch(max_nodes=self.max_nodes,
                                        max_depth=self.max_depth,
                                        num_samples=self.num_samples,
                                        abandon_if_contain = self.abandon_if_contain,
                                        is_incontext=self.is_incontext,
                                        template=self.template,
                                        use_retrieval=self.use_retrieval)
            if self.info == {}:
                self.info.update(generator.info)
                self.info.update(search.info)
                
            state = interactive.get_state(0)
            search.insert(Node(0, 0, "", state)) # type: ignore
            search.search_proof(generator, interactive)
            results.append((decl, search, copy.copy(generator)))
        
        test_file.unlink()
        return results
    
    @staticmethod
    def collect_info(decl: str, search, generator) -> dict:
        """ This function collects info for final results
        """
        nodes = [{
            "id": node.sid,
            "parent": node.parent_sid,
            "depth": node.depth,
            "tactic": node.tactic,
            "state": [goal.pretty for goal in node.state],
        } for node in search.nodes.values()]
        return {
            "declaration": decl,
            "success": search.found,
            "calls": generator.calls,
            "nodes": nodes,
            "stop_cause": {
                "nodes": len(search.nodes) >= search.max_nodes,
                "depth": search.depth >= search.max_depth,
                "calls": not generator.has_quota()
            }
        }

    def parse_result(self, formal_statement, results):
        """
        用途：整理总体的输出结果信息
        results: 为 process_one() 生成的结果
        """
        collect_results = [BaseService.collect_info(decl, search, generator) for decl, search, generator in results]
        ret = {
            'formal_statement': formal_statement,
            'collect_results': collect_results,
        }
        if collect_results and collect_results[0]['success']:
            # 成功时才输出formal_proof
            ret['formal_proof'] = ProofParseManage.get_correct_proof(ret)
        return ret

    def single_run(self, formal_statement, gpu_id=0):
        """
        单条运行测试, 并解析出返回值
        """
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
        # this_generator = TacticGenerator(self.model_list, gpu_id, self.local_model_path)
        self._init_single_generator(gpu_id)
        results = self.process_one(formal_statement, self.single_generator) # type: ignore
        ret = self.parse_result(formal_statement, results)
        return ret

    def _init_single_generator(self, gpu_id=0):
        if self.single_generator is None:
            self.single_generator = TacticGenerator(
                model_list=self.model_list, 
                gpu_id=gpu_id, 
                local_model_path=self.local_model_path,
                sampling_params=self.sampling_params,
                max_calls=self.max_calls)