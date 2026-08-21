# services/tools/calculator.py
import math
import ast
import operator


SAFE_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

SAFE_FUNCS = {
    "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "abs": abs, "round": round, "pi": math.pi, "e": math.e,
}


def _eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.Name) and node.id in SAFE_FUNCS:
        return SAFE_FUNCS[node.id]
    elif isinstance(node, ast.BinOp) and type(node.op) in SAFE_OPS:
        return SAFE_OPS[type(node.op)](_eval(node.left), _eval(node.right))
    elif isinstance(node, ast.UnaryOp) and type(node.op) in SAFE_OPS:
        return SAFE_OPS[type(node.op)](_eval(node.operand))
    elif isinstance(node, ast.Call):
        func = _eval(node.func)
        args = [_eval(a) for a in node.args]
        return func(*args)
    else:
        raise ValueError(f"Ruxsat etilmagan ifoda: {type(node).__name__}")


def calculate(expression: str) -> str:
    """Xavfsiz matematik hisob-kitob."""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval(tree.body)
        return f"?? {expression} = **{result}**"
    except ZeroDivisionError:
        return "? Nolga bo'lish mumkin emas!"
    except Exception as e:
        return f"? Hisob xatosi: {e}"
