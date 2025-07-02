# HERALD-AF
## Configuration
To get started, modify the configuration file at [`conf/config.py`](conf/config.py):
```python
LEAN_TEST_PATH = "/path/to/lean_test" # Path to the Lean repo: https://github.com/frenzymath/lean_test_v4160
DEFAULT_LAKE_PATH = '/path/to/lake' # Path to Lean's lake directory


NIM_CONFIG = {
    'url': "https://api.deepseek.com/v1",
    'key': "your api key" # Your DeepSeek API key
}
```

## Data format
Each input data should be a JSONL line with two keys: `id` and `informal_statement`.
You can refer to `data/example/simp_10.jsonl` as an example:
```json
{"id": 5, "informal_statement": "Prove that product of two groups is a group, \n\n    Given groups $G,H$. We define $G\\times H$ as follows: \n\n    \n\n    $\\bullet$ Elements are the set $G\\times H$. \n\n\n\n    $\\bullet$ Multiplication given by $(g_1,h_1)(g_2h_2)=(g_1g_2,h_1h_2)$. \n\n\n\n    $\\bullet$ Identity given by $(e_G,e_H)$, where $e_G,e_H$ are the identities of $G,H$. \n\n\n\n    $\\bullet$ Inverse given by $(g,h)^{-1}=(g^{-1},h^{-1})$."}
{"id": 6, "informal_statement": "Prove that the following is a group, \n\n    Given group $(G,*)$. We define $(G^\\mathrm{op},\\circ)$ as follows: \n\n    \n\n    $\\bullet$ Elements are the set $G$. \n\n\n\n    $\\bullet$ Multiplication $\\circ$ given by $g\\circ h:=h*g$. \n\n\n\n    $\\bullet$ Identity and inverse same as in $G$."}
```

## Running HERALD
HERALD uses the DeepSeek API to back-translate formal statements, so only one GPU is required.
To run:
```bash
cd Herald
python -m herald.run --source_file /path/to/your/data --result_dir /path/to/save/result
```