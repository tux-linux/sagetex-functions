import sys
import re
import os

def process_file(filename):
    if not os.path.exists(filename):
        sys.stderr.write(f"Error: File '{filename}' not found.\n")
        return

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()

        if not content:
            sys.stderr.write("File is empty. Nothing to process.\n")
            return

        # 1. Define the number wrapping logic
        def wrap_numbers_in_math(text):
            # SKIP PATTERNS: If the regex matches these, it returns them unchanged (Group 1)
            # This ensures we don't double-wrap or break existing macros.
            skip = [
                r'\\nums?\{[^}]*\}',                # Matches \num{...} and \nums{...}
                r'\\qtys?\{[^}]*\}(?:\{[^}]*\})?',  # Matches \qty{v}{u}, \qty{v}, \qtys{v}{u}, etc.
                r'\\begin\{[^}]*\}',                # Environment starts
                r'\\end\{[^}]*\}',                  # Environment ends
                r'\\color\{[^}]*\}',                # Color commands
                r'_[0-9a-zA-Z\{\}\\]+',             # Subscripts: I_{x}, I_{\mathit{HE}}
                r'\^[0-9a-zA-Z\{\}\\]+',            # Superscripts: V^{2}
                r'[a-zA-Z]+\d+',                    # Variables: R1, V2
            ]
            
            # Combine skips and the target (Group 2: standalone numbers)
            regex_str = r'(' + '|'.join(skip) + r')|(\b\d+(?:\.\d+)?\b)'
            pattern = re.compile(regex_str)

            def replacer(match):
                if match.group(2): # If we found a raw number in Group 2
                    return r'\num{' + match.group(2) + '}'
                return match.group(1) # Return the skipped text from Group 1 as-is

            return pattern.sub(replacer, text)

        # 2. Match the SageTeX \newlabel structure
        # Prefix: \newlabel{@sageinlineX}{{% [whitespace]
        # Content: The math (lazy match)
        # Suffix: }{}{}{}{}} (The standard LaTeX label suffix for SageTeX)
        block_pattern = re.compile(
            r'(\\newlabel\{@sageinline\d+\}\{\{%\s*)(.*?)(\}\{?\}\{?\}\{?\}\{?\}\})', 
            re.DOTALL
        )

        def block_replacer(match):
            prefix, math_content, suffix = match.groups()
            
            # If the block is ALREADY just a pure quantity or number command, leave it.
            # This prevents issues like \qty{\num{4}}{V}
            stripped = math_content.strip()
            if stripped.startswith(('\\qty', '\\num')):
                return match.group(0)
            
            processed_math = wrap_numbers_in_math(math_content)
            return prefix + processed_math + suffix

        # 3. Apply the transformation
        new_content, count = block_pattern.subn(block_replacer, content)

        # 4. Final Output handling
        if count == 0:
            sys.stderr.write("Warning: No @sageinline blocks found. Is the file format correct?\n")
            # If nothing matched, output original content to prevent losing data
            print(content, end='')
        else:
            sys.stderr.write(f"Successfully wrapped numbers in {count} blocks.\n")
            print(new_content, end='')

    except Exception as e:
        sys.stderr.write(f"An unexpected error occurred: {e}\n")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: python wrap_math_numbers.py <filename>\n")
    else:
        process_file(sys.argv[1])
