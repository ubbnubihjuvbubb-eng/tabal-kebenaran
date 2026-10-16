import tkinter as tk
from tkinter import ttk, messagebox
import itertools
import re

# ============================================================
# PJBL-1: SIMULATOR TABEL KEBENARAN
# Fitur:
# 1. Input ekspresi logika
# 2. Tokenisasi
# 3. Parsing dengan recursive descent
# 4. Deteksi variabel otomatis
# 5. Pembangkitan kombinasi T/F
# 6. Evaluasi ekspresi
# 7. Tampilan tabel kebenaran
#
# Operator yang didukung:
# AND : AND, and, &, ∧
# OR  : OR, or, |, ∨
# NOT : NOT, not, !, ¬
# XOR : XOR, xor, ⊕
# IMPLIKASI : ->, =>, →
# BIKONDISIONAL : <->, <=>, ↔
# Konstanta: T/TRUE dan F/FALSE
# ============================================================


# -------------------- TOKENIZER --------------------

TOKEN_RE = re.compile(
    r"""
    \s*
    (
        <->|<=>|->|=>|→|↔|
        \(|\)|
        ∧|∨|¬|!|&|\||⊕|
        \bAND\b|\bOR\b|\bNOT\b|\bXOR\b|
        \bTRUE\b|\bFALSE\b|\bT\b|\bF\b|
        [A-Za-z_][A-Za-z0-9_]*
    )
    """,
    re.IGNORECASE | re.VERBOSE
)


def tokenize(text):
    """Mengubah ekspresi menjadi daftar token."""
    tokens = []
    pos = 0

    while pos < len(text):
        match = TOKEN_RE.match(text, pos)

        if not match:
            # Izinkan spasi di akhir
            if text[pos:].strip() == "":
                break
            raise ValueError(
                f"Karakter/operator tidak dikenali di posisi {pos + 1}: "
                f"'{text[pos]}'"
            )

        tokens.append(match.group(1))
        pos = match.end()

    tokens.append("EOF")
    return tokens


# -------------------- PARSER --------------------

class Parser:
    """
    Grammar:
        expression  := implication
        implication := equivalence [IMPL implication]
        equivalence := or_expr { EQUIV or_expr }
        or_expr     := xor_expr { OR xor_expr }
        xor_expr    := and_expr { XOR and_expr }
        and_expr    := unary { AND unary }
        unary       := NOT unary | primary
        primary     := VARIABLE | CONSTANT | '(' expression ')'
    """

    def __init__(self, tokens):
        self.tokens = tokens
        self.index = 0
        self.variables = set()

    def current(self):
        return self.tokens[self.index]

    def advance(self):
        token = self.current()
        self.index += 1
        return token

    def accept(self, *values):
        current = self.current().upper()
        for value in values:
            if current == value:
                self.advance()
                return True
        return False

    def expect(self, *values):
        if not self.accept(*values):
            expected = " / ".join(values)
            raise ValueError(
                f"Token '{self.current()}' tidak sesuai. "
                f"Diharapkan: {expected}"
            )

    def parse(self):
        node = self.parse_implication()

        if self.current() != "EOF":
            raise ValueError(
                f"Token berlebih atau sintaks tidak valid: '{self.current()}'"
            )

        return node

    def parse_implication(self):
        left = self.parse_equivalence()

        if self.accept("->", "=>", "→"):
            right = self.parse_implication()
            return ("IMPLIES", left, right)

        return left

    def parse_equivalence(self):
        node = self.parse_or()

        while self.accept("<->", "<=>", "↔"):
            right = self.parse_or()
            node = ("EQUIV", node, right)

        return node

    def parse_or(self):
        node = self.parse_xor()

        while self.accept("OR", "∨", "|"):
            right = self.parse_xor()
            node = ("OR", node, right)

        return node

    def parse_xor(self):
        node = self.parse_and()

        while self.accept("XOR", "⊕"):
            right = self.parse_and()
            node = ("XOR", node, right)

        return node

    def parse_and(self):
        node = self.parse_unary()

        while self.accept("AND", "∧", "&"):
            right = self.parse_unary()
            node = ("AND", node, right)

        return node

    def parse_unary(self):
        if self.accept("NOT", "¬", "!"):
            return ("NOT", self.parse_unary())

        return self.parse_primary()

    def parse_primary(self):
        token = self.current()

        if token == "(":
            self.advance()
            node = self.parse_implication()
            self.expect(")")
            return node

        upper = token.upper()

        if upper in ("TRUE", "T"):
            self.advance()
            return ("CONST", True)

        if upper in ("FALSE", "F"):
            self.advance()
            return ("CONST", False)

        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token):
            self.advance()
            self.variables.add(token)
            return ("VAR", token)

        raise ValueError(f"Token '{token}' tidak dapat digunakan di posisi ini.")


# -------------------- EVALUATOR --------------------

def evaluate(node, values):
    kind = node[0]

    if kind == "CONST":
        return node[1]

    if kind == "VAR":
        return values[node[1]]

    if kind == "NOT":
        return not evaluate(node[1], values)

    left = evaluate(node[1], values)
    right = evaluate(node[2], values)

    if kind == "AND":
        return left and right

    if kind == "OR":
        return left or right

    if kind == "XOR":
        return left != right

    if kind == "IMPLIES":
        return (not left) or right

    if kind == "EQUIV":
        return left == right

    raise ValueError(f"Operator tidak dikenal: {kind}")


# -------------------- FORMAT AST --------------------

def ast_to_text(node):
    """Menampilkan hasil parsing sebagai struktur sederhana."""
    kind = node[0]

    if kind == "VAR":
        return node[1]
    if kind == "CONST":
        return "TRUE" if node[1] else "FALSE"
    if kind == "NOT":
        return f"(NOT {ast_to_text(node[1])})"

    names = {
        "AND": "AND",
        "OR": "OR",
        "XOR": "XOR",
        "IMPLIES": "->",
        "EQUIV": "<->"
    }

    return (
        f"({ast_to_text(node[1])} "
        f"{names[kind]} "
        f"{ast_to_text(node[2])})"
    )


# -------------------- APLIKASI GUI --------------------

class TruthTableApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PJBL-1 - Simulator Tabel Kebenaran")
        self.root.geometry("1050x700")
        self.root.minsize(850, 600)

        self.setup_style()
        self.build_ui()

    def setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))

    def build_ui(self):
        main = ttk.Frame(self.root, padding=20)
        main.pack(fill="both", expand=True)

        title = ttk.Label(
            main,
            text="Simulator Tabel Kebenaran",
            style="Title.TLabel"
        )
        title.pack(anchor="w")

        subtitle = ttk.Label(
            main,
            text="PJBL-1 Sesi Ke-2 | Parser • Deteksi Variabel • Generator T/F",
            style="Subtitle.TLabel"
        )
        subtitle.pack(anchor="w", pady=(0, 18))

        input_frame = ttk.LabelFrame(
            main,
            text=" 1. Masukkan Ekspresi Logika ",
            padding=15
        )
        input_frame.pack(fill="x")

        self.expression_var = tk.StringVar(
            value="(p AND q) OR NOT r"
        )

        self.entry = ttk.Entry(
            input_frame,
            textvariable=self.expression_var,
            font=("Consolas", 13)
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry.bind("<Return>", lambda event: self.generate_table())

        ttk.Button(
            input_frame,
            text="Generate Tabel",
            command=self.generate_table
        ).pack(side="left")

        examples = ttk.Label(
            main,
            text=(
                "Contoh: p AND q    |    (p OR q) AND NOT r    |    "
                "p -> q    |    p <-> q    |    p XOR q"
            )
        )
        examples.pack(anchor="w", pady=(8, 15))

        info_frame = ttk.Frame(main)
        info_frame.pack(fill="x", pady=(0, 12))

        self.variable_label = ttk.Label(
            info_frame,
            text="Variabel: -",
            style="Header.TLabel"
        )
        self.variable_label.pack(side="left")

        self.combination_label = ttk.Label(
            info_frame,
            text="Jumlah kombinasi: -",
            style="Header.TLabel"
        )
        self.combination_label.pack(side="right")

        table_frame = ttk.LabelFrame(
            main,
            text=" 2. Tabel Kebenaran ",
            padding=10
        )
        table_frame.pack(fill="both", expand=True)

        # Scrollbar vertikal
        y_scroll = ttk.Scrollbar(
            table_frame,
            orient="vertical"
        )
        y_scroll.pack(side="right", fill="y")

        # Scrollbar horizontal
        x_scroll = ttk.Scrollbar(
            table_frame,
            orient="horizontal"
        )
        x_scroll.pack(side="bottom", fill="x")

        self.tree = ttk.Treeview(
            table_frame,
            show="headings",
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set
        )
        self.tree.pack(fill="both", expand=True)

        y_scroll.config(command=self.tree.yview)
        x_scroll.config(command=self.tree.xview)

        bottom = ttk.LabelFrame(
            main,
            text=" 3. Informasi Parsing ",
            padding=10
        )
        bottom.pack(fill="x", pady=(12, 0))

        self.token_label = ttk.Label(
            bottom,
            text="Token: -",
            wraplength=950
        )
        self.token_label.pack(anchor="w")

        self.ast_label = ttk.Label(
            bottom,
            text="Hasil parsing: -",
            wraplength=950
        )
        self.ast_label.pack(anchor="w", pady=(5, 0))

        self.entry.focus()

    def clear_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def generate_table(self):
        expression = self.expression_var.get().strip()

        if not expression:
            messagebox.showwarning(
                "Input kosong",
                "Masukkan ekspresi logika terlebih dahulu."
            )
            return

        try:
            # 1. Tokenisasi
            tokens = tokenize(expression)

            # 2. Parsing
            parser = Parser(tokens)
            tree = parser.parse()

            # 3. Deteksi variabel
            variables = sorted(parser.variables, key=str.lower)

            # 4. Bersihkan tabel lama
            self.clear_table()

            # Kolom tabel
            columns = variables + ["Hasil"]
            self.tree["columns"] = columns

            for col in columns:
                self.tree.heading(
                    col,
                    text=col if col != "Hasil" else expression
                )
                self.tree.column(
                    col,
                    width=110,
                    minwidth=80,
                    anchor="center"
                )

            # 5. Bangkitkan semua kombinasi T/F
            combinations = itertools.product([True, False], repeat=len(variables))

            count = 0

            for combo in combinations:
                values = dict(zip(variables, combo))
                result = evaluate(tree, values)

                row = [
                    "T" if values[var] else "F"
                    for var in variables
                ]
                row.append("T" if result else "F")

                self.tree.insert("", "end", values=row)
                count += 1

            # 6. Informasi
            self.variable_label.config(
                text=(
                    "Variabel: "
                    + (", ".join(variables) if variables else "tidak ada")
                )
            )

            self.combination_label.config(
                text=f"Jumlah kombinasi: {count}"
            )

            # Hilangkan EOF dari tampilan token
            shown_tokens = [t for t in tokens if t != "EOF"]

            self.token_label.config(
                text="Token: " + " | ".join(shown_tokens)
            )

            self.ast_label.config(
                text="Hasil parsing: " + ast_to_text(tree)
            )

        except Exception as error:
            self.clear_table()
            self.variable_label.config(text="Variabel: -")
            self.combination_label.config(text="Jumlah kombinasi: -")
            self.token_label.config(text="Token: -")
            self.ast_label.config(text="Hasil parsing: -")

            messagebox.showerror(
                "Ekspresi tidak valid",
                str(error)
            )


# -------------------- MAIN --------------------

if __name__ == "__main__":
    root = tk.Tk()
    app = TruthTableApp(root)
    root.mainloop()
