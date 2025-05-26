import random
import string
import timeit
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Sequence,
)

from hexbytes import (
    HexBytes,
)

from web3._utils.encoding import (
    hex_encode_abi_type,
    to_json,
)

# Number of times to execute the main statement for each timing loop
NUMBER_OF_EXECUTIONS = 1000
# Number of times to repeat the timing loop
REPEAT_COUNT = 3


# --- Test Data Generation ---
def generate_random_bytes(length: int) -> bytes:
    return bytes(random.getrandbits(8) for _ in range(length))


def generate_random_hex_string(length: int) -> str:
    return "0x" + "".join(random.choices(string.hexdigits.lower(), k=length))


HEX_ENCODE_ABI_TYPE_CASES: List[Dict[str, Any]] = [
    {
        "description": "uint256",
        "abi_type": "uint256",
        "value": 12345678901234567890,
    },
    {
        "description": "address",
        "abi_type": "address",
        "value": "0x" + "1" * 40,
    },
    {
        "description": "bytes32",
        "abi_type": "bytes32",
        "value": b"\x01" * 32,
    },
    {
        "description": "string",
        "abi_type": "string",
        "value": "Hello, Web3!",
    },
    {"description": "bool (True)", "abi_type": "bool", "value": True},
    {"description": "bool (False)", "abi_type": "bool", "value": False},
    {
        "description": "uint256[] (small array)",
        "abi_type": "uint256[]",
        "value": [1, 2, 3],
    },
    {
        "description": "uint256[] (larger array)",
        "abi_type": "uint256[]",
        "value": list(range(100)),
    },
    {
        "description": "bytes (dynamic)",
        "abi_type": "bytes",
        "value": b"dynamic bytes array example",
    },
]

COMPLEX_DICT_FOR_TO_JSON: Dict[str, Any] = {
    "number": 12345,
    "hash": HexBytes("0x" + "a" * 64),
    "parentHash": HexBytes(generate_random_bytes(32)),
    "nonce": HexBytes(generate_random_bytes(8)),
    "sha3Uncles": HexBytes(generate_random_bytes(32)),
    "logsBloom": HexBytes(generate_random_bytes(256)),
    "transactionsRoot": HexBytes(generate_random_bytes(32)),
    "stateRoot": HexBytes(generate_random_bytes(32)),
    "receiptsRoot": HexBytes(generate_random_bytes(32)),
    "miner": generate_random_hex_string(40),
    "difficulty": 123456789012345,
    "totalDifficulty": 98765432109876543210,
    "extraData": HexBytes(b"some" + generate_random_bytes(28) + b"data"),
    "size": 9000,
    "gasLimit": 8000000,
    "gasUsed": 21000,
    "timestamp": timeit.default_timer(),  # float, will be handled by json
    "transactions": [
        HexBytes("0x" + "b" * 64),
        HexBytes("0x" + "c" * 64),
        HexBytes(generate_random_bytes(32)),
    ],
    "uncles": [HexBytes(generate_random_bytes(32))],
    "logs": [
        {
            "address": generate_random_hex_string(40),
            "topics": [
                HexBytes("0x" + "f" * 64),
                HexBytes(generate_random_bytes(32)),
            ],
            "data": HexBytes("0x123456" + generate_random_bytes(10).hex()),
            "blockNumber": 12340,
            "transactionHash": HexBytes(generate_random_bytes(32)),
            "transactionIndex": 0,
            "blockHash": HexBytes(generate_random_bytes(32)),
            "logIndex": 0,
            "removed": False,
        }
        for _ in range(3)  # Create a few log entries
    ],
    "baseFeePerGas": 10000000000, # Example EIP-1559 field
    "mixHash": HexBytes(generate_random_bytes(32)),
    "withdrawals": [ # Example EIP-4895 field
        {
            "index": i,
            "validatorIndex": 100 + i,
            "address": generate_random_hex_string(40),
            "amount": 32 * 10**9, # in gwei
        } for i in range(2)
    ],
    "withdrawalsRoot": HexBytes(generate_random_bytes(32)),
}


# --- Benchmark Execution ---
def run_benchmark(
    description: str,
    func_to_benchmark: Callable[..., Any],
    *args: Any,
) -> None:
    """Runs the benchmark for a given function and arguments, prints the result."""
    func_name = func_to_benchmark.__name__
    
    # Setup code should import the function directly from its module.
    # The arguments (arg0, arg1, ...) will be in the globals dict.
    # HexBytes might be needed for type hints or reconstruction in some edge cases,
    # but generally not if the objects are passed in directly.
    setup_code = f"from web3._utils.encoding import {func_name}"
    if func_name == "to_json": # for COMPLEX_DICT_FOR_TO_JSON which uses HexBytes
        setup_code += "\nfrom hexbytes import HexBytes"


    benchmark_globals = {func_name: func_to_benchmark}
    # Add HexBytes to globals if to_json is benchmarked, as test data uses it.
    if func_name == "to_json":
        benchmark_globals["HexBytes"] = HexBytes

    arg_names = []
    for i, arg in enumerate(args):
        arg_name = f"arg{i}"
        benchmark_globals[arg_name] = arg
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
            f"  {description:<40}: {avg_time_per_execution * 1e6:.2f} µs per execution",
            flush=True,
        )
    except Exception as e:
        print(f"  {description:<40}: Error - {e}", flush=True)


if __name__ == "__main__":
    print(
        f"Starting benchmarks ({NUMBER_OF_EXECUTIONS} executions per test, "
        f"{REPEAT_COUNT} repeats, best time taken)\n",
        flush=True
    )

    print("--- hex_encode_abi_type benchmarks ---", flush=True)
    for case in HEX_ENCODE_ABI_TYPE_CASES:
        run_benchmark(
            case["description"],
            hex_encode_abi_type,
            case["abi_type"],
            case["value"],
        )

    print("\n--- to_json benchmarks ---", flush=True)
    run_benchmark(
        "Complex Dictionary",
        to_json,
        COMPLEX_DICT_FOR_TO_JSON,
    )

    print("\nBenchmarking finished.", flush=True)
