from collections import Counter
from heapdict import heapdict
from manager.struct import Node, state_repr_dedup
from manager.thirdparty import Interactive, TacticGenerator
from manager.thirdparty.verifier import verify_proof
import conf.config
from manager.search.exception import SearchError
import traceback

def hard_stop_criterion(node: Node, window_size=5) -> bool:
    return all('have' in n.tactic for n in node.current_path[:-window_size-1:-1])

class BestFirstSearch:
    def __init__(
        self,
        num_samples: int = conf.config.NUM_SAMPLES,
        max_nodes: int = conf.config.MAX_NODES,
        max_depth: int = conf.config.MAX_DEPTH,
        abandon_if_contain: list[str] = conf.config.ABANDON_IF_CONTAIN,
        is_incontext: bool = conf.config.IS_INCONTEXT,
        template: str = 'deepseek',
        use_retrieval: bool = conf.config.USE_RETRIEVAL,
        alpha: float = 0.5
    ):
        self.found = False
        self.nodes = {}
        self.score = heapdict()
        self.depth = 0
        self.max_nodes = max_nodes
        self.max_depth = max_depth
        self.num_samples = num_samples
        self.tactic_sid_record = []
        self.abandon_if_contain = abandon_if_contain
        self.is_incontext = is_incontext
        self.template = template
        self.use_retrieval = use_retrieval
        self.alpha = alpha

    def insert(self, node: Node, formal_statement: str=None):
        if not node.state:
            try:
                print(f"lake repl check!!!",flush=True)
                full_proof = self.get_incontext(node, formal_statement)
                repl_res = verify_proof(full_proof)
            except Exception as e:
                print(traceback.format_exc())
                self.found = False
            else:
                self.found = repl_res
            if not self.found:
                return
            # self.found = True
        deduped_state_str = state_repr_dedup(node.state)
        if deduped_state_str not in self.nodes:
            self.nodes[deduped_state_str] = node
            if node.depth >0:
                self.score[deduped_state_str] = -node.score/((node.depth)**self.alpha)
            else:
                self.score[deduped_state_str] = 0.0
            self.depth = max(self.depth, node.depth)

    def get(self) -> Node:
        k, _ = self.score.popitem()
        return self.nodes[k]

    def going(self) -> bool:
        return not self.found and len(self.nodes) < self.max_nodes

    def tactic_filter(self, tactic: str) -> bool:
        for forbidden_tactic in self.abandon_if_contain:
            if forbidden_tactic in tactic:
                return False
        return True
    
    def get_incontext(self, node: Node, formal_statement: str):
        path = []
        current = node
        while current:
            path.append(current.tactic)
            current = current.parent
        path.reverse()
        res = formal_statement.replace("sorry", "").replace("by", "").strip() + " by\n"
        res += "\n".join(path)
        return res
    
    def search_proof(self, generator: TacticGenerator, interactive: Interactive):
        while self.going() and generator.has_quota():
            try:
                node = self.get()
            except IndexError:
                break
            if self.is_incontext:
                incontext = self.get_incontext(node, generator.formal_statement)
            else:
                incontext = None
            tactics, logprobs = generator.from_state(node.state, self.num_samples, incontext, self.template, self.use_retrieval)
            tactics_logprob = []
            for tactic, logprob in zip(tactics,logprobs):
                tactics_logprob.append((tactic,logprob))
            for tactic_logprob, num_reps in Counter(tactics_logprob).items():
                tactic,logprob = tactic_logprob
                if not self.tactic_filter(tactic):
                    continue
                self.tactic_sid_record.append({"tactic":tactic, "sid":node.sid})
                try:
                    sid = interactive.run_tactic(node.sid, tactic)     
                except RuntimeError as e:
                    # error_info = traceback.format_exc()
                    # print(error_info,flush=True)
                    pass
                except Exception as e:
                    #目前仅在run_tactic加入记录error-logging功能， 因为根据以往经验在get_state/giveup 加入try block可能会导致broken pipe error
                    #如果确定问题所在可以手动添加
                    raise SearchError("An error occurred at run_tactic", 
                                    error_data = self.tactic_sid_record,
                                    error_type = e)
                else:
                    state = interactive.get_state(sid)
                    # print(f"{tactic},logprob:{logprob}",flush=True)
                    # print(state,flush=True)
                    new_node = Node(sid, node.sid, tactic, state, node.depth + 1, logprob+node.score, node)
                    if hard_stop_criterion(new_node):
                        continue
                    self.insert(new_node,generator.formal_statement)
                    if not state and self.found:
                        interactive.commit(sid)
                        break
        if not self.found:
            sid = interactive.give_up(0)
            interactive.commit(sid)

    @property
    def info(self):
        return dict(
            use_beam_search=False,
            beam_width=None, 
            num_samples=self.num_samples, 
            max_nodes=self.max_nodes,
            max_depth=self.max_depth)
