from data.block_data import RegularBlock


def normalize_key(key: str):
    return key.strip().lower().replace(" ", "_").replace("-", "_")


def normalize_row(row: dict):
    return {normalize_key(k): v for k, v in row.items()}


class TableData:
    def __init__(self):
        self.columns = set()
        self.rows = []
        self.next_id = 1

    def sync_columns_from_blocks(self, blocks):
        new_cols = {
            c
            for b in blocks
            if isinstance(b, RegularBlock)
            for c in (*b.input_columns, *b.output_columns)
            if c and c.strip()
        } or {"input", "output"}

        if self.columns != new_cols:
            for row in self.rows:
                for col in new_cols - set(row.keys()):
                    row[col] = ""
                for col in set(row.keys()) - new_cols - {"id"}:
                    del row[col]
            self.columns = new_cols

        return list(self.columns)

    def add_row(self):
        row = {"id": self.next_id}
        for col in self.columns:
            row[col] = ""
        self.rows.append(row)
        self.next_id += 1
        return self.rows

    def delete_row(self, row_id):
        self.rows = [r for r in self.rows if r["id"] != row_id]
        for i, row in enumerate(self.rows, 1):
            row["id"] = i
        self.next_id = len(self.rows) + 1
        return self.rows

    def clear_rows(self):
        self.rows = []
        self.next_id = 1
        return self.rows

    def update_cell(self, row_id, col_name, value):
        for row in self.rows:
            if row["id"] == row_id:
                row[col_name] = value
                return True
        return False


table = TableData()
inference_table = TableData()
