import re
import itertools
from typing import (
    TYPE_CHECKING,
    Optional, # Added import
)

from eth_typing import (
    TypeStr,
)

if TYPE_CHECKING:
    # This avoids a circular import if these types are ever needed here directly for more complex logic
    # For now, only TypeStr is used from eth_typing directly in this file.
    pass

# --- Constants for ABI type checking ---
DYNAMIC_TYPES = ["bytes", "string"]

INT_SIZES = range(8, 257, 8)
BYTES_SIZES = range(1, 33) # bytes1 to bytes32

UINT_TYPES = [f"uint{i}" for i in INT_SIZES]
INT_TYPES = [f"int{i}" for i in INT_SIZES]
# Includes "bytes32.byte" which seems specific or legacy, keeping if it was in original
# For simplicity, assuming BYTES_TYPES are just bytes1..32 for now.
# The original definition was: BYTES_TYPES = [f"bytes{i}" for i in BYTES_SIZES] + ["bytes32.byte"]
# Let's stick to the core bytesN for clarity unless "bytes32.byte" is essential elsewhere.
# For now, using the simpler list that corresponds to actual ABI types bytes1...bytes32
BYTES_M_TYPES = [f"bytes{i}" for i in BYTES_SIZES]


STATIC_TYPES = list(
    itertools.chain(
        ["address", "bool"],
        UINT_TYPES,
        INT_TYPES,
        BYTES_M_TYPES, # Using BYTES_M_TYPES here
    )
)

BASE_TYPE_REGEX = "|".join(
    _type + "(?![a-z0-9])" for _type in itertools.chain(STATIC_TYPES, DYNAMIC_TYPES)
)

SUB_TYPE_REGEX = r"\[" "[0-9]*" r"\]" # Matches array declarations like "[2]" or "[]"

TYPE_REGEX = ("^" "(?:{base_type})" "(?:(?:{sub_type})*)?" "$").format(
    base_type=BASE_TYPE_REGEX,
    sub_type=SUB_TYPE_REGEX,
)

ARRAY_REGEX = ("^" "[a-zA-Z0-9_]+" "({sub_type})+" "$").format(sub_type=SUB_TYPE_REGEX)

NAME_REGEX = "[a-zA-Z_]" "[a-zA-Z0-9_]*"

ENUM_REGEX = ("^" "{lib_name}" r"\." "{enum_name}" "$").format(
    lib_name=NAME_REGEX, enum_name=NAME_REGEX
)

# --- Type Predicate Functions ---

def is_recognized_type(abi_type: TypeStr) -> bool:
    return bool(re.match(TYPE_REGEX, abi_type))

def is_bool_type(abi_type: TypeStr) -> bool:
    return abi_type == "bool"

def is_uint_type(abi_type: TypeStr) -> bool:
    # Check against the generated list of uint types (e.g., "uint8", ..., "uint256")
    return abi_type in UINT_TYPES

def is_int_type(abi_type: TypeStr) -> bool:
    # Check against the generated list of int types (e.g., "int8", ..., "int256")
    return abi_type in INT_TYPES

def is_address_type(abi_type: TypeStr) -> bool:
    return abi_type == "address"

def is_bytes_type(abi_type: TypeStr) -> bool:
    # This should match "bytes" (dynamic) and "bytesN" (fixed-size)
    if abi_type == "bytes":
        return True
    if abi_type.startswith("bytes") and abi_type[5:].isnumeric():
        size = int(abi_type[5:])
        if 1 <= size <= 32:
            return True
    return False

def is_string_type(abi_type: TypeStr) -> bool:
    return abi_type == "string"

def is_array_type(abi_type: TypeStr) -> bool:
    return bool(re.match(ARRAY_REGEX, abi_type))

def is_probably_enum(abi_type: TypeStr) -> bool: # Used in normalize_event_input_types
    return bool(re.match(ENUM_REGEX, abi_type))

# --- Array specific utilities ---

END_BRACKETS_OF_ARRAY_TYPE_REGEX = r"\[[^]]*\]$"

def sub_type_of_array_type(abi_type: TypeStr) -> str:
    if not is_array_type(abi_type): # is_array_type is defined in this module
        raise ValueError(f"Cannot parse subtype of nonarray abi-type: {abi_type}") # Changed to ValueError for generic util
    return re.sub(END_BRACKETS_OF_ARRAY_TYPE_REGEX, "", abi_type, count=1)

def length_of_array_type(abi_type: TypeStr) -> Optional[int]:
    if not is_array_type(abi_type): # is_array_type is defined in this module
        raise ValueError(f"Cannot parse length of nonarray abi-type: {abi_type}") # Changed to ValueError

    match = re.search(END_BRACKETS_OF_ARRAY_TYPE_REGEX, abi_type)
    if match is None:
        return None # Should not happen if is_array_type passed and regex is correct
    
    inner_brackets = match.group(0).strip("[]")
    if not inner_brackets: # Dynamic array like 'uint[]'
        return None
    else: # Fixed-size array like 'uint[2]'
        return int(inner_brackets)
