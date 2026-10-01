import ast
import operator
import math
import sys

# Разрешенные математические операторы
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Разрешенные функции и константы
FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "abs": abs,
    "round": round,
    "log": math.log,
}

CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


def safe_eval(node):
    """Рекурсивный безопасный парсинг абстрактного синтаксического дерева (AST)."""
    if isinstance(node, ast.Expression):
        return safe_eval(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Неподдерживаемое значение: {node.value}")

    # Имена переменных (константы pi, e)
    if isinstance(node, ast.Name):
        if node.id in CONSTANTS:
            return CONSTANTS[node.id]
        raise ValueError(f"Неизвестная константа: {node.id}")

    # Бинарные операции (+, -, *, /, **, %)
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in OPERATORS:
            left = safe_eval(node.left)
            right = safe_eval(node.right)
            if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                raise ZeroDivisionError("Деление на ноль")
            return OPERATORS[op_type](left, right)
        raise ValueError(f"Неподдерживаемый оператор: {op_type.__name__}")

    # Унарные операции (-x, +x)
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in OPERATORS:
            operand = safe_eval(node.operand)
            return OPERATORS[op_type](operand)
        raise ValueError(f"Неподдерживаемый оператор: {op_type.__name__}")

    # Вызовы функций: sqrt(16), abs(-5)
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in FUNCTIONS:
            fn = FUNCTIONS[node.func.id]
            args = [safe_eval(arg) for arg in node.args]
            return fn(*args)
        raise ValueError(f"Неизвестная функция: {getattr(node.func, 'id', 'unknown')}")

    raise ValueError(f"Неподдерживаемое выражение: {type(node).__name__}")


def calculate(expr: str):
    """Вычисляет результат выражения, переданного в виде строки."""
    expr = expr.strip()
    if not expr:
        return None
    tree = ast.parse(expr, mode="eval")
    return safe_eval(tree)


def main():
    print("=" * 40)
    print("        Консольный Калькулятор          ")
    print("=" * 40)
    print("Поддерживает: +, -, *, /, //, %, **")
    print("Функции: sqrt(x), sin(x), cos(x), abs(x)")
    print("Константы: pi, e")
    print("Для выхода введите: exit или quit\n")

    while True:
        try:
            expression = input("calc > ").strip()
            if not expression:
                continue

            if expression.lower() in ("exit", "quit", "q"):
                print("До свидания!")
                break

            result = calculate(expression)
            if result is not None:
                # Если число целое (например, 4.0), выводим как 4
                if isinstance(result, float) and result.is_integer():
                    result = int(result)
                print(f"= {result}\n")

        except ZeroDivisionError:
            print("Ошибка: деление на ноль!\n")
        except (ValueError, SyntaxError) as e:
            print(f"Ошибка в выражении: {e}\n")
        except KeyboardInterrupt:
            print("\nВыход.")
            break
        except Exception as e:
            print(f"Непредвиденная ошибка: {e}\n")


if __name__ == "__main__":
    main()