import dataclasses
import json
import logging
import subprocess
from io import TextIOWrapper
from pathlib import Path

import conf.config as config
from manager.struct.structs import from_json, Goal, ProofGoal, ProofVariable
import os
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(asctime)s [%(name)s] %(message)s')
logger = logging.getLogger(os.path.basename(__file__))
IS_BUILD = False

def get_project_toolchain(root: Path) -> str:
    with (root / "lean-toolchain").open() as fp:
        return fp.read()


def build_with_toolchain(root: Path, toolchain: str) -> Path:
    logger.info("Building interactive for %s", toolchain)
    if IS_BUILD:
        with (root / "lean-toolchain").open("w") as fp:
            fp.write(toolchain)
        # logger.info("Building interactive for %s", toolchain)
        if subprocess.call(
                ["lake", "build"],
                stdout=subprocess.DEVNULL,
                cwd=root) != 0:
            raise RuntimeError(f"Failed to build: {root} with {toolchain}")
    return root / ".lake" / "build" / "bin"


def build_interactive(toolchain: str) -> Path:
    bin_path = build_with_toolchain(config.interactive_path, toolchain)
    return bin_path / "interactive"


class Interactive:
    def __init__(self, root: Path, path: Path):
        toolchain = get_project_toolchain(root)
        interactive_bin = build_interactive(toolchain)
        args = ["lake", "env", interactive_bin, "-i", path]
        self.proc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            cwd=root,
        )
        self.read_from = self.proc.stdout
        self.write_to = TextIOWrapper(self.proc.stdin, line_buffering=True)
        self.id = 0
        self.tactic_mode = False

    def read(self) -> dict:
        line = self.read_from.readline().strip()
        logger.debug("<-" + repr(line))
        return json.loads(line)

    def write(self, data: dict):
        data = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        logger.debug("->" + data)
        print(data, file=self.write_to)

    def open_file(self, path: Path, selectors: list[str | int | None]):
        assert not self.tactic_mode
        self.write({"filename": str(path), "selectors": selectors})

    def get_next_problem(self) -> str | None:
        assert not self.tactic_mode
        logger.debug("get_next_problem")
        response = self.read()
        decl_name = response.get("declName")
        self.tactic_mode = decl_name is not None
        return decl_name

    def request(self, method: str, params: dict):
        assert self.tactic_mode
        self.id += 1
        self.write({'id': self.id, 'method': method, 'params': params})
        response = self.read()
        try:
            return response['result']
        except KeyError:
            raise RuntimeError(response['error'])

    def run_tactic(self, sid: int, tactic: str, heartbeats: int = 200000000) -> int:
        return self.request('runTactic', {'sid': sid, 'tactic': tactic, 'heartbeats': heartbeats})

    def get_state(self, sid: int) -> list[Goal]:
        res = self.request('getState', {'sid': sid})
        return from_json(list[Goal], res)

    def get_messages(self, sid: int) -> list[str]:
        res = self.request('getMessages', {'sid': sid})
        return from_json(list[str], res)

    def resolve_name(self, sid: int, name: str) -> list[tuple[str, list[str]]]:
        return self.request('resolveName', {'sid': sid, 'name': name})

    def unify(self, sid: int, s1: str, s2: str) -> list[tuple[str, str | None]] | None:
        return self.request('unify', {'sid': sid, 's1': s1, 's2': s2})

    def new_state(self, state: list[ProofGoal]) -> int:
        return self.request('newState', {'state': [dataclasses.asdict(g) for g in state]})

    def get_position(self) -> dict:
        return self.request('getPosition', {})

    def give_up(self, sid: int) -> int:
        return self.request('giveUp', {'sid': sid})

    def commit(self, sid: int):
        self.request('commit', {'sid': sid})
        self.tactic_mode = False


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    interactive = Interactive(Path(__file__).parent, Path("Example.lean"))
    sid = 0
    interactive.open_file(Path("Example.lean"), ["neg_is_some_none", "eq_trans_sym"])

    while True:
        problem = interactive.get_next_problem()
        if problem is None:
            break

        print("Solving problem", problem)
        sid = 0

        while True:
            state = interactive.get_state(sid)
            if not state:
                # proof complete
                interactive.commit(sid)
                break
            print("current state id:", sid)
            print(f"{len(state)} goals:")
            for goal in state:
                print(goal.pretty)

            command = input()
            try:
                if command.startswith(":s"):
                    sid = int(command.split()[1])
                elif command.startswith(":u"):
                    params = command.split()[1:]
                    result = interactive.unify(sid, params[0], params[1])
                    print(result)
                elif command.startswith(":n"):
                    sid = interactive.new_state([
                        ProofGoal(context=[ProofVariable("a", "Nat")], type="Nat"),
                        ProofGoal(context=[ProofVariable("b", "Nat")], type="Nat")
                    ])
                else:
                    sid = interactive.run_tactic(sid, command)
                messages = interactive.get_messages(sid)
                if messages:
                    print("Messages:", messages)
            except RuntimeError as e:
                err = e.args[0]
                print(f"Error {err['code']}: {err['message']}")
                print(err['data'])