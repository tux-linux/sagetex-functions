#!/usr/bin/env python3
r"""
Wraps \sage{_xxx} with \pdftooltip{...}{definition line}
by scanning sagesilent blocks for lines that define _xxx variables.

If a variable is defined multiple times, the definition closest BEFORE each
usage site is used, so redefinitions are handled correctly.

WARNING: written by Claude AI. Use at your own risk, even though the logic seems good to me.
"""

import re
import sys
from collections import defaultdict


def extract_definitions(tex_content):
    """
    Scan sagesilent blocks for lines defining _varname variables.
    Returns dict: varname -> sorted list of (line_number, definition_string)
    All definitions are preserved so redefinitions are handled per-usage-site.
    """
    definitions = defaultdict(list)

    sagesilent_pattern = re.compile(
        r'\\begin\{sagesilent\}(.*?)\\end\{sagesilent\}',
        re.DOTALL
    )

    for block_match in sagesilent_pattern.finditer(tex_content):
        block = block_match.group(1)
        block_start_line = tex_content[:block_match.start()].count('\n')

        for i, line in enumerate(block.split('\n')):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            lineno = block_start_line + i

            # Pattern 1: var, _var = ...  (dexpr, matdexpr, svar, etc.)
            m = re.match(r'^\s*\w[\w]*\s*,\s*(_\w+)\s*=\s*(.+)', stripped)
            if m:
                varname = m.group(1).lstrip('_')
                definitions[varname].append((lineno, clean_for_tooltip(stripped)))
                continue

            # Pattern 2: _var = ...
            m = re.match(r'^\s*(_\w+)\s*=\s*(.+)', stripped)
            if m:
                varname = m.group(1).lstrip('_')
                definitions[varname].append((lineno, clean_for_tooltip(stripped)))
                continue

    # Sort each variable's definitions by line number
    for varname in definitions:
        definitions[varname].sort(key=lambda x: x[0])

    return definitions


def get_definition_at(definitions, varname, usage_lineno):
    """
    Return the definition of varname whose line number is closest to
    (but not after) usage_lineno. Falls back to first definition if none precede it.
    """
    entries = definitions.get(varname)
    if not entries:
        return None
    best = entries[0][1]  # fallback: first definition ever
    for lineno, defn in entries:
        if lineno <= usage_lineno:
            best = defn
        else:
            break  # list is sorted, stop early
    return best


def clean_for_tooltip(s):
    """Strip characters that break pdftooltip's plain-text argument."""
    s = s.strip()
    s = s.replace("\\", "")
    s = s.replace('{', '').replace('}', '')
    s = s.replace('$', '')
    s = s.replace('%', '')
    s = s.replace('#', '')
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def wrap_with_tooltip(tex_content, definitions):
    """
    Replace macros referencing _xxx variables with pdftooltip-wrapped versions,
    using the definition that was most recently assigned BEFORE the usage line.
    """
    lines = tex_content.split('\n')

    patterns = [
        (re.compile(r'\\sage\{(_\w+)\}'), 'sage'),
    ]

    result_lines = []
    for lineno, line in enumerate(lines):
        for compiled, macro_type in patterns:
            def make_replacer(lineno, definitions):
                def replacer(m):
                    full_match = m.group(0)
                    varname = m.group(1).lstrip('_')
                    defn = get_definition_at(definitions, varname, lineno)
                    if defn is None:
                        return full_match
                    return r'\pdftooltip{' + full_match + r'}{\detokenize{' + defn + r'}}'
                return replacer
            line = compiled.sub(make_replacer(lineno, definitions), line)
        result_lines.append(line)

    result = '\n'.join(result_lines)

    # Remove accidental double-wrapping, keeping innermost
    double_wrap = re.compile(
        r'\\pdftooltip\{'
        r'(\\pdftooltip\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}\{[^{}]*\})'
        r'\}\{[^{}]*\}'
    )
    while double_wrap.search(result):
        result = double_wrap.sub(r'\1', result)

    return result

def extract_dexpr_args(call_text):
    """
    From a dexpr/matdexpr call's argument text, extract all identifier names
    that are not operators or function names.
    """
    SKIP = {'DIV', 'TIMES', 'PLUS', 'MINUS', 'POW', 'dexpr', 'matdexpr', 'True', 'False', 'None'}
    identifiers = re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\b', call_text)
    return [name for name in identifiers if name not in SKIP and not name.startswith('_')]

def extract_full_call(lines, start_lineno):
    """
    Extract the full call text starting at start_lineno, handling multi-line calls.
    Returns (call_text, end_lineno).
    """
    call_text = ""
    for i in range(start_lineno, min(start_lineno + 20, len(lines))):
        call_text += lines[i]
        if call_text.count('(') > 0 and call_text.count('(') <= call_text.count(')'):
            return call_text, i
    return call_text, start_lineno

def inject_sym_registries(tex_content):
    """
    Find all dexpr/matdexpr calls in sagesilent blocks and inject
    _build_sym_registry({name: name_str, ...}) calls before each one.
    """
    lines = tex_content.split('\n')
    
    # Find sagesilent block ranges
    in_sagesilent = False
    sagesilent_ranges = []
    start = None
    for i, line in enumerate(lines):
        if r'\begin{sagesilent}' in line:
            in_sagesilent = True
            start = i
        elif r'\end{sagesilent}' in line and in_sagesilent:
            in_sagesilent = False
            sagesilent_ranges.append((start, i))

    # Find dexpr/matdexpr call lines within sagesilent blocks
    call_pattern = re.compile(r'\b(dexpr|matdexpr)\s*\(')
    
    injections = {}  # lineno -> registry call to insert before
    
    for block_start, block_end in sagesilent_ranges:
        for i in range(block_start, block_end):
            if call_pattern.search(lines[i]):
                call_text, end_line = extract_full_call(lines, i)
                names = extract_dexpr_args(call_text)
                if names:
                    # Build registry dict as a string: {'V': 'V', 'R_1': 'R_1', ...}
                    registry_str = '{' + ', '.join(f'"{n}": "{n}"' for n in names) + '}'
                    injections[i] = f'_set_sym_names({registry_str})'

    # Inject lines in reverse order to preserve line numbers
    result_lines = lines[:]
    for lineno in sorted(injections.keys(), reverse=True):
        # Match indentation of the call line
        indent = re.match(r'^(\s*)', result_lines[lineno]).group(1)
        result_lines.insert(lineno, indent + injections[lineno])

    return '\n'.join(result_lines)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 add_tooltips.py input.tex [output.tex]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.tex', '_tooltipped.tex')

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    print("Scanning for _variable definitions in sagesilent blocks...")
    definitions = extract_definitions(content)

    total_defs = sum(len(v) for v in definitions.values())
    multi = {k: v for k, v in definitions.items() if len(v) > 1}
    print(f"Found {len(definitions)} unique variables ({total_defs} total definitions).")
    if multi:
        print(f"  Variables redefined (will use closest preceding definition):")
        for k, entries in sorted(multi.items()):
            print(f"    _{k}: {len(entries)} definitions at lines {[e[0] for e in entries]}")

    print("\nWrapping macros with \\pdftooltip...")
    result = wrap_with_tooltip(content, definitions)

    tooltip_count = len(re.findall(r'\\pdftooltip\{\\(?:sage)', result))
    print(f"Added {tooltip_count} \\pdftooltip wrappers.")
    
    print("\nInjecting symbolic name registries for dexpr/matdexpr...")
    result = inject_sym_registries(result)
    
    inject_count = len(re.findall(r'_set_sym_names\(', result))
    print(f"Injected {inject_count} registry calls.")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(result)

    print(f"Output written to: {output_file}")


if __name__ == '__main__':
    main()
