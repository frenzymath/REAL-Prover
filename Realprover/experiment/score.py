import sys
from manager.manage import ProofParseManage

result_dir = sys.argv[1]
ProofParseManage.get_stats(result_dir)
ProofParseManage.visualize_all_proof_trees(result_dir, keep_false=False)
ProofParseManage.get_all_correct_proofs(result_dir)
# ProofParseManage.get_demo_data(result_dir)