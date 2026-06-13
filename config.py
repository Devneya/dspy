import os
import yaml

SCHEMA_PATH = os.path.join("static", "dspy_schemas.yaml")
with open(SCHEMA_PATH, "r") as f:
    DSPY_MODULE_SCHEMAS = yaml.safe_load(f)

BLOCK_TYPES = list(DSPY_MODULE_SCHEMAS.keys())
WRAPPER_TYPES = {
    block_type
    for block_type, schema in DSPY_MODULE_SCHEMAS.items()
    if schema.get("wrapper", 0) == 1
}

MODULE_NAMES = {
    block_type: schema["name"] for block_type, schema in DSPY_MODULE_SCHEMAS.items()
}

init_predict = False
blocks = []
block_id = 1
active_block_id = None
is_optimized = False
current_mode = "build"

def mark_unoptimized():
    global is_optimized
    is_optimized = False