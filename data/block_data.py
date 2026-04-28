import config

# class BlockData:
#     def __init__(self, block_type, position):
#         self.id = f"b{config.block_id}"
#         self.type = block_type
#         self.position = position
#         self.label = config.MODULE_NAMES.get(block_type, block_type)
#         self.input_columns = self.get_default_input_columns(position)
#         self.output_columns = self.get_default_output_columns(position)
#         self.params = {}
#         config.block_id += 1

#     def get_default_input_columns(self, position):
#         if position == 0:
#             return ["input"]
#         prev_block = config.blocks[position - 1] if position > 0 else None
#         if prev_block and prev_block.output_columns:
#             return [prev_block.output_columns[0]]
#         return ["input"]

#     def get_default_output_columns(self, position):
#         return ["output"] if position == 0 else [f"output_{position+1}"]

#     def get_columns(self, table_type):
#         return self.input_columns if table_type == "inputs" else self.output_columns

#     def get_used_column_names(self, table_type=None):
#         used = set()
#         for b in config.blocks:
#             if b.position < self.position:
#                 used.update([c for c in b.input_columns if c and c.strip()])
#                 used.update([c for c in b.output_columns if c and c.strip()])
#         if table_type == "outputs":
#             used.update([c for c in self.input_columns if c and c.strip()])
#             used.update([c for c in self.output_columns if c and c.strip()])
#         return used

#     def delete_column(self, table_type, col_index):
#         columns = self.input_columns if table_type == "inputs" else self.output_columns
#         if col_index < len(columns):
#             return columns.pop(col_index)
#         return None


# def create_block(block_type, position):
#     return BlockData(block_type, position)


class BlockData:
    def __init__(self, block_type, position):
        self.id = f"b{config.block_id}"
        self.type = block_type
        self.position = position
        self.label = config.MODULE_NAMES.get(block_type, block_type)
        self.params = {}
        config.block_id += 1


class RegularBlock(BlockData):
    def __init__(self, block_type, position):
        super().__init__(block_type, position)
        self.input_columns = self.get_default_input_columns(position)
        self.output_columns = self.get_default_output_columns(position)

    def get_default_input_columns(self, position):
        if position == 0:
            return ["input"]
        for i in range(position - 1, -1, -1):
            prev = config.blocks[i]
            if isinstance(prev, RegularBlock) and prev.output_columns:
                return [prev.output_columns[0]]
        return ["input"]

    def get_default_output_columns(self, position):
        return ["output"] if position == 0 else [f"output_{position + 1}"]

    def get_columns(self, table_type):
        return self.input_columns if table_type == "inputs" else self.output_columns

    def get_used_column_names(self, table_type=None):
        used = set()
        for b in config.blocks:
            if b.position < self.position and isinstance(b, RegularBlock):
                used.update(c for c in b.input_columns if c and c.strip())
                used.update(c for c in b.output_columns if c and c.strip())
        if table_type == "outputs":
            used.update(c for c in self.input_columns if c and c.strip())
            used.update(c for c in self.output_columns if c and c.strip())
        return used

    def delete_column(self, table_type, col_index):
        columns = self.input_columns if table_type == "inputs" else self.output_columns
        if col_index < len(columns):
            return columns.pop(col_index)
        return None


class WrapperBlock(BlockData):
    def __init__(self, block_type, position):
        super().__init__(block_type, position)
        self.wrapped_block_id = config.blocks[position - 1].id if position > 0 else None
        self.N = 3
        self.reward_code = config.DSPY_MODULE_SCHEMAS.get(block_type, {}).get(
            "reward_code", ""
        )
        self.threshold = config.DSPY_MODULE_SCHEMAS.get(block_type, {}).get(
            "default_threshold", 0.5
        )
        self.fail_count = None

    def get_wrapped_block(self):
        if not self.wrapped_block_id:
            return None
        return next((b for b in config.blocks if b.id == self.wrapped_block_id), None)

    @property
    def effective_fail_count(self):
        return self.fail_count if self.fail_count is not None else self.N


def create_block(block_type, position):
    if block_type in config.WRAPPER_TYPES:
        return WrapperBlock(block_type, position)
    return RegularBlock(block_type, position)
