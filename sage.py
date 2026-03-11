\begin{sagesilent}
import sympy as sp
import inspect

DIV  = "/"
TIMES = "*"
PLUS = "+"
MINUS = "-"
POW = "^"
NEG = "NEG"
DIFF = 'd'
PARTIAL = 'p'
def DERIV(dtype, num, den, order=None):
    return ('__deriv__', dtype, num, den, order)

NUM_QTY_COLOR = "blue"

PRECISION_CHECKS = True
RAT_ANS = True

_SYM_NAMES = {}
_SYM_COUNTS = {} # Ajout d'un dictionnaire de quotas

def _set_sym_names(d, counts=None):
    global _SYM_NAMES, _SYM_COUNTS
    _SYM_NAMES = d
    if counts is None:
        _SYM_COUNTS = {k: float('inf') for k in d} # Rétrocompatibilité
    else:
        _SYM_COUNTS = counts.copy()

def _id_to_sym(val):
    frame = inspect.currentframe()
    while frame is not None:
        for name, entry in _SYM_NAMES.items():
            if isinstance(entry, tuple):
                sage_name, latex_name = entry
            else:
                sage_name, latex_name = entry, None
            local_val = frame.f_locals.get(name)
            if local_val is val:
                # Vérifie si la variable a encore un "droit" d'être remplacée
                if _SYM_COUNTS.get(name, 0) > 0:
                    _SYM_COUNTS[name] -= 1
                    return SR.var(sage_name, latex_name=latex_name) if latex_name else SR.var(sage_name)
        frame = frame.f_back

    if val in QQ:
        return val

    frame = inspect.currentframe()
    while frame is not None:
        for name, entry in _SYM_NAMES.items():
            if isinstance(entry, tuple):
                sage_name, latex_name = entry
            else:
                sage_name, latex_name = entry, None
            local_val = frame.f_locals.get(name)
            if local_val is not None:
                try:
                    if local_val == -val:
                        if _SYM_COUNTS.get(name, 0) > 0:
                            _SYM_COUNTS[name] -= 1
                            sym = SR.var(sage_name, latex_name=latex_name) if latex_name else SR.var(sage_name)
                            return -sym
                except:
                    pass
        frame = frame.f_back

    return val

def _symbolify_list(elements):
    result = []
    for e in elements:
        if isinstance(e, list):
            result.append(_symbolify_list(e))
        elif _is_op(e):
            result.append(e)
        else:
            result.append(_id_to_sym(e))
    return result

def dexpr(lhs, rhs=None):
    if not _SYM_NAMES:
        return _dexpr(lhs, rhs)
    sym_lhs = _symbolify_list(lhs)
    sym_rhs = _symbolify_list(rhs) if rhs is not None else None
    _, sym_lhs_lat = _parse(sym_lhs, default_op=PLUS)
    if rhs is None:
        val, num_lat = _dexpr(lhs)
        if str(sym_lhs_lat) == str(num_lat):
            return val, num_lat
        return val, LatexExpr(sym_lhs_lat + '=' + str(num_lat))
    _, sym_rhs_lat = _parse(sym_rhs, default_op=PLUS)
    val, num_lat = _dexpr(lhs, rhs)
    # Extract just the numeric lhs=rhs part for comparison
    sym_combined = sym_lhs_lat + '=' + sym_rhs_lat
    _, num_only = _dexpr(lhs, rhs)
    if str(sym_combined) == str(num_only):
        return val, num_lat
    return val, LatexExpr(sym_lhs_lat + '=' + sym_rhs_lat + r'\Longrightarrow ' + str(num_lat))

def set_precision_checks(bool):
    global PRECISION_CHECKS
    PRECISION_CHECKS = bool
    return ""

def set_rational_answers(bool):
    global RAT_ANS
    RAT_ANS = bool
    return ""

def infinite_decimal(x):
    if x not in QQ:
        return True

    d = QQ(x).denominator()

    while d % 2 == 0:
        d //= 2
    while d % 5 == 0:
        d //= 5

    return d > 1

def _latex_or_number(X, precision, unit=None):
    if (X.parent() == SR and X.variables()) or (PRECISION_CHECKS == True and X.is_integer() == False and precision == 0) or precision == None:
        return "", r"{\color{red}" + latex(X) + "}", True

    pre_val = ""
    if RAT_ANS == True and X.is_integer() == False:
        pre_val += r"\left["
        pre_val += latex(X)
        pre_val += r"\right]"
        if isinstance(unit, str):
            pre_val += r"\:\mathrm{"
            pre_val += unit
            pre_val += r"}"

        # Check both: is it an infinite decimal, AND does rounding change the value?
        rounded = RR(("{:.{prec}f}".format(X.n(), prec=precision)))
        if infinite_decimal(X) or rounded != RR(X):
            pre_val += r"\approx"
        else:
            pre_val += "="

    val = "{:.{prec}f}".format(X.n(), prec=precision)
    return pre_val, val, False

def num(X, precision, color=True):
    pre_val, val, bool = _latex_or_number(X, precision)
    if bool:
        return val
    ret = r"{}".format(pre_val)
    if color:
        ret += r"\color{{{}}}".format(NUM_QTY_COLOR)
    ret += r"\num{{{}}}".format(val)
    return ret

def qty(X, precision, unit, color=True):
    pre_val, val, bool = _latex_or_number(X, precision, unit)
    if bool:
        return val
    ret = r"{}".format(pre_val)
    if color:
        ret += r"\color{{{}}}".format(NUM_QTY_COLOR)
    ret += r"\qty{{{}}}".format(val)
    ret += r"{{{}}}".format(unit)
    return ret

def svar(name, lname=None):
    symbolic_var = var(name, latex_name=lname)
    globals()[f"_{name}"] = symbolic_var
    return symbolic_var

# Return parent: return r"\text{{{}}}".format(X.parent()

#### HELPERS ####

def _is_op(e):
    return e in (DIV, TIMES, PLUS, POW, MINUS, NEG)

def _is_symbolic(sage_val):
    """True if sage_val is a bare symbol, function application, or product of such."""
    if sage_val.parent() != SR:
        return False
    if sage_val.is_symbol():
        return True
    # Function application like i(t), v_L(t)
    op = sage_val.operator()
    if op is not None and isinstance(op, sage.symbolic.function.SymbolicFunction):
        return True
    # Product of symbols/function applications
    if op is not None and hasattr(op, '__name__') and op.__name__ in ('mul_vararg', 'mul'):
        return all(_is_symbolic(o) for o in sage_val.operands())
    return False

def _can_add_parens(lt, pow):
    if lt.startswith(r"\left("):
        return False
    # Always wrap sums/differences (including leading negatives)
    if '+' in lt or '-' in lt:
        return True
    return (r"\cdot" in lt or (any(c.isalpha() for c in lt) and not lt.isalpha())) and not lt.startswith(r"\frac{")

#### PARSER ####

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

    # Resolve NEG tokens: NEG x -> (-x, "-latex(x)")
    resolved = []
    i = 0
    while i < len(expanded):
        e = expanded[i]
        if e == NEG:
            i += 1
            nxt = expanded[i]
            if isinstance(nxt, list):
                sv, lt = _parse(nxt, default_op=TIMES)
            else:
                sv, lt = nxt, latex(nxt)
            # Store as a special pre-negated tuple
            resolved.append(('__neg__', -sv, lt))
        else:
            resolved.append(e)
        i += 1

    # Collect terms as (op_before, sage_val, latex_str, is_nested)
    terms, current_op = [], PLUS
    for e in resolved:
        if isinstance(e, tuple) and e[0] == '__neg__':
            _, sv, lt = e
            # Prepend minus but mark as nested so _build_product can decide on parens
            terms.append((current_op, sv, "-" + lt, True))
            current_op = PLUS
        elif isinstance(e, tuple) and e[0] == '__deriv__':
            _, dtype, num, den, order = e
            sv, lt = _deriv_latex(dtype, num, den, order)
            terms.append((current_op, sv, lt, False))
            current_op = PLUS
        elif _is_op(e):
            current_op = e
        elif isinstance(e, list):
            sv, lt = _parse(e, default_op=TIMES)
            terms.append((current_op, sv, lt, True))
            current_op = PLUS
        else:
            terms.append((current_op, e, latex(e), False))
            current_op = PLUS

    return _combine(terms)

def _combine(terms):
    """
    Fold terms into (sage, latex) respecting precedence:
    POW binds tightest, then TIMES/DIV, then PLUS.
    """
    # Group into additive chunks; each chunk is a run of TIMES/DIV/POW factors
    groups, current_group = [], []
    for (op, sv, lt, nested) in terms:
        if op in (PLUS, MINUS) and current_group:
            groups.append(current_group)
            current_group = []
        current_group.append((op, sv, lt, nested))
    if current_group:
        groups.append(current_group)

    add_sages, add_latexs = [], []
    for group in groups:
        lead_op = group[0][0]
        is_fraction = any(op == DIV for (op, *_) in group)
        if is_fraction:
            gs, gl = _build_fraction(group)
            wrap = False
        else:
            gs, gl = _build_product(group)
            wrap = (len(groups) > 1) and r"\cdot" in gl and r"\sqrt" not in gl

        if lead_op == MINUS:
            gs = -gs

        add_sages.append(gs)
        if wrap:
            add_latexs.append((lead_op, r"\left(%s\right)" % gl))
        else:
            add_latexs.append((lead_op, gl))

    final_sage  = sum(add_sages)
    _, first_lt = add_latexs[0]
    final_latex = first_lt
    for sv, (op, lt) in zip(add_sages[1:], add_latexs[1:]):
        if op == MINUS:
            if lt.startswith(r"-\left("):  # already wrapped by NEG, don't double wrap
                final_latex += lt
            elif lt.lstrip().startswith('-'):
                final_latex += r"-\left(" + lt + r"\right)"
            else:
                final_latex += '-' + lt
        else:
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

def _deriv_latex(dtype, num, den, order=None):
    if isinstance(num, list):
        num_sage, num_lt = _parse(num, default_op=TIMES)
        num_simple = False
    else:
        num_sage, num_lt = num, latex(num)
        num_simple = True

    if isinstance(den, list):
        _, den_lt = _parse(den, default_op=TIMES)
        den_lt = r"\left(%s\right)" % den_lt
    else:
        den_sage = den
        den_lt = latex(den)

    # prefix = 'p' if dtype == 'p' else 'd'
    # cmd = prefix + ('ifs' if num_simple else 'if')
    # For now, keep it as-is, because Sage always displays numerator outside of fraction
    cmd = 'pif'

    order_lt = "[%s]" % latex(order) if order is not None else ""
    lt = r"\%s%s{%s}{%s}" % (cmd, order_lt, num_lt, den_lt)

    # Perform actual differentiation for the sage value
    n = order if order is not None else 1
    try:
        if dtype == 'p':
            diff_sage = num_sage.diff(den_sage, n)
        else:
            diff_sage = num_sage.diff(den_sage, n)
    except:
        diff_sage = num_sage  # fallback if differentiation fails

    return diff_sage, lt

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

def _dexpr(lhs, rhs=None):
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
            expr = RREF[row_idx, n_fvars]
            for free_col, free_var in enumerate(fvars):
                if free_col not in pivot_cols:
                    coeff = -RREF[row_idx, free_col]
                    if coeff != 0:
                        expr += coeff * free_var
            sol_dict[var] = expr
    lt += display_rref_matrix(RREF, fvars, pivot_cols, unit, precision)
    return RREF, lt, sol_dict

def display_rref_matrix(RREF, fvars, pivot_cols, unit=None, precision=None):
    n_fvars = len(fvars)
    lt = latex(RREF) + r"\Longrightarrow\begin{cases}"
    fvars_sorted = sorted(list(fvars), key=str)
    for var in fvars_sorted:
        orig_idx = list(fvars).index(var)
        if orig_idx in pivot_cols:
            row_idx = pivot_cols.index(orig_idx)
            rhs = RREF[row_idx, n_fvars]
            expr = rhs
            for col_idx, v in enumerate(fvars):
                if col_idx not in pivot_cols and col_idx != orig_idx:
                    coeff = -RREF[row_idx, col_idx]
                    if coeff != 0:
                        expr += coeff * v
            lt += latex(var) + r"="
            if precision is None:
                lt += latex(expr)
            elif not isinstance(unit, str):
                lt += num(expr, precision)
            else:
                lt += qty(expr, precision, unit)
        else:
            lt += latex(var) + r"\text{\:: variable libre}"
        lt += r"\\"
    lt += r"\end{cases}"
    return lt

def extract_equations_matrix_product(LHS, VAR, RHS):
    lhs = list(LHS * VAR)
    rhs = list(RHS)
    return [lhs, rhs]

def compute_parallel_resistance(resistors):
    R = var('R')
    expr = 1/R == 0
    for value in resistors:
        expr = expr.lhs() == expr.rhs() + 1/value

    return solve(expr, R)[0].rhs()

def extract_parameters_Y_s_p(V):
    t = var('t')
    resultats_Y = []
    resultats_s_p = []

    # On vérifie si V est une somme.
    # Si operator(V) est l'addition, on prend les opérandes, sinon on met V dans une liste.
    if hasattr(V, 'operator') and V.operator() is not None and "add" in str(V.operator()):
        termes = V.operands()
    else:
        termes = [V]

    for terme in termes:
        partie_exp = None

        # 1. On cherche si le terme contient une exponentielle
        # On regarde le terme lui-même et ses sous-parties
        if "exp" in str(terme.operator()):
            partie_exp = terme
        else:
            for op in terme.operands():
                if "exp" in str(op.operator()):
                    partie_exp = op
                    break

        # 2. Extraction des valeurs
        if partie_exp is not None:
            # s_p est l'argument de l'exp (1er opérande) divisé par t
            s_p = partie_exp.operands()[0] / t
            # Y est le terme total divisé par l'exponentielle
            Y = terme / partie_exp

            resultats_Y.append(Y)
            resultats_s_p.append(s_p)
        else:
            # Si aucune exp n'est trouvée (cas du 6 par exemple)
            resultats_Y.append(terme)
            resultats_s_p.append(0)

    return resultats_Y, resultats_s_p
\end{sagesilent}
