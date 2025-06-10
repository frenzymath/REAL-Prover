import json
from pathlib import Path
import os
from manager.thirdparty import Interactive, TacticGenerator
from util import CommonUtil, profiler
import conf.config


class SearchError(Exception):
    def __init__(self, message="An error occurred", error_data=None, error_type = None):
        super().__init__(message)
        self.error_data = error_data
        self.error_type = error_type
        
def error_logging(logging_path: Path, id: str, statement:str, tactic_sid_record: list[dict]):
    record = {"statement": statement,
            "tactic_sid_record":tactic_sid_record}
    CommonUtil.write_to_json_file(logging_path, record)


#从experiment/run.py 中运行
def single_error_test(record_path:Path):
    lean_env = Path("/root/.elan/bin")
    os.environ["PATH"] += ":" + str(lean_env)
    root = Path("../lean_test_v4130")
    interactive = Interactive(root, Path("Header.lean"), conf.config.ABANDON_IF_CONTAIN)
    test_file = root / "TestOne.lean"
    record = CommonUtil.load_json(record_path)
    statement = record["statement"]
    tactic_list = record["tactic_sid_record"]
    with test_file.open("w") as fp:
        fp.write(statement)
    interactive.open_file(test_file, [None])
    decl = interactive.get_next_problem()
    sid = 0
    for tactic_sid in tactic_list:
        try:
            sid = interactive.run_tactic(tactic_sid["sid"], tactic_sid["tactic"])    
        except RuntimeError:
            print("PARENT_SID:", tactic_sid["sid"], "NEW_SID:", sid, "TACTIC:", tactic_sid["tactic"], "fail")
            pass
        except Exception as e:
            print("ERROR_SID:", tactic_sid["sid"], "ERROR_TACTIC:", tactic_sid["tactic"])
            raise e
        else:
            print("PARENT_SID:", tactic_sid["sid"], "NEW_SID:", sid, "TACTIC:", tactic_sid["tactic"], "success")
            tactic_sid["new_sid"] = sid
            state = interactive.get_state(sid)
            if not state:
                print("success")
                break
            for goal in state:
                print(goal.pretty)
            print("----------------------------------------------------")

    sid = interactive.give_up(0)
    interactive.commit(sid)
    decl = interactive.get_next_problem()