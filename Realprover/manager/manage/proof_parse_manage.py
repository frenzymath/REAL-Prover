from pathlib import Path
import json
from pprint import pp
from matplotlib import pyplot as plt
import networkx as nx
from conf import config

from manager.struct import Goal
import os

class ProofParseManage(object):
    """
    此处代码从源代码 stats.py 文件中移植
    """

    @staticmethod
    def get_correct_proof(data: dict) -> str:
        proof = data['formal_statement']
        for p in data['collect_results']:
            G, path = ProofParseManage.get_proof_tree(p)
            edge_labels = nx.get_edge_attributes(G, "label")
            proof = proof.replace("sorry", "").replace("by", "").strip() + " by"
            for i in range(len(path) - 1):
                tac = edge_labels[(path[i], path[i + 1])]
                proof += "\n  " + tac
        return proof

    @staticmethod
    def get_proof_tree(data: dict) -> tuple[nx.DiGraph, list[int]]:
        # Create a directed graph
        nodes = data["nodes"]
        G = nx.DiGraph()
        correct_path = []

        # Add nodes and edges
        for node in nodes:
            G.add_node(
                node["id"],
                parent=node["parent"],
                id=node["id"],
                tactic=node["tactic"],
                state=node["state"]
            )
            if node["id"] != node["parent"]:
                G.add_edge(node["parent"], node["id"], label=node["tactic"])
            # Check if this step ends with an empty goal
            if not node["state"]:
                correct_path.append(node["id"])

        # Backtrack the correct path
        path = []
        if correct_path:
            # Assume the first empty goal is the correct one
            node = correct_path[0]
            while node in G:
                path.append(node)
                # Stop if we reach the root
                if node == G.nodes[node]["parent"]:
                    break
                node = G.nodes[node]["parent"]
            path = path[::-1]  # Reverse the path to start from the root
        return G, path

    @staticmethod
    def pp_state(state: list[Goal]) -> str:
        return "\n\n".join([goal.pretty for goal in state])

    @staticmethod
    def collect_error(nid: int, decl: str, state: str, tactic: str, error: str, result_dir: Path) -> None:
        with open(result_dir, 'a') as fp:
            fp.write(
                f'# Error on node {nid}\n\n## Informal statement:\n{decl}\n\n## State:\n{state}\n\n## Tactic:\n{tactic}\n\n## Detail:\n\n{error}\n\n'
            )

    @staticmethod
    def concat_proof(d: dict) -> str:
        nodes = d['nodes'][1:]  # ignore the first node
        concatenated = "\n".join(["  " + n['tactic'] for n in nodes])
        return concatenated

    @staticmethod
    def pretty(data: list[dict], result_dir: Path) -> None:
        output_dir = Path("outputs") / (result_dir.name)
        output_dir.mkdir(exist_ok=True)
        for d in data[:]:
            formal_statement = d['formal_proof']
            informal_statement = d['informal_stmt']
            result_file = result_dir / f"{d['answer_id']}.json"
            with open(result_file) as fp:
                result_dict = json.load(fp)
                if not result_dict:
                    continue
                if not result_dict[0]['success']:
                    continue
                formal_proof = ProofParseManage.concat_proof(result_dict[0])

            with open(output_dir / f"{d['answer_id']}.lean", "w") as fp:
                fp.write(f"/- {informal_statement} -/\n")
                fp.write(formal_statement + formal_proof)
            # print(formal_statement + formal_proof)

    @staticmethod
    def visualize_proof_tree(G: nx.DiGraph, path: list[int], output: Path = Path("figs/test_plot.jpg")) -> None:
        # Draw the graph
        pos = nx.drawing.nx_agraph.graphviz_layout(
            G, prog="dot")  # Layout for visualization
        colors = ["red" if node in path else "blue" for node in G.nodes]
        labels = {node: f"{G.nodes[node]['id']}" for node in G.nodes}
        _, ax = plt.subplots(figsize=(10, 8))
        nx.draw(
            G,
            pos,
            ax,
            with_labels=True,
            labels=labels,
            node_color=colors,
            node_size=500,
            font_size=10,
            font_color="white",
            edge_color="gray",
        )
        edge_labels = nx.get_edge_attributes(G, "label")
        nx.draw_networkx_edge_labels(
            G,
            pos,
            edge_labels=edge_labels,
            font_size=8,
            rotate=False
        )
        plt.title("Proof Search Tree")
        plt.show()
        plt.savefig(output)

    @staticmethod
    def get_prompt(data, node):
        for i, n in enumerate(data[-1]["nodes"]):
            if n["id"] == node:
                pp(data[-1]['calls'][i][2])
                return data[-1]["calls"][i][2]

    @staticmethod
    def get_one_kto_data(data: dict):
        G, path = ProofParseManage.get_proof_tree(data)
        correct_edges = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
        results = []
        for edge in G.edges:
            node = G.nodes[edge[1]]
            try:
                prompt = ProofParseManage.get_prompt(data, node["id"])
            except IndexError:
                prompt = ""
            d = {
                "id": node["id"],
                "parent": node["parent"],
                "tactic": node["tactic"],
                "state": node["state"],
                "prompt": prompt
            }
            if edge in correct_edges:
                d.update({"label": True})
            else:
                d.update({"label": False})
            results.append(d)
        return results

    @staticmethod
    def get_kto_data(result_dir: Path):
        kto_data = []
        for file in result_dir.iterdir():
            with file.open() as fp:
                data = json.load(fp)
            try:
                one_kto_data = ProofParseManage.get_one_kto_data(data)
            except Exception as e:
                one_kto_data = []
                print(e)
            kto_data.extend(one_kto_data)
        print(len(kto_data))
        with open(Path("kto_data") / (result_dir.name + ".json"), 'w') as fp:
            json.dump(kto_data, fp, ensure_ascii=False, indent=2)
   
    @staticmethod
    def get_stats(result_dir: str, info: dict = {}):
        results = dict(total=0, success=0, accuracy=0.0)
        generated_dir = os.path.join(result_dir, 'generated')
        for dir_path in os.listdir(generated_dir):
            success_flag = False
            full_path = os.path.join(generated_dir,dir_path)
            for root, dir, files in os.walk(full_path):
                for file in files:
                    if '.json' in file and os.path.samefile(full_path,root):
                        file_path = os.path.join(root, file)
                        with open(file_path,'r') as f:
                            data = json.load(f)
                            for problem in data['collect_results']:
                                if problem["success"]:
                                    results['success'] += 1 
                                    success_flag = True
                                    break
                if success_flag:
                    break
            results['total'] += 1
        results['accuracy'] = results["success"] / results['total']
        results.update(info)
        with open(Path(result_dir, 'result.txt'), 'w', encoding='utf-8') as fp:
            for k, v in results.items():
                fp.write(f'{k}: {v}\n')
        pp(results)
    
    @staticmethod
    def visualize_all_proof_trees(result_dir: str, keep_false: bool = True):
        output_dir = Path(result_dir, 'figs')
        output_dir.mkdir(exist_ok=True)
        for file in Path(result_dir, 'generated').iterdir():
            with file.open() as fp:
                data = json.load(fp)
            if not data['collect_results']:
                continue
            if (not keep_false) and (not data['collect_results'][-1]['success']):
                continue
            for p in data['collect_results']:
                G, path = ProofParseManage.get_proof_tree(p)
                output_path = output_dir / file.name.replace('.json', '.png')
                ProofParseManage.visualize_proof_tree(G, path, output_path)

    @staticmethod
    def get_all_correct_proofs(result_dir: str) -> None:
        output_dir = Path(result_dir, 'proofs')
        output_dir.mkdir(exist_ok=True)
        for file in Path(result_dir, 'generated').iterdir():
            with file.open() as fp:
                data = json.load(fp)
            if not data['collect_results'] or not data['collect_results'][-1]['success']:
                continue
            proof = ProofParseManage.get_correct_proof(data)
            with open(Path(output_dir, file.name.replace('.json', '.lean')), 'w') as fp:
                fp.write(proof)

    @staticmethod
    def get_demo_data(result_dir: str) -> None:
        output_dir = Path(result_dir, 'demos')
        output_dir.mkdir(exist_ok=True)
        for file in Path(result_dir, 'generated').iterdir():
            with file.open() as fp:
                data = json.load(fp)
            if 'formal_proof' not in data.keys():
                continue
            data['_formal_proof'] = data.pop('formal_proof')   
            data['informal_statement'] = ''
            if not data['collect_results']:
                continue
            if not data['collect_results'][-1]['success']:
                continue
            data['nodes'] = data['collect_results'][-1]['nodes']
            _, path = ProofParseManage.get_proof_tree(data)
            data.pop('collect_results')
            for n in data['nodes']:
                n['informal_tactic'] = ''
                n['short_informal_tactic'] = ''
                n['informal_state'] = [''] * len(n['state'])
                n['in_right_path'] = n['id'] in path
            with open(output_dir / file.name, 'w') as fp:
                json.dump(data, fp, ensure_ascii=False, indent=4)
                
    
    @staticmethod
    def get_length_distribution(result_dir: str):
        from collections import Counter
        len_list = []
        generated_dir = Path(result_dir, "generated")
        for dir_path in os.listdir(generated_dir):
            success_flag = False
            full_path = os.path.join(generated_dir,dir_path)
            for root, dir, files in os.walk(full_path):
                for file in files:
                    if '.json' in file and os.path.samefile(full_path,root):
                        file_path = os.path.join(root, file)
                        with open(file_path,'r') as f:
                            data = json.load(f)
                        if data['collect_results'][-1]['success']:
                            G, path = ProofParseManage.get_proof_tree(data['collect_results'][-1])
                            len_list.append(len(path)-1)
        counter = Counter(len_list)

        numbers = list(counter.keys())
        frequencies = list(counter.values())

        output = Path(result_dir, "len_distribution.png")

        plt.bar(numbers, frequencies)
        plt.xlabel('Length')
        plt.ylabel('Frequency')
        plt.title('Proof Length Distribution')
        plt.savefig(output, dpi=300, bbox_inches='tight')

