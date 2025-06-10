
import time
import threading
from collections import defaultdict


class Profile:
    def __init__(self):
        self.execution_times = defaultdict(list)
        self.local = threading.local()

    def start(self, name):
        """Start timing a code block."""
        if not hasattr(self.local, 'stack'):
            self.local.stack = []

        start_time = time.time()
        self.local.stack.append((name, start_time))

    def stop(self, name):
        """Stop timing a code block."""
        end_time = time.time()

        if not hasattr(self.local, 'stack') or not self.local.stack:
            raise ValueError(f"No active timing block named '{name}' to stop.")

        last_name, start_time = self.local.stack.pop()
        if last_name != name:
            raise ValueError(f"Mismatched timing blocks: expected '{last_name}' but got '{name}'.")

        elapsed_time = end_time - start_time
        self.execution_times[name].append(elapsed_time)
        print(f'stop {name} with {elapsed_time}', flush=True)

    def get_execution_times(self):
        """Get the total execution times for each named block."""
        times = {name: sum(records) for name, records in self.execution_times.items()}
        return times

    def print_execution_times(self):
        """Print the execution times for all recorded blocks."""
        for name, records in self.execution_times.items():
            total_time = sum(records)
            print(f"Block '{name}' executed in total: {total_time:.6f} seconds over {len(records)} runs.")


profiler = Profile()
