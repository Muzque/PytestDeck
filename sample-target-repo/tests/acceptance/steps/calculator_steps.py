from behave import given, when, then
from calculator import Calculator

@given('I have a calculator')
def step_given_calculator(context):
    print("\n[acceptance] Given: Initializing Calculator")
    context.calc = Calculator()

@when('I add {a:d} and {b:d}')
def step_when_add(context, a, b):
    context.result = context.calc.add(a, b)
    print(f"[acceptance] When: Added {a} + {b} = {context.result}")

@when('I divide {a:d} by {b:d}')
def step_when_divide(context, a, b):
    context.result = context.calc.divide(a, b)
    print(f"[acceptance] When: Divided {a} / {b} = {context.result}")

@then('the result should be {expected:d}')
def step_then_result(context, expected):
    print(f"[acceptance] Then: Verifying result == {expected} (actual: {context.result})")
    assert context.result == expected, f"Expected {expected}, got {context.result}"
