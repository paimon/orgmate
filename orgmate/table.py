from dataclasses import dataclass

@dataclass
class Column:
    width: int = 0
    align: str = '<'

    def get_template(self):
        return '{:' + f'{self.align}{self.width}' + '}'


class Table:
    def __init__(self, col_count):
        self.cols = [Column() for _ in range(col_count)]
        self.rows = []

    def add_row(self, *row):
        row = [str(field) for field in row]
        for field, col in zip(row, self.cols):
            col.width = max(col.width, len(field))
        self.rows.append(row)

    def print(self):
        template = ' '.join(col.get_template() for col in self.cols)
        for row in self.rows:
            print(template.format(*row))
        self.rows.clear()
