import random
import string
import timeit
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
)

# Functions to benchmark
from web3._utils.validation import (
    validate_abi,
    validate_abi_value,
    validate_address,
    validate_rpc_response_and_raise_if_error,
)

# Types and exceptions for test data and error handling
from eth_typing import (
    ABI,
    ABIFunction,
    HexStr,
    TypeStr,
    # RPCResponse was incorrectly imported from here
)
from web3.types import ( # Correct import for RPCResponse
    RPCResponse,
)
from web3.exceptions import (
    InvalidAddress,
    Web3ValueError, # For ABI validation errors
    Web3RPCError,   # For RPC error responses
    Web3TypeError,  # For ABI value type errors
)


# --- Constants ---
NUMBER_OF_EXECUTIONS = 1000
REPEAT_COUNT = 3

# --- Test Data Generation ---

# For validate_abi_value
VALIDATE_ABI_VALUE_CASES: List[Dict[str, Any]] = [
    {"description": "uint256 (valid int)", "abi_type": "uint256", "value": 123456789012345678901234567890, "raises": None},
    {"description": "uint256 (str int should fail)", "abi_type": "uint256", "value": "98765432109876543210", "raises": Web3TypeError},
    {"description": "address (valid checksum)", "abi_type": "address", "value": "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B", "raises": None},
    {"description": "bytes32 (valid hex)", "abi_type": "bytes32", "value": "0x" + "a" * 64, "raises": None},
    {"description": "string (valid str)", "abi_type": "string", "value": "Hello Web3! This is a test string.", "raises": None},
    {"description": "bool (True)", "abi_type": "bool", "value": True, "raises": None},
    {"description": "bool (False)", "abi_type": "bool", "value": False, "raises": None},
    {"description": "uint256[] (small list)", "abi_type": "uint256[]", "value": [1, 2, 3, 4, 5], "raises": None},
    {"description": "uint256 (invalid type for value)", "abi_type": "uint256", "value": "not_a_number", "raises": Web3TypeError},
    {"description": "address (invalid format)", "abi_type": "address", "value": "0x123", "raises": InvalidAddress}, # InvalidAddress for format
    {"description": "bytes32 (invalid length)", "abi_type": "bytes32", "value": "0x" + "a" * 60, "raises": Web3TypeError}, # Web3TypeError for wrong length bytes
]

# For validate_address
VALIDATE_ADDRESS_CASES: List[Dict[str, Any]] = [
    {"description": "valid checksummed address", "value": "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B", "raises": None},
    {"description": "invalid checksum (lowercase)", "value": "0xab5801a7d398351b8be11c439e05c5b3259aec9b", "raises": InvalidAddress},
    {"description": "valid ENS name", "value": "vitalik.eth", "raises": None}, # Assuming ENS validation logic doesn't resolve here
    {"description": "invalid ENS name (hyphen start)", "value": "-vitalik.eth", "raises": InvalidAddress},
    {"description": "invalid address (too short)", "value": "0x12345", "raises": InvalidAddress},
]

# For validate_abi
VALID_ABI_SIMPLE: ABI = [
    ABIFunction(type="function", name="myFunction", inputs=[], outputs=[])
]
ABI_WITH_SELECTOR_COLLISION: ABI = [
    ABIFunction(type="function", name="myFunction", inputs=[{"name": "a", "type": "uint256"}], outputs=[]),
    ABIFunction(type="function", name="myFunction", inputs=[{"name": "b", "type": "uint256"}], outputs=[]), # Same name and input types after normalization for selector
]
# A more direct collision based on identical signatures for selector generation
ABI_WITH_DIRECT_SELECTOR_COLLISION: ABI = [
    ABIFunction(type="function", name="collide", inputs=[{"name":"data", "type":"bytes"}], outputs=[]),
    ABIFunction(type="function", name="collide", inputs=[{"name":"data", "type":"bytes"}], outputs=[])
]


VALIDATE_ABI_CASES: List[Dict[str, Any]] = [
    {"description": "small valid ABI", "value": VALID_ABI_SIMPLE, "raises": None},
    {"description": "ABI with selector collision", "value": ABI_WITH_DIRECT_SELECTOR_COLLISION, "raises": Web3ValueError},
    {"description": "ABI not a list", "value": {"not_a": "list"}, "raises": Web3ValueError},
    {"description": "ABI list with non-dict", "value": [1,2,3], "raises": Web3ValueError}, # Corrected expected exception
]

# For validate_rpc_response_and_raise_if_error
VALID_RPC_RESPONSE: RPCResponse = {"jsonrpc": "2.0", "id": 1, "result": "0x1"}
ERROR_RPC_RESPONSE: RPCResponse = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32600, "message": "Invalid request"}}
# Note: validate_rpc_response_and_raise_if_error needs more args, typically error_formatters=None
VALIDATE_RPC_RESPONSE_CASES: List[Dict[str, Any]] = [
    {"description": "valid RPC response", "value": VALID_RPC_RESPONSE, "args_tuple": (None, False, None, []), "raises": None},
    {"description": "RPC response with error", "value": ERROR_RPC_RESPONSE, "args_tuple": (None, False, None, []), "raises": Web3RPCError},
]


# --- Benchmark Execution Helper ---
def run_benchmark(
    description: str,
    func_to_benchmark: Callable[..., Any],
    *args: Any, # Main arguments for the function
    benchmark_args_tuple: Optional[tuple] = None, # For functions like validate_rpc_response needing more fixed args
    expected_exception: Optional[type] = None,
) -> None:
    """Runs the benchmark for a given function and arguments, prints the result."""
    func_name = func_to_benchmark.__name__

    setup_parts = [f"from web3._utils.validation import {func_name}"]
    benchmark_globals: Dict[str, Any] = {
        func_name: func_to_benchmark,
    }

    if expected_exception:
        # For built-in exceptions, they don't need to be imported or added to globals.
        # For custom exceptions, they must be in benchmark_globals.
        # The current script imports custom exceptions (Web3ValueError etc.) at the top level,
        # making them available in __main__'s scope for benchmark_globals.
        if not hasattr(__builtins__, expected_exception.__name__):
            setup_parts.append(f"from __main__ import {expected_exception.__name__}")
            benchmark_globals[expected_exception.__name__] = expected_exception
        # If it's a built-in, it's already available to timeit's stmt.
    
    setup_code = "\n".join(setup_parts)

    # Prepare arguments for the statement
    stmt_arg_names = []
    for i, arg_val in enumerate(args):
        arg_name = f"main_arg{i}"
        benchmark_globals[arg_name] = arg_val
        stmt_arg_names.append(arg_name)
    
    if benchmark_args_tuple is not None:
        for i, b_arg_val in enumerate(benchmark_args_tuple):
            b_arg_name = f"bench_arg{i}"
            benchmark_globals[b_arg_name] = b_arg_val
            stmt_arg_names.append(b_arg_name)


    stmt_code = f"{func_name}({', '.join(stmt_arg_names)})"

    if expected_exception:
        stmt_code = f"try: {stmt_code}\nexcept {expected_exception.__name__}: pass"

    try:
        times = timeit.repeat(
            stmt=stmt_code,
            setup=setup_code,
            globals=benchmark_globals,
            repeat=REPEAT_COUNT,
            number=NUMBER_OF_EXECUTIONS,
        )
        avg_time_per_execution = min(times) / NUMBER_OF_EXECUTIONS
        suffix = " (error path)" if expected_exception else " (success path)"
        print(
            f"  {description:<50}: {avg_time_per_execution * 1e6:.2f} µs per execution{suffix}",
            flush=True,
        )
    except Exception as e:
        print(f"  {description:<50}: Error during benchmark - {type(e).__name__}: {e}", flush=True)


# --- Main Execution ---
if __name__ == "__main__":
    print(
        f"Starting Validation Logic Benchmarks ({NUMBER_OF_EXECUTIONS} executions per test, "
        f"{REPEAT_COUNT} repeats, best time taken)\n",
        flush=True
    )

    print("--- validate_abi_value benchmarks ---", flush=True)
    for case in VALIDATE_ABI_VALUE_CASES:
        run_benchmark(
            case["description"],
            validate_abi_value,
            case["abi_type"],
            case["value"],
            expected_exception=case["raises"]
        )

    print("\n--- validate_address benchmarks ---", flush=True)
    for case in VALIDATE_ADDRESS_CASES:
        run_benchmark(
            case["description"],
            validate_address,
            case["value"],
            expected_exception=case["raises"]
        )

    print("\n--- validate_abi benchmarks ---", flush=True)
    for case in VALIDATE_ABI_CASES:
        run_benchmark(
            case["description"],
            validate_abi,
            case["value"],
            expected_exception=case["raises"]
        )

    print("\n--- validate_rpc_response_and_raise_if_error benchmarks ---", flush=True)
    for case in VALIDATE_RPC_RESPONSE_CASES:
        run_benchmark(
            case["description"],
            validate_rpc_response_and_raise_if_error,
            case["value"], # This is the RPCResponse object
            benchmark_args_tuple=case["args_tuple"], # (error_formatters, is_subscription, logger, params)
            expected_exception=case["raises"]
        )

    print("\nBenchmarking finished.", flush=True)
