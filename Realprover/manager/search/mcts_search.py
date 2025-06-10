from collections import Counter
import math
from typing import Optional, Dict, Tuple

from manager.struct import Node, Goal, state_repr_dedup
from manager.thirdparty import Interactive, TacticGenerator
import conf.config
from manager.search.exception import SearchError
EPSILON = 1e-3

class MCTSNode(Node):
    def __init__(self,
                sid: int,
                parent_sid: int,
                tactic: str,
                state: list[Goal],
                depth: int = 0,
                score: float = 0, #现版本MCTS代码并未用到node的score
                parent: Optional["Node"] = None):
        super().__init__(sid, parent_sid, tactic, state, depth, score, parent)
        self.visits = 0  # 访问次数
        self.value = 0.0  # 价值估计
        self.children: Dict[str, "MCTSNode"] = {} # str是字符串化的tacitc

class MCTSSearch:
    def __init__(
        self,
        num_samples: int = conf.config.NUM_SAMPLES,
        max_nodes: int = conf.config.MAX_NODES,
        max_depth: int = conf.config.MAX_DEPTH,
        max_calls: int = conf.config.MAX_CALLS,
        simulation_depth: int = conf.config.SIM_DEPTH,  # MCTS模拟的最大深度
        max_root_expansion: int = conf.config.MAX_ROOT_EXPANSION, # 根节点最多扩展的次数
        c_puct: float = conf.config.C_PUCT,  # PUCT公式的探索参数
        c_score: float = conf.config.C_SCORE, # UCB中score的权重
        c_expansion_fail_penalty: float = conf.config.C_EXPANSION_FAIL_PENALTY, # 扩展失败时反向传播的value，是正数
        abandon_if_contain: list[str] = conf.config.ABANDON_IF_CONTAIN
    ):
        self.found = False
        self.nodes: Dict[str, MCTSNode] = {}  # 由于是继承式字段扩增，所以外面当作Node类的调用不会出问题
        self.root: MCTSNode = None
        self.score = dict() #(deduped_state_str, score), 用于UCB的计算，当作基础值。注意并非heapdict，所以都是正值，跟beamsearch不同
        self.depth = 0
        self.max_nodes = max_nodes
        self.max_depth = max_depth
        self.max_calls = max_calls
        self.num_samples = num_samples
        self.simulation_depth = simulation_depth
        self.c_puct = c_puct
        self.max_root_expansion = max_root_expansion
        self.c_score = c_score
        self.c_expansion_fail_penalty = c_expansion_fail_penalty
        self.call_cnt = 0
        self.tactic_sid_record = []
        self.abandon_if_contain = abandon_if_contain

    def tactic_filter(self, tactic: str) -> bool:
        for forbidden_tactic in self.abandon_if_contain:
            if forbidden_tactic in tactic:
                return False
        return True
    
    def insert(self, node):
        if not isinstance(node, MCTSNode): #处理外界当作node的使用
            node = MCTSNode(
                sid=node.sid,
                parent_sid=node.parent_sid,
                tactic=node.tactic,
                state=node.state,
                depth=node.depth,
                score=node.score,
                parent=node.parent
            )
        if not node.state:
            # self.interactive.commit(node.sid)
            self.found = True
            self.success_sid = node.sid
        deduped_state_str = state_repr_dedup(node.state)
        if deduped_state_str not in self.nodes:
            self.nodes[deduped_state_str] = node
            self.depth = max(self.depth, node.depth)
            self.score[deduped_state_str] = 0

    def _delete_node(self, mcts_node: MCTSNode):
        if mcts_node.sid == 0:  # 根节点不删除
            return
        
        # 递归删除所有子节点
        for child in list(mcts_node.children.values()):  # 使用list创建副本避免在迭代时修改
            self._delete_node(child)
        
        # 删除当前节点
        parent = mcts_node.parent
        del parent.children[mcts_node.tactic]
        del self.nodes[state_repr_dedup(mcts_node.state)]
        del self.score[state_repr_dedup(mcts_node.state)]
        
        # 清理引用关系
        mcts_node.parent = None
        mcts_node.children.clear()

    def _get_root(self) -> MCTSNode:
        assert self.nodes
        #选取self.nodes里面sid为0的节点。如果没有或者超出一个则报错
        root_nodes = [node for node in self.nodes.values() if node.sid == 0]
        if len(root_nodes) == 0:
            raise ValueError("Root node not found")
        elif len(root_nodes) > 1:
            raise ValueError("Multiple sid = 0 root nodes found")
        return root_nodes[0]
    
    def _build_children(self, mcts_node: MCTSNode, generator: TacticGenerator, interactive: Interactive) -> bool:
        if mcts_node.children:
            return True
        tactics, scores = generator.from_state(mcts_node.state, self.num_samples)
        self.call_cnt += 1
        has_valid_tactics = False
        for (tactic, num_reps), _ in zip(Counter(tactics).items(), scores):
            if not self.tactic_filter(tactic):
                continue
            self.tactic_sid_record.append({"tactic":tactic, "sid":mcts_node.sid})
            try:
                sid = interactive.run_tactic(mcts_node.sid, tactic)
            except RuntimeError:
                pass
            except Exception as e:
                #根据以往经验在get_state/giveup 加入try block可能会导致broken pipe error
                #如果确定问题所在可以手动添加
                raise SearchError("An error occurred at run_tactic", 
                    error_data = self.tactic_sid_record,
                    error_type = e)
            else:
                has_valid_tactics = True
                try:
                    #这里据国雄消息可能还有bug， debug后去掉try block
                    state = interactive.get_state(sid)
                except Exception as e:
                    raise SearchError("An error occurred at get_state", 
                        error_data = self.tactic_sid_record,
                        error_type = e)
                if state_repr_dedup(state) not in self.nodes:
                    new_node = MCTSNode(sid, mcts_node.sid, tactic, state, 
                              mcts_node.depth + 1, 1, mcts_node)
                    mcts_node.children[tactic] = new_node
                    self.insert(new_node)
                    if not state:
                        interactive.commit(sid)
                        self.found = True
                        return True
                self.score[state_repr_dedup(state)] += num_reps
        if not has_valid_tactics:
            self._delete_node(mcts_node)
            return False
        return True

    def _select(self, mcts_node: MCTSNode) -> MCTSNode:
        """选择阶段：使用PUCT公式选择最优子节点
        Args:
            mcts_node: 当前MCTS节点
        Returns:
            选择的子节点
        """
        if not mcts_node.children:
            return mcts_node
            
        # 使用PUCT公式选择子节点
        best_value = float('-inf')
        best_child = None
        total_visits = sum(child.visits for child in mcts_node.children.values())

        temp_scores = []
        
        for child in mcts_node.children.values():
            # UCB公式: Q + c_puct * sqrt(N) / (1 + n)
            exploit = self.c_score * self.score[state_repr_dedup(child.state)] + child.value / (child.visits + EPSILON) # 防止除0
            explore = self.c_puct * math.sqrt(total_visits) / (1 + child.visits)
            value = exploit + explore
            temp_scores.append((self.score[state_repr_dedup(child.state)],child.value / (child.visits + EPSILON),explore,child.tactic))
            if value > best_value:
                best_value = value
                best_child = child
                
        return best_child # type: ignore

    def _expand(self, mcts_node: MCTSNode, generator: TacticGenerator, interactive: Interactive) -> Optional[MCTSNode]:
        """扩展阶段：展开一个children已经被build好的节点
        Returns:
            新扩展的子节点, 如果无法扩展则返回None
        """
        flag = self._build_children(mcts_node, generator, interactive)
        if not flag:
            return None
        else:
            return mcts_node #注意这里实际上标准MCTS的expand部分被纳入这里写的select了。这里只是标准MCTS的expand部分的收尾处理。

    def _simulate(self, mcts_node: MCTSNode, generator: TacticGenerator, interactive: Interactive) -> float:
        """模拟阶段：向下模拟几步并评估终态。只roll-out一次，是因为相信value model的准确度。
        value model理应返回"成功概率"，为0到1之间的float。
        Returns:
            模拟得到的价值估计
        """
        current_node = mcts_node
        depth = 0
        while depth < self.simulation_depth:
            if not current_node.state:
                return 1.0  # 找到证明
            tactics, _ = generator.from_state(current_node.state, 1)  # 只采样一个动作，没加call_cnt是避免两种情况混淆
            # TODO: 按sample budget采样，之后取最高分tactic继续
            if not tactics:
                break
            if not self.tactic_filter(tactics[0]):
                continue
            self.tactic_sid_record.append({"tactic":tactics[0], "sid":current_node.sid})
            try: 
                sid = interactive.run_tactic(current_node.sid, tactics[0])
            except RuntimeError:
                print(f"------- \n tactic: {tactics[0]} \n node_num: {len(self.nodes)}")
                break
            except Exception as e:
                #根据以往经验在get_state/giveup 加入try block可能会导致broken pipe error
                #如果确定问题所在可以手动添加
                raise SearchError("An error occurred at run_tactic", 
                    error_data = self.tactic_sid_record,
                    error_type = e)
            else:
                #这里据国雄消息可能还有bug， debug后去掉try block
                try:
                    state = interactive.get_state(sid)
                except Exception as e:
                    raise SearchError("An error occurred at get_state", 
                        error_data = self.tactic_sid_record,
                        error_type = e)
                current_node = Node(sid, current_node.sid, tactics[0], state,
                                current_node.depth + 1, 1, current_node)
                depth += 1
                
        # TODO: 使用价值网络评估终态
        if not current_node.state:
            return 1.0
        return self.score[state_repr_dedup(mcts_node.state)]

    def _backpropagate(self, mcts_node: MCTSNode, value: float):
        """反向传播阶段：更新节点统计信息
        Args:
            mcts_node: 当前MCTS节点
            value: 模拟得到的价值
        """
        current = mcts_node
        while current:
            current.visits += 1
            current.value += value
            # 获取父节点
            parent_state = state_repr_dedup(current.parent.state) if current.parent else None #TODO: 把parent在继承类中复写为MCTSNode
            current = self.nodes.get(parent_state) if parent_state else None

    def going(self) -> bool:
        return not self.found and len(self.nodes) < self.max_nodes and self.depth < self.max_depth and self.call_cnt < self.max_calls

    def search_proof(self, generator: TacticGenerator, interactive: Interactive):
        """执行MCTS搜索
        Args:
            generator: tactic生成器
            interactive: 交互式证明环境
        """
        self.root = self._get_root()
        cnt = 0
        while (cnt < self.max_root_expansion and not self.root.children):
            self._build_children(self.root, generator, interactive)
            cnt += 1
        if not self.root.children:
            print(f"------- \n No valid tactics found ON ROOT: \ndepth {self.root.depth} \n state: {self.root.state}\n node_num: {len(self.nodes)}\n")
            sid = interactive.give_up(0)
            interactive.commit(sid)
            return
        while self.going() and generator.has_quota():
            current = self.root
            # 选择
            while current.children:
                current = self._select(current)
            parent = current.parent if current.parent else None
            # 扩展
            new_node = self._expand(current, generator, interactive)
            if self.found:
                break
            if new_node:
                current = new_node
                #模拟
                value = self._simulate(current, generator, interactive)
                #反向传播
                self._backpropagate(current, value)
            else:
                value = -self.c_expansion_fail_penalty
                if parent:
                    self._backpropagate(parent, value) #认为模型没有有效tactic输出是差情况，反向传播一个差的value
            # 检查是否找到证明
            # if self.found:
            #     interactive.commit(self.success_sid)
            #     break
                
        if not self.found:
            sid = interactive.give_up(0)
            interactive.commit(sid)

    @property
    def info(self):
        """返回搜索器的配置信息"""
        return dict(
            use_beam_search=False,
            use_mcts=True,
            beam_width=None,
            num_samples=self.num_samples,
            max_nodes=self.max_nodes,
            max_depth=self.max_depth,
            simulation_depth=self.simulation_depth,
            c_puct=self.c_puct
        )
