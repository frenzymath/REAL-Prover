import json
import logging
import tempfile
import subprocess
import random
import datetime
import os
import pathlib
import shutil

DEFAULT_LAKE_PATH = "~/.elan/bin/lake"
DEFAULT_LEAN_WORKSPACE = "../lean_test_4160"

def verify_proof(full_code: str, 
                lake_path: str = DEFAULT_LAKE_PATH,
                lean_workspace: str = DEFAULT_LEAN_WORKSPACE,
                timeout: int = 300) -> bool:
    """Verify if the proof code compiles successfully in Lean.
    
    Args:
        code: The proof code to verify
        formal_statement: The theorem statement prefix
        lake_path: Path to lake executable
        lean_workspace: Path to Lean workspace
        timeout: Maximum verification time in seconds
        
    Returns:
        True if verification succeeds, False otherwise
    """
    
    # full_code = formal_statement.strip() + code
    
    command = {"cmd": full_code, "allTactics": False, "ast": False, 
              "tactics": False, "premises": False}
    message_str = json.dumps(command, ensure_ascii=False)
    
    try:
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as temp_file:
            temp_file.write(message_str + "\r\n\r\n")
            temp_file.seek(0)
            outputs = subprocess.run(
                [lake_path, "exe", "repl"],
                stdin=temp_file,
                capture_output=True,
                text=True,
                cwd=lean_workspace,
                timeout=timeout,
            )
        result = json.loads(outputs.stdout)
        result = {
            "sorries": result.get("sorries", []),
            "errors": [m for m in result.get("messages", []) 
                      if m["severity"] == "error" or "sorry" in m["data"]]
        }
        if not result["errors"] and not result["sorries"]:
            str = "Pass"
        else:
            str = "False"
        return not result["errors"] and not result["sorries"]
    except Exception as e:
        logging.error(f"Verification failed: {str(e)}")
        return False
    
if __name__ == "__main__":
    json_path = "/volume/ai4math/users/szj/realprover/stepprover-v2/experiment/logs/2025-05-07/bf2_alge_annot_qwen_nrag_sft_T_1_5_pass64-alg_test_v2-64-1024-0853/generated/1110/1110_43.json"
    with open(json_path,'r') as f:
        data = json.load(f)
        proof_data = data["formal_proof"]
        print(proof_data)
        res = verify_proof(proof_data)
        print(res)