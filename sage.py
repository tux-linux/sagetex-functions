\begin{sagesilent}
import sympy as sp

DIV  = "/"
TIMES = "*"
PLUS = "+"
POW = "^"

IGNORE_PRECISION_CHECKS = False

def ignore_precision_checks():
    global IGNORE_PRECISION_CHECKS
    IGNORE_PRECISION_CHECKS = True
    return ""

def _latex_or_number(X, precision):
    if (X.parent() == SR and X.variables()) or (IGNORE_PRECISION_CHECKS == False and X.is_integer() == False and precision == 0) or precision == None:
        return r"{\color{red}" + latex(X) + "}", True
    return "{:.{prec}f}".format(X.n(), prec=precision), False

def num(X, precision):
    val, bool = _latex_or_number(X, precision)
    if bool:
        return val
    return r"\num{{{}}}".format(val)

def qty(X, precision, unit):
    val, bool = _latex_or_number(X, precision)
    if bool:
        return val
    return r"\qty{{{}}}{}".format(val, unit)

def svar(name, lname=None):
    symbolic_var = var(name, latex_name=lname)
    globals()[f"_{name}"] = symbolic_var
    return symbolic_var

# Return parent: return r"\text{{{}}}".format(X.parent()

# ── helpers ────────────────────────────────────────────────────────────────────

def _is_op(e):
    return e in (DIV, TIMES, PLUS, POW)

def _is_symbolic(sage_val):
    """True if sage_val is a bare symbol or product of symbols (no numeric coeff)."""
    if sage_val.parent() != SR:
        return False
    if sage_val.is_symbol():
        return True
    op = sage_val.operator()
    if op is not None and op.__name__ in ('mul_vararg', 'mul'):
        return all(o.is_symbol() for o in sage_val.operands())
    return False

def _can_add_parens(lt, pow):
    return not (lt.startswith(r"\left(")) and (r"\cdot" in lt or (any(c.isalpha() for c in lt)) and not lt.isalpha()) and not lt.startswith(r"\frac{")

# ── parser ─────────────────────────────────────────────────────────────────────

def _parse(elements, default_op=PLUS):
    """
    Parse a list of values and operator tokens into (sage_value, latex_string).
    Nested lists are parsed recursively with default_op=TIMES.
    Adjacent non-op items get `default_op` inserted implicitly.
    """
    # Insert implicit operators between adjacent non-op items
    expanded = []
    for e in elements:
        if expanded and not _is_op(e) and not _is_op(expanded[-1]):
            expanded.append(default_op)
        expanded.append(e)

    # Collect terms as (op_before, sage_val, latex_str, is_nested)
    terms, current_op = [], PLUS
    for e in expanded:
        if _is_op(e):
            current_op = e
            continue
        if isinstance(e, list):
            sv, lt = _parse(e, default_op=TIMES)
            terms.append((current_op, sv, lt, True))
        else:
            terms.append((current_op, e, latex(e), False))
        current_op = PLUS  # reset after consuming; explicit op overrides next

    return _combine(terms)

def _combine(terms):
    """
    Fold terms into (sage, latex) respecting precedence:
    POW binds tightest, then TIMES/DIV, then PLUS.
    """
    # Group into additive chunks; each chunk is a run of TIMES/DIV/POW factors
    groups, current_group = [], []
    for (op, sv, lt, nested) in terms:
        if op == PLUS and current_group:
            groups.append(current_group)
            current_group = []
        current_group.append((op, sv, lt, nested))
    if current_group:
        groups.append(current_group)

    add_sages, add_latexs = [], []
    for group in groups:
        is_fraction = any(op == DIV for (op, *_) in group)
        if is_fraction:
            gs, gl = _build_fraction(group)
            wrap = False  # fractions provide their own visual grouping
        else:
            gs, gl = _build_product(group)
            # Wrap in parens condition
            wrap = (len(groups) > 1) and r"\cdot" in gl and r"\sqrt" not in gl

        add_sages.append(gs)
        if wrap:
            add_latexs.append(r"\left(%s\right)" % gl)
        else:
            add_latexs.append(gl)

    final_sage  = sum(add_sages)
    final_latex = add_latexs[0]
    for sv, lt in zip(add_sages[1:], add_latexs[1:]):
        if lt.lstrip().startswith('-'):
            final_latex += lt
        else:
            final_latex += '+' + lt

    return final_sage, final_latex

def _build_product(group, force_no_parens=False):
    """
    Render a run of TIMES/POW factors into (sage, latex).
    POW has higher precedence than TIMES.

    In the group, each item is (op_before, sage_val, latex_str, is_nested).
    When we see POW as op_before on item[i], it means item[i-1] ^ item[i].

    Parentheses rules:
      - Never if force_no_parens (inside \\frac)
      - Never if this nested subexpression is the only factor in the group
      - Never if the subexpression is purely symbolic (renders as e.g. xy)
      - Always if the subexpression contains addition (ambiguous without parens)

    \\cdot rules:
      - Omit \\cdot when the right factor is purely symbolic (write '3x' not '3 \\cdot x')
      - Include \\cdot otherwise
    """
    # First, handle POW operations (right-associative, highest precedence)
    # Process from right to left for right-associativity
    processed = []
    i = 0
    while i < len(group):
        op, sv, lt, nested = group[i]

        # If this element has POW as its operator, it means: previous_element ^ this_element
        # But we need to look ahead to see if we should process it now
        if op == POW:
            # This shouldn't be the first element
            if not processed:
                raise ValueError("POW operator cannot be first in expression")

            # Pop the previous element (the base)
            base_op, base_sv, base_lt, base_nested = processed.pop()

            # Current element is the exponent
            exp_sv, exp_lt = sv, lt

            # Build sage expression
            result_sv = base_sv ** exp_sv

            # Build latex expression
            result_lt = ""
            if exp_sv == 1/2:
                result_lt = r"\sqrt{%s}" % base_lt
            else:
                if _can_add_parens(base_lt, True):
                    base_lt = r"\left(%s\right)" % base_lt
                result_lt = base_lt + "^{" + exp_lt + "}"

            # Add the power result back with the original operator from the base
            processed.append((base_op, result_sv, result_lt, False))
        else:
            # Not a power operation, just add it
            processed.append((op, sv, lt, nested))

        i += 1

    # Now handle TIMES operations on the processed list
    sage_val = product(sv for (_, sv, _, _) in processed)
    only_one = (len(processed) == 1)

    parts = []
    for (_, sv, lt, nested) in processed:
        if nested and not force_no_parens and not only_one:
            # Add parens if the nested term contains + or - AND isn't already grouped
            if _can_add_parens(lt, False):
                lt = r"\left(%s\right)" % lt
        parts.append((sv, lt))

    latex_parts = [parts[0][1]]
    for (sv, lt) in parts[1:]:
        if _is_symbolic(sv):
            latex_parts.append(r" \, " + lt)           # juxtapose: no \cdot
        else:
            latex_parts.append(r" \cdot " + lt)

    return sage_val, "".join(latex_parts)

def _build_fraction(group):
    """Render a TIMES/DIV/POW group as \\frac{numerator}{denominator}."""
    num_parts, den_parts, in_denom = [], [], False
    for (op, sv, lt, nested) in group:
        if op == DIV:
            in_denom = True
        (den_parts if in_denom else num_parts).append((op, sv, lt, nested))

    # Numerator/denominator are single items — no parens needed inside \frac
    ns, nl = _build_product(num_parts, force_no_parens=True)
    ds, dl = _build_product(den_parts, force_no_parens=True)
    return ns / ds, r"\frac{%s}{%s}" % (nl, dl)

# ── public API ─────────────────────────────────────────────────────────────────

def dexpr(lhs, rhs=None):
    """
    Build a (Sage expression, LaTeX string) pair.

    Top-level default operator: PLUS.
    Nested list default operator: TIMES.
    Explicit tokens DIV / TIMES / PLUS / POW override the default locally.

    Examples:
        x = svar('x')
        dexpr([4, 3, [4, TIMES, x], [5, DIV, 4], [4, TIMES, [5, PLUS, 3]]])
        dexpr([2, TIMES, x, POW, 2])  # 2x^2
        dexpr([x, POW, 2, PLUS, y, POW, 2])  # x^2 + y^2
        dexpr([2, TIMES, x], [10])
    """
    lhs_sage, lhs_lat = _parse(lhs, default_op=PLUS)
    if rhs is None:
        return lhs_sage, LatexExpr(lhs_lat)
    rhs_sage, rhs_lat = _parse(rhs, default_op=PLUS)
    return (lhs_sage == rhs_sage), LatexExpr(lhs_lat + '=' + rhs_lat)

def matdexpr(mat):
    if hasattr(mat, 'rows'):
        mat = [[[entry] for entry in row] for row in mat.rows()]

    # Determine columns from the first row
    n_cols = len(mat[0])
    m = matrix(SR, 0, n_cols)

    lt = r"\left(\begin{array}{" + "r" * n_cols + "}"

    for row in mat:
        sage_row = []
        for element in row:
            lt += r"\quad "
            # Handle [value, latex_string] or just [value]
            if isinstance(element, (list, tuple)) and len(element) > 1:
                lt += str(element[1])
                sage_row.append(element[0])
            else:
                val = element[0] if isinstance(element, (list, tuple)) else element
                lt += latex(val)
                sage_row.append(val)
            lt += r" &"

        row_to_stack = matrix(SR, [sage_row])
        m = m.stack(row_to_stack)

        lt = lt[:-1] + r"\\"
    lt = lt[:-2] + r"\end{array}\right)"
    return m, LatexExpr(lt)

def prepare_rref_matrix(LHS, VAR, RHS, unit=None, precision=None):
    sys = list(LHS * VAR - RHS)
    CONSTS = matrix(ZZ, 0, 1)
    fvars = list(VAR.list())
    COEFFS = matrix(SR, 0, len(fvars))

    for expr in sys:
        const = -expr[0].subs({v: 0 for v in fvars})
        CONSTS = CONSTS.stack(vector([const]))

    i = 0
    while i < len(sys):
        sys[i][0] = sys[i][0] + CONSTS[i][0]
        COEFFS = COEFFS.stack(jacobian(sys[i][0], fvars))
        i += 1

    AUG = COEFFS.augment(CONSTS, subdivide=True)
    RREF = AUG.rref()
    lt = latex(AUG) + r"\sim"
    n_fvars = len(fvars)

    pivot_cols = list(RREF.pivots())
    sol_dict = {}
    for col_idx, var in enumerate(fvars):
        if col_idx in pivot_cols:
            row_idx = pivot_cols.index(col_idx)
            sol_dict[var] = RREF[row_idx, n_fvars]

    lt += display_rref_matrix(RREF, fvars, pivot_cols, unit, precision)
    return RREF, lt, sol_dict


def display_rref_matrix(RREF, fvars, pivot_cols, unit=None, precision=None):
    n_fvars = len(fvars)
    lt = latex(RREF) + r"\Longrightarrow\begin{cases}"

    fvars_sorted = sorted(list(fvars), key=str)

    for col_idx, var in enumerate(fvars_sorted):
        # Find original index (before sorting) to check pivot
        orig_idx = list(fvars).index(var)
        if orig_idx in pivot_cols:
            row_idx = pivot_cols.index(orig_idx)
            lt += latex(var) + r"="
            val = RREF[row_idx, n_fvars]
            if precision is None:
                lt += latex(val)
            elif not isinstance(unit, str):
                lt += num(val, precision)
            else:
                lt += qty(val, precision, unit)
        else:
            lt += latex(var) + r"\text{\:: variable libre}"
        lt += r"\\"

    lt += r"\end{cases}"
    return lt

def extract_equations_matrix_product(LHS, VAR, RHS):
    lhs = list(LHS * VAR)
    rhs = list(RHS)
    return [lhs, rhs]

\end{sagesilent}
