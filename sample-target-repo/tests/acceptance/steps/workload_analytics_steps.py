import time
from behave import when
from calculator import Calculator


@when("I raise {base:g} to the power of {exp:g}")
def step_raise_power(context, base, exp):
    if not hasattr(context, "calc"):
        context.calc = Calculator()
    print(f"[behave] Raising {base} to the power of {exp}", flush=True)
    time.sleep(0.12)
    context.result = context.calc.power(base, exp)


@when("I compute the modulo of {a:g} by {b:g}")
def step_compute_modulo(context, a, b):
    if not hasattr(context, "calc"):
        context.calc = Calculator()
    print(f"[behave] Computing {a} % {b}", flush=True)
    time.sleep(0.12)
    context.result = context.calc.modulo(a, b)


@when("I clamp the sensor reading {val:g} between {low:g} and {high:g}")
def step_clamp_reading(context, val, low, high):
    if not hasattr(context, "calc"):
        context.calc = Calculator()
    print(f"[behave] Clamping {val} into [{low}, {high}]", flush=True)
    time.sleep(0.12)
    context.result = context.calc.clamp(val, low, high)


@when("I compute the percentage of {part:g} out of {whole:g}")
def step_compute_percentage(context, part, whole):
    if not hasattr(context, "calc"):
        context.calc = Calculator()
    print(f"[behave] Computing percentage of {part} / {whole}", flush=True)
    time.sleep(0.12)
    context.result = context.calc.percentage(part, whole)
