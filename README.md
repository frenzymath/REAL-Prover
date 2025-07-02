# REAL-Prover

## Introduction

This repository contains the codebase for **REAL-Prover**, a retrieval-augmented stepwise theorem prover built on Lean 4.

## Content

### LeanSearch-PS
See the detailed documentation in [LeanSearch-PS/README.md](LeanSearch-PS/README.md).



### Jixia-interactive
**Jixia**:  
A foundational library used in REAL-Prover.  
Repository: [https://github.com/frenzymath/jixia](https://github.com/frenzymath/jixia)

```bash
git clone https://github.com/frenzymath/jixia
cd jixia
lake build
```

**Interactive**:  
Provides interactive tactics and proof state.  
Repository: [https://github.com/frenzymath/interactive](https://github.com/frenzymath/interactive)

```bash
git clone https://github.com/frenzymath/interactive
cd interactive
lake build
```


### REAL-Prover
See [Realprover/README.md](Realprover/README.md) for usage and implementation details.

### FATE-M Dataset
The FATE-M dataset is located at [`Realprover/data/fate_m.jsonl`](Realprover/data/fate_m.jsonl).


### Data
Additional dataset documentation and structure coming soon.