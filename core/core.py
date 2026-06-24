import ast
import json
import os
import subprocess
import sys
import tempfile
import dspy
import config
from data.block_data import WrapperBlock
from data.table_data import table

program = None
lm = None

FORBIDDEN_IMPORTS = {
    "os",
    "subprocess",
    "sys",
    "shutil",
    "socket",
    "requests",
    "http",
    "urllib",
    "ftplib",
    "telnetlib",
    "smtplib",
    "imaplib",
    "pathlib",
    "glob",
    "fnmatch",
    "pickle",
    "marshal",
    "ctypes",
    "multiprocessing",
    "threading",
    "signal",
    "pty",
    "tty",
    "cgi",
    "cgitb",
    "webbrowser",
}

FORBIDDEN_CALLS = {
    "open",
    "exec",
    "eval",
    "compile",
    "__import__",
    "globals",
    "locals",
    "getattr",
    "setattr",
    "delattr",
    "breakpoint",
    "input",
}

FORBIDDEN_ATTRS = {
    "__builtins__",
    "__class__",
    "__bases__",
    "__subclasses__",
    "__globals__",
    "__code__",
    "__closure__",
}


class SafePythonInterpreter(dspy.PythonInterpreter):
    def execute(self, code: str) -> str:
        try:
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "--memory",
                    "128m",
                    "--cpus",
                    "1",
                    "--read-only",
                    "--tmpfs",
                    "/tmp:noexec",
                    "python:3.12-alpine",
                    "python",
                    "-c",
                    code,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                return f"Error: {result.stderr}"
            return result.stdout
        except subprocess.TimeoutExpired:
            return "Error: execution timed out"
        except Exception as e:
            return f"Error: {e}"


def validate_reward_code(code: str):
    if not code or not code.strip():
        return False, "Code is empty"
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_IMPORTS:
                    return False, f"Import not allowed: {alias.name}"
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in FORBIDDEN_IMPORTS:
                return False, f"Import not allowed: {node.module}"
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                return False, f"Call not allowed: {node.func.id}()"
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in FORBIDDEN_CALLS
            ):
                return False, f"Call not allowed: .{node.func.attr}()"

        if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_ATTRS:
            return False, f"Attribute access not allowed: .{node.attr}"

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "getattr" and len(node.args) >= 2:
                if isinstance(node.args[1], ast.Constant):
                    if node.args[1].value in FORBIDDEN_ATTRS:
                        return False, f"getattr bypass blocked: {node.args[1].value}"

    return True, "OK"


def setup_lm():
    global lm
    model = config.lm_model
    
    if model.startswith("openai"):
        lm = dspy.LM(model, api_key=config.OPENAI_API_KEY)
    elif model.startswith("deepseek"):
        lm = dspy.LM(model, api_key=config.DEEPSEEK_API_KEY)
    # elif model.startswith("anthropic"):
    #     lm = dspy.LM(model, api_key=config.ANTHROPIC_API_KEY)
    # elif model.startswith("gemini"):
    #     lm = dspy.LM(model, api_key=config.GOOGLE_API_KEY)
    elif model.startswith("ollama"):
        lm = dspy.LM(model, api_base="http://localhost:11434")
    else:
        lm = dspy.LM(model)

    dspy.configure(lm=lm)


def get_program():
    global program, lm
    if lm is None:
        setup_lm()
    if program is None:
        program = build_program()
    return program


def optimize():
    global program, lm
    if lm is None:
        setup_lm()
    program = build_program()
    program = train(program, table.rows)
    return program


def build_signature(block):
    fields = {}
    for col in block.input_columns:
        fields[col] = dspy.InputField()
    for col in block.output_columns:
        fields[col] = dspy.OutputField()
    return type(f"{block.type}_signature", (dspy.Signature,), fields)


def build_reward_fn_docker(block):
    code = block.reward_code
    if not code or not code.strip():
        return lambda inputs, prediction: 1.0

    ok, err = validate_reward_code(code)
    if not ok:
        print(f"Reward code rejected: {err}", file=sys.stderr)
        return lambda inputs, prediction: 1.0

    tmpdir = tempfile.mkdtemp()
    codepath = os.path.join(tmpdir, "reward_fn.py")
    with open(codepath, "w") as f:
        f.write(code)

    def docker_reward(inputs, prediction):
        try:
            pred_dict = {
                k: v for k, v in prediction.__dict__.items() if not k.startswith("_")
            }
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "--memory",
                    "64m",
                    "--cpus",
                    "1",
                    "--read-only",
                    "--tmpfs",
                    "/tmp:noexec",
                    "-v",
                    f"{tmpdir}:/code:ro",
                    "python:3.12-alpine",
                    "python",
                    "-c",
                    f"""
import sys
sys.path.insert(0, '/code')
from reward_fn import reward_fn
import json

inputs = json.loads({json.dumps(inputs)!r})
prediction_dict = json.loads({json.dumps(pred_dict)!r})

class MockPrediction:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

prediction = MockPrediction(**prediction_dict)
result = reward_fn(inputs, prediction)
print(json.dumps(float(result)))
""",
                ],
                capture_output=True,
                text=True,
                timeout=100,
            )
            return max(0.0, min(1.0, float(result.stdout.strip())))
        except Exception as e:
            print(f"Docker reward error: {e}", file=sys.stderr)
            return 0.0

    return docker_reward


def build_module(block):
    signature = build_signature(block)
    if block.type == "chainofthought":
        return dspy.ChainOfThought(signature)
    elif block.type == "programofthought":
        return dspy.ProgramOfThought(signature, interpreter=SafePythonInterpreter())
    elif block.type == "multichaincomparison":
        return dspy.MultiChainComparison(signature)
    return dspy.Predict(signature)


def build_wrapper(block):
    wrapped_block = block.get_wrapped_block()
    base_module = build_module(wrapped_block)
    if block.type == "refine":
        return dspy.Refine(
            module=base_module,
            reward_fn=build_reward_fn_docker(block),
            threshold=float(block.threshold),
            N=int(block.N),
        )
    else:
        return dspy.BestOfN(
            module=base_module,
            reward_fn=build_reward_fn_docker(block),
            threshold=float(block.threshold),
            N=int(block.N),
        )


def is_wrapped(block):
    return any(
        isinstance(b, WrapperBlock) and b.wrapped_block_id == block.id
        for b in config.blocks
    )


def build_program():
    class Pipeline(dspy.Module):
        def __init__(self):
            super().__init__()
            self.steps = []

            for block in config.blocks:
                if isinstance(block, WrapperBlock):
                    module = build_wrapper(block)
                elif not is_wrapped(block):
                    module = build_module(block)
                else:
                    continue
                self.steps.append(module)

        def forward(self, **inputs):
            result = dict(inputs)

            for module in self.steps:
                output = module(**result)
                result.update(output)

            return dspy.Prediction(**result)

    return Pipeline()


def build_trainset(examples):
    all_outputs = set()
    for block in config.blocks:
        if hasattr(block, "output_columns"):
            all_outputs.update(block.output_columns)
    trainset = []
    for row in examples:
        example_data = {k: v for k, v in row.items() if k != "id"}
        if not example_data:
            continue
        inputs = {k: v for k, v in example_data.items() if k not in all_outputs}
        if inputs:
            trainset.append(dspy.Example(**example_data).with_inputs(*inputs.keys()))
    return trainset


def train(program, examples):
    optimizer = dspy.BootstrapFewShot()
    optimized = optimizer.compile(program, trainset=build_trainset(examples))
    return optimized


def run(program, **inputs):
    return program(**inputs)
