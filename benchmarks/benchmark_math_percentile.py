print("Script execution started.", flush=True)
import random
import timeit
from typing import (
    List,
    Sequence,
)

from web3._utils.math import (
    percentile,
)

# Define test cases
LIST_SIZES = {
    "small": 10,
    "medium": 1000,
    "large": 100000,
}

PERCENTILES_TO_TEST = [0, 25.5, 50, 75.5, 100]

NUMBER_OF_EXECUTIONS = 100  # Number of times to execute the function for each test


def generate_random_list(size: int) -> List[int]:
    """Generates a list of random integers."""
    return [random.randint(0, 1000000) for _ in range(size)]


def run_benchmark(
    func_to_benchmark, data: Sequence[int], percentile_value: float
) -> float:
    """Runs the benchmark for a given function, data, and percentile."""
    setup_code = f"""
from __main__ import {func_to_benchmark.__name__}
data = {data}
percentile_value = {percentile_value}
"""
    stmt_code = f"{func_to_benchmark.__name__}(data, percentile_value)"
    # Use timeit to measure execution time
    times = timeit.repeat(
        stmt_code, setup=setup_code, repeat=3, number=NUMBER_OF_EXECUTIONS
    )
    return min(times) / NUMBER_OF_EXECUTIONS  # Return average time of the best run


if __name__ == "__main__":
    print(
        f"Benchmarking `percentile` function ({NUMBER_OF_EXECUTIONS} executions per test)",
        flush=True,
    )
    for name, size in LIST_SIZES.items():
        print(f"\n--- {name.capitalize()} list ({size} elements) ---", flush=True)
        random_list = generate_random_list(size)
        for p_val in PERCENTILES_TO_TEST:
            try:
                avg_time = run_benchmark(percentile, random_list, p_val)
                print(
                    f"  Percentile {p_val:>5}: {avg_time*1e6:.2f} µs per execution",
                    flush=True,
                )  # print in microseconds
            except Exception as e:
                print(f"  Percentile {p_val:>5}: Error - {e}", flush=True)
    print("\nBenchmarking finished.", flush=True)
    # Example of how to benchmark the compiled version if available
    # Note: This requires the compiled module to be in the PYTHONPATH
    # and named differently or handled via a switch.
    # For simplicity, this example assumes you might have a compiled version
    # aliased or accessible. If you have `math.cpython-310-x86_64-linux-gnu.so`
    # you might need to import it specifically if not automatically picked up.

    # To benchmark a potentially compiled version (conceptual):
    # try:
    #     # This assumes that if a compiled version exists,
    #     # it might be imported or accessible via a different name
    #     # or that Python's import mechanism might pick it up.
    #     # For a direct comparison, one might need to set up separate environments
    #     # or rename modules.
    #     from web3._utils import math_compiled # Placeholder for compiled version
    #
    #     print("\nBenchmarking `percentile` function (compiled version if available)")
    #     for name, size in LIST_SIZES.items():
    #         print(f"\n--- {name.capitalize()} list ({size} elements) ---")
    #         random_list = generate_random_list(size)
    #         for p_val in PERCENTILES_TO_TEST:
    #             try:
    #                 avg_time = run_benchmark(math_compiled.percentile, random_list, p_val)
    #                 print(f"  Percentile {p_val:>5}: {avg_time * 1e6:.2f} µs per execution")
    #             except Exception as e:
    #                 print(f"  Percentile {p_val:>5}: Error - {e}")
    # except ImportError:
    #     print("\nCompiled version of math module not found, skipping its benchmark.")
    # except AttributeError:
    #     print("\nCompiled version does not have 'percentile', skipping its benchmark.")
