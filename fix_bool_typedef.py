#!/usr/bin/env python3
"""Fix the bool typedef collision in generated_bridge.dart.

The flutter_rust_bridge_codegen + ffigen generates a typedef like:
  typedef bool = ffi.NativeFunction<ffi.Int Function(ffi.Pointer<ffi.Int>)>;

This shadows Dart's built-in `bool` type, causing type errors in other files.

Fix strategy:
1. Remove the `typedef bool = ...` line entirely
2. In NativeFunction<> signatures (which define the C types), replace
   ffi.Pointer<bool> with ffi.Pointer<ffi.Bool>
3. In .asFunction<> calls (which define Dart types), keep bool as-is since
   Dart FFI automatically converts ffi.Bool to Dart bool
4. In the wrapper functions' parameter lists, replace Pointer<bool> with
   ffi.Pointer<ffi.Bool> to match the NativeFunction signatures
5. Apply the DartPort Bool->Uint8 fix from build.py
"""
import re

filepath = 'flutter/lib/generated_bridge.dart'

with open(filepath, 'r') as f:
    content = f.read()

# 1. Remove the typedef bool line
content = re.sub(
    r'typedef bool = ffi\.NativeFunction<ffi\.Int Function\(ffi\.Pointer<ffi\.Int>\)>;\n',
    '',
    content
)

# 2. Apply the DartPort Bool->Uint8 fix (from build.py's ffi_bindgen_function_refactor)
content = content.replace(
    'ffi.NativeFunction<ffi.Bool Function(DartPort',
    'ffi.NativeFunction<ffi.Uint8 Function(DartPort'
)

# 3. In NativeFunction<> signatures, replace ffi.Pointer<bool> with ffi.Pointer<ffi.Bool>
# These are within _lookup<ffi.NativeFunction<...>> calls
# We need to be careful to only replace in NativeFunction context

# Replace in ffi.NativeFunction signatures (C-level type declarations)
def fix_native_function(match):
    """Replace bool with ffi.Bool inside NativeFunction<> signatures."""
    text = match.group(0)
    # Replace Pointer<bool> with Pointer<ffi.Bool> inside NativeFunction<>
    text = text.replace('ffi.Pointer<bool>', 'ffi.Pointer<ffi.Bool>')
    return text

content = re.sub(
    r'ffi\.NativeFunction<[^>]+(?:<[^>]*>)*[^>]*>',
    fix_native_function,
    content
)

# 4. Fix the wrapper function parameter types: Pointer<bool> -> ffi.Pointer<ffi.Bool> 
# These are in the wire_xxx function signatures
# e.g., ffi.Pointer<bool> prompt, -> ffi.Pointer<ffi.Bool> prompt,
content = content.replace('ffi.Pointer<bool>', 'ffi.Pointer<ffi.Bool>')

# 5. Fix .asFunction<> calls: Pointer<bool> -> ffi.Pointer<ffi.Bool>
# In Dart FFI, the Dart type for ffi.Pointer<ffi.Bool> is still ffi.Pointer<ffi.Bool>
# (pointers don't auto-convert like scalar types)
# But ffi.Bool -> bool auto-converts in .asFunction

# Also fix any remaining bare `bool` in asFunction where it used to be the typedef
# Actually, in asFunction, the Dart equivalent of C's Bool is Dart's bool, so keep it

with open(filepath, 'w') as f:
    f.write(content)

print("Fixed bool typedef issues in generated_bridge.dart")

# Count remaining issues
remaining = content.count('ffi.Pointer<bool>')
print(f"Remaining ffi.Pointer<bool> occurrences: {remaining}")
remaining_typedef = content.count('typedef bool')
print(f"Remaining typedef bool: {remaining_typedef}")
