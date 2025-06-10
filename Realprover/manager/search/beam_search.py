from collections import Counter
from heapdict import heapdict
from manager.struct import Node, state_repr_dedup
from manager.thirdparty import Interactive, TacticGenerator
import conf.config
from manager.search.exception import SearchError
# import logging


class BeamSearch:
    def __init__(self,
                beam_width: int = conf.config.BEAM_WIDTH,
                num_samples: int = conf.config.NUM_SAMPLES,
                max_nodes: int = conf.config.MAX_NODES, 
                max_depth: int = conf.config.MAX_DEPTH,
                abandon_if_contain: list[str] = conf.config.ABANDON_IF_CONTAIN
                ):
        self.found = False
        self.nodes = {}
        self.score = heapdict()
        self.depth = 0
        self.beam_width = beam_width
        self.num_samples = num_samples
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self.tactic_sid_record = []
        self.abandon_if_contain = abandon_if_contain
        
    def insert(self, node: Node):
        if not node.state:
            self.found = True

        deduped_state_str = state_repr_dedup(node.state)
        if deduped_state_str not in self.nodes:
            self.nodes[deduped_state_str] = node
            self.score[deduped_state_str] = -node.score
            self.depth = max(self.depth, node.depth)
            # print(f'{len(self.nodes)} Explored.')
        else:
            try:
                self.score[deduped_state_str] -= node.score 
            except KeyError:
                pass

    def get(self) -> list[Node]:
        beam = []
        for _ in range(min(len(self.score), self.beam_width)):
            k, _ = self.score.popitem()
            beam.append(self.nodes[k])
        # self.process_record.append(self.nodes[k])
        return beam

    def going(self) -> bool:
        return not self.found and len(self.nodes) < self.max_nodes and self.depth < self.max_depth

    def tactic_filter(self, tactic: str) -> bool:
        for forbidden_tactic in self.abandon_if_contain:
            if forbidden_tactic in tactic:
                return False
        return True

    def search_proof(self,
                     generator: TacticGenerator, 
                     interactive: Interactive):
        assert len(self.nodes) == 1
        assert generator.calls == []
        while self.going() and generator.has_quota():
            beam = self.get()
            if not beam:
                break
            for node in beam:
                tactics, scores = generator.from_state(node.state, self.num_samples)
                for (tactic, num_reps), _ in zip(Counter(tactics).items(), scores):
                    if not self.tactic_filter(tactic):
                        continue
                    self.tactic_sid_record.append({"tactic":tactic, "sid":node.sid})
                    try:
                        sid = interactive.run_tactic(node.sid, tactic)
                    except RuntimeError:
                        pass
                    except Exception as e:
                        #目前仅在run_tactic加入记录error-logging功能， 因为根据以往经验在get_state/giveup 加入try block可能会导致broken pipe error
                        #如果确定问题所在可以手动添加
                        raise SearchError("An error occurred at run_tactic", 
                                    error_data = self.tactic_sid_record,
                                    error_type = e)
                    else:
                        state = interactive.get_state(sid)
                        new_node = Node(sid, node.sid, tactic, state, node.depth + 1, num_reps, node)
                        self.insert(new_node)
                        if not state:
                            interactive.commit(sid)
                            self.found = True
                            return
        if not self.found:
            sid = interactive.give_up(0)
            interactive.commit(sid)
    
    @property
    def info(self):
        return dict(
            use_beam_search=True,
            beam_width=self.beam_width, 
            num_samples=self.num_samples, 
            max_nodes=self.max_nodes,
            max_depth=self.max_depth)
