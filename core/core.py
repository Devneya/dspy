import importlib
import sys
import uuid
import dspy
import config
from data.block_data import WrapperBlock
from data.table_data import table

program = None
lm = None


# fix this
def setup_lm():
    global lm
    lm = dspy.LM("ollama/llama3.2", api_base="http://localhost:11434")
    dspy.configure(lm=lm)


def get_program():
    global program
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


def build_reward_fn(block):
    code = block.reward_code
    if not code or not code.strip():
        return lambda inputs, prediction: 1.0
    filename = f"/tmp/dspy_reward_{uuid.uuid4().hex}.py"
    with open(filename, "w") as f:
        f.write("import dspy\n")
        f.write(code)
    try:
        spec = importlib.util.spec_from_file_location(
            f"reward_fn_{uuid.uuid4().hex}", filename
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        fn = getattr(module, "reward_fn", None)
        if fn:
            return fn
    except Exception as e:
        print(f"Error loading reward function: {e}", file=sys.stderr)
    return lambda inputs, prediction: 1.0


def build_module(block):
    signature = build_signature(block)
    if block.type == "chainofthought":
        return dspy.ChainOfThought(signature)
    elif block.type == "programofthought":
        return dspy.ProgramOfThought(signature)
    elif block.type == "multichaincomparison":
        return dspy.MultiChainComparison(signature)
    return dspy.Predict(signature)


def build_wrapper(block):
    wrapped_block = block.get_wrapped_block()
    base_module = build_module(wrapped_block)
    if block.type == "refine":
        return dspy.Refine(
            module=base_module,
            reward_fn=build_reward_fn(block),
            threshold=block.threshold,
            N=int(block.N),
        )
    else:
        return dspy.BestOfN(
            module=base_module,
            reward_fn=build_reward_fn(block),
            threshold=block.threshold,
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
    print(f"Trainset size: {len(trainset)}", file=sys.stderr)
    for t in trainset:
        print(f"  Example: {t}", file=sys.stderr)
    return trainset


def train(program, examples):
    optimizer = dspy.BootstrapFewShot()
    optimized = optimizer.compile(program, trainset=build_trainset(examples))
    return optimized


def run(program, **inputs):
    return program(**inputs)
