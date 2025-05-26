import random
import string
import timeit
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Sequence,
    Union,
)

from web3._utils.formatters import (
    apply_key_map,
    hex_to_integer,
    map_collection,
    recursive_map,
)

# --- Constants ---
NUMBER_OF_EXECUTIONS = 1000  # Number of times to execute the main statement for each timing loop
REPEAT_COUNT = 3  # Number of times to repeat the timing loop

# --- Test Data Generation ---

# For recursive_map and map_collection
def simple_transform(val: Any) -> Any:
    if isinstance(val, int):
        return str(val) + "_transformed"
    elif isinstance(val, str):
        return val + "!"
    return val # Should not happen with current test data, but good practice

def generate_nested_dict(levels: int, keys_per_level: int) -> Dict[Any, Any]:
    if levels == 0:
        return {f"leaf_key_{i}": random.randint(0, 100) for i in range(keys_per_level)}
    return {
        f"key_{level}_{i}": generate_nested_dict(levels - 1, keys_per_level)
        if i % 2 == 0 else (f"str_val_{level}_{i}" if i%3 == 0 else random.randint(100,200) )
        for i in range(keys_per_level)
        for level in [levels] # just to use level in f-string
    }

def generate_nested_list(levels: int, items_per_level: int) -> List[Any]:
    if levels == 0:
        return [random.randint(0, 100) if i % 2 == 0 else f"leaf_str_{i}" for i in range(items_per_level)]
    return [
        generate_nested_list(levels - 1, items_per_level)
        if i % 2 == 0 else (f"str_val_{levels}_{i}" if i%3 == 0 else random.randint(100,200) )
        for i in range(items_per_level)
    ]

# For apply_key_map
SAMPLE_DICT_FOR_KEY_MAP: Dict[str, Any] = {
    f"original_key_{i}": random.randint(0, 1000) for i in range(10)
}
SAMPLE_KEY_MAPPINGS: Dict[str, str] = {
    "original_key_1": "new_key_one",
    "original_key_3": "new_key_three",
    "original_key_5": "new_key_five",
    "non_existent_key": "should_not_appear", # To test non-mapped keys
}

# For hex_to_integer
HEX_STRING_CASES: List[Dict[str, str]] = [
    {"description": "short hex (0x0)", "value": "0x0"},
    {"description": "short hex (0xa)", "value": "0xa"},
    {"description": "medium hex", "value": "0x" + "1" * 8}, # 0x11111111
    {"description": "longer hex", "value": "0x" + "f" * 16}, # 0xffffffffffffffff
    {"description": "max_uint256_approx", "value": "0x" + "f" * 64},
]


# --- Benchmark Execution Helper ---
def run_benchmark(
    description: str,
    func_to_benchmark: Callable[..., Any],
    *args: Any,
) -> None:
    """Runs the benchmark for a given function and arguments, prints the result."""
    func_name = func_to_benchmark.__name__

    setup_code = f"from web3._utils.formatters import {func_name}"
    if func_name == "recursive_map" or func_name == "map_collection":
        # The 'simple_transform' function needs to be in globals for timeit
        setup_code += "\nfrom __main__ import simple_transform"


    benchmark_globals: Dict[str, Any] = {
        func_name: func_to_benchmark,
    }
    if func_name == "recursive_map" or func_name == "map_collection":
        benchmark_globals["simple_transform"] = simple_transform

    arg_names = []
    for i, arg_val in enumerate(args):
        arg_name = f"arg{i}"
        benchmark_globals[arg_name] = arg_val
        arg_names.append(arg_name)

    stmt_code = f"{func_name}({', '.join(arg_names)})"

    try:
        times = timeit.repeat(
            stmt=stmt_code,
            setup=setup_code,
            globals=benchmark_globals,
            repeat=REPEAT_COUNT,
            number=NUMBER_OF_EXECUTIONS,
        )
        avg_time_per_execution = min(times) / NUMBER_OF_EXECUTIONS
        print(
            f"  {description:<50}: {avg_time_per_execution * 1e6:.2f} µs per execution",
            flush=True,
        )
    except Exception as e:
        print(f"  {description:<50}: Error - {e}", flush=True)


# --- Main Execution ---
if __name__ == "__main__":
    print(
        f"Starting Formatter Benchmarks ({NUMBER_OF_EXECUTIONS} executions per test, "
        f"{REPEAT_COUNT} repeats, best time taken)\n",
        flush=True
    )

    # --- recursive_map benchmarks ---
    print("--- recursive_map benchmarks ---", flush=True)
    nested_dict_data = generate_nested_dict(levels=3, keys_per_level=4)
    nested_list_data = generate_nested_list(levels=3, items_per_level=4)

    run_benchmark(
        "nested dictionary (3 levels, 4 keys/level)",
        recursive_map,
        simple_transform, # func arg for recursive_map
        nested_dict_data  # data arg for recursive_map
    )
    run_benchmark(
        "nested list (3 levels, 4 items/level)",
        recursive_map,
        simple_transform, # func arg for recursive_map
        nested_list_data  # data arg for recursive_map
    )

    # --- map_collection benchmarks ---
    print("\n--- map_collection benchmarks ---", flush=True)
    flat_list_data = [random.randint(0, 100) for _ in range(100)]
    flat_dict_data = {f"key_{i}": random.randint(0, 100) for i in range(100)}

    run_benchmark(
        "flat list (100 integers)",
        map_collection,
        simple_transform, # func arg for map_collection
        flat_list_data    # data arg for map_collection
    )
    run_benchmark(
        "flat dictionary (100 int values)",
        map_collection,
        simple_transform, # func arg for map_collection
        flat_dict_data    # data arg for map_collection
    )

    # --- apply_key_map benchmarks ---
    print("\n--- apply_key_map benchmarks ---", flush=True)
    # apply_key_map is curried. Benchmark the fully applied function.
    # So, we create a callable that takes the dictionary as its argument.
    # func_to_benchmark = apply_key_map(SAMPLE_KEY_MAPPINGS)
    # Then call run_benchmark("...", func_to_benchmark, SAMPLE_DICT_FOR_KEY_MAP)
    # However, apply_key_map itself is the target.
    # The way it's defined, it returns a generator. We should consume it.
    # For benchmark, it's better to benchmark `dict(apply_key_map(key_mappings, data_dict))`
    # or ensure the curried version is correctly called.
    # The current `apply_key_map` is curried and then decorated with `@to_dict`.
    # So `apply_key_map(SAMPLE_KEY_MAPPINGS, SAMPLE_DICT_FOR_KEY_MAP)` should work directly.
    run_benchmark(
        "dictionary with key renaming (10 keys, 3 remapped)",
        apply_key_map,
        SAMPLE_KEY_MAPPINGS,
        SAMPLE_DICT_FOR_KEY_MAP
    )

    # --- hex_to_integer benchmarks ---
    print("\n--- hex_to_integer benchmarks ---", flush=True)
    for case in HEX_STRING_CASES:
        run_benchmark(
            case["description"],
            hex_to_integer,
            case["value"]
        )

    print("\nBenchmarking finished.", flush=True)
