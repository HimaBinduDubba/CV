from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import BooleanVar, IntVar, StringVar, Tk, filedialog, messagebox
from tkinter import ttk


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "Data"
DEFAULT_CONFIG = PROJECT_ROOT / "config.local.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "full_extraction" / "extraction_results_gemini.json"
DEFAULT_STACKUP = PROJECT_ROOT / "results" / "stackup" / "stackup_relevant_dimensions.json"


class ExtractionGUI:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("Engineering Drawing Dimension Extractor")
        self.root.geometry("1180x760")
        self.root.minsize(980, 620)

        self.data_dir = StringVar(value=str(DEFAULT_DATA_DIR))
        self.config_file = StringVar(value=str(DEFAULT_CONFIG))
        self.output_file = StringVar(value=str(DEFAULT_OUTPUT))
        self.stackup_file = StringVar(value=str(DEFAULT_STACKUP))
        self.dpi = IntVar(value=150)
        self.workers = IntVar(value=4)
        self.auto_refresh = BooleanVar(value=True)
        self.status = StringVar(value="Ready")

        self.process: subprocess.Popen[str] | None = None
        self.output_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.last_loaded_output: Path | None = None

        self._build_style()
        self._build_layout()
        self._set_running(False)
        self._load_stackup_if_present()
        self._load_results_if_present(silent=True)
        self._poll_output_queue()

    def _build_style(self) -> None:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TFrame", background="#f6f7f9")
        style.configure("Header.TFrame", background="#27313f")
        style.configure("Header.TLabel", background="#27313f", foreground="#ffffff", font=("Segoe UI", 15, "bold"))
        style.configure("Subheader.TLabel", background="#27313f", foreground="#d7dee8", font=("Segoe UI", 9))
        style.configure("Card.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("TLabel", background="#f6f7f9", foreground="#18202a", font=("Segoe UI", 9))
        style.configure("Card.TLabel", background="#ffffff", foreground="#18202a", font=("Segoe UI", 9))
        style.configure("Metric.TLabel", background="#ffffff", foreground="#18202a", font=("Segoe UI", 18, "bold"))
        style.configure("MetricCaption.TLabel", background="#ffffff", foreground="#596574", font=("Segoe UI", 8))
        style.configure("Accent.TButton", font=("Segoe UI", 9, "bold"))
        style.configure("Treeview", rowheight=26, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, style="Header.TFrame", padding=(18, 14))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Engineering Drawing Dimension Extractor", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Review bolt protrusion tolerance stack-up, source dimensions, worst-case limits, and open engineering actions.",
            style="Subheader.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        main = ttk.PanedWindow(self.root, orient="horizontal")
        main.grid(row=1, column=0, sticky="nsew")

        left = ttk.Frame(main, padding=14)
        right = ttk.Frame(main, padding=(0, 14, 14, 14))
        main.add(left, weight=0)
        main.add(right, weight=1)

        self._build_controls(left)
        self._build_results(right)

        footer = ttk.Frame(self.root, padding=(12, 8))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status).grid(row=0, column=0, sticky="w")

    def _build_controls(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)

        inputs = ttk.Frame(parent, style="Card.TFrame", padding=12)
        inputs.grid(row=0, column=0, sticky="ew")
        inputs.columnconfigure(1, weight=1)

        self._path_row(inputs, 0, "Stack-up JSON", self.stackup_file, self._choose_stackup_file)
        ttk.Button(inputs, text="Load Stack-Up", command=self._load_stackup_from_file).grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8, 10))
        ttk.Separator(inputs).grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        self._path_row(inputs, 3, "Data folder", self.data_dir, self._choose_data_dir)
        self._path_row(inputs, 4, "Config JSON", self.config_file, self._choose_config_file)
        self._path_row(inputs, 5, "Output JSON", self.output_file, self._choose_output_file)

        ttk.Label(inputs, text="DPI", style="Card.TLabel").grid(row=6, column=0, sticky="w", pady=(10, 0))
        ttk.Spinbox(inputs, from_=72, to=400, increment=25, textvariable=self.dpi, width=8).grid(row=6, column=1, sticky="w", pady=(10, 0))
        ttk.Label(inputs, text="Workers", style="Card.TLabel").grid(row=7, column=0, sticky="w", pady=(8, 0))
        ttk.Spinbox(inputs, from_=1, to=12, increment=1, textvariable=self.workers, width=8).grid(row=7, column=1, sticky="w", pady=(8, 0))
        ttk.Checkbutton(inputs, text="Refresh tables while extraction runs", variable=self.auto_refresh).grid(
            row=8, column=0, columnspan=3, sticky="w", pady=(10, 0)
        )

        actions = ttk.Frame(parent, padding=(0, 12, 0, 0))
        actions.grid(row=1, column=0, sticky="ew")
        actions.columnconfigure((0, 1), weight=1)
        self.start_button = ttk.Button(actions, text="Start Extraction", style="Accent.TButton", command=self._start_extraction)
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.stop_button = ttk.Button(actions, text="Stop", command=self._stop_extraction)
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ttk.Button(actions, text="Load Results", command=self._load_results_from_output).grid(row=1, column=0, sticky="ew", pady=(8, 0), padx=(0, 6))
        ttk.Button(actions, text="Open Output Folder", command=self._open_output_folder).grid(row=1, column=1, sticky="ew", pady=(8, 0), padx=(6, 0))

        metrics = ttk.Frame(parent, style="Card.TFrame", padding=12)
        metrics.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        metrics.columnconfigure((0, 1), weight=1)
        self.metric_nominal = self._metric(metrics, 0, 0, "--", "Known nominal")
        self.metric_range = self._metric(metrics, 0, 1, "--", "Worst case")
        self.metric_confirm = self._metric(metrics, 1, 0, "0", "Open actions")
        self.metric_ppt = self._metric(metrics, 1, 1, "--", "PPT nominal")

        log_frame = ttk.Frame(parent, style="Card.TFrame", padding=12)
        log_frame.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        parent.rowconfigure(3, weight=1)
        log_frame.rowconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)
        ttk.Label(log_frame, text="Run Log", style="Card.TLabel", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.log = self._text_widget(log_frame, height=16)
        self.log.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

    def _build_results(self, parent: ttk.Frame) -> None:
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        self.tabs = ttk.Notebook(parent)
        self.tabs.grid(row=0, column=0, sticky="nsew")

        self.summary_frame = ttk.Frame(self.tabs, padding=12)
        self.summary_frame.columnconfigure(0, weight=1)
        self.summary_frame.columnconfigure(1, weight=1)
        self.summary_frame.rowconfigure(2, weight=1)
        self.tabs.add(self.summary_frame, text="Stack-Up Summary")

        self.stack_title = StringVar(value="Bolt protrusion tolerance stack-up")
        self.stack_formula = StringVar(value="Load the stack-up JSON to review the analysis.")
        self.stack_caution = StringVar(value="")
        ttk.Label(self.summary_frame, textvariable=self.stack_title, font=("Segoe UI", 15, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(self.summary_frame, textvariable=self.stack_formula, font=("Segoe UI", 10)).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 12))

        calc_card = ttk.Frame(self.summary_frame, style="Card.TFrame", padding=12)
        calc_card.grid(row=2, column=0, sticky="nsew", padx=(0, 8))
        calc_card.columnconfigure(1, weight=1)
        ttk.Label(calc_card, text="Calculation Snapshot", style="Card.TLabel", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        self.calc_rows: dict[str, StringVar] = {}
        for index, label in enumerate(("Known contributors nominal", "Known worst-case minimum", "Known worst-case maximum", "PPT reference nominal", "PPT shown stack thickness"), start=1):
            ttk.Label(calc_card, text=label, style="Card.TLabel").grid(row=index, column=0, sticky="w", pady=(9, 0))
            var = StringVar(value="--")
            self.calc_rows[label] = var
            ttk.Label(calc_card, textvariable=var, style="Card.TLabel", font=("Segoe UI", 10, "bold")).grid(row=index, column=1, sticky="e", pady=(9, 0))

        action_card = ttk.Frame(self.summary_frame, style="Card.TFrame", padding=12)
        action_card.grid(row=2, column=1, sticky="nsew", padx=(8, 0))
        action_card.rowconfigure(1, weight=1)
        action_card.columnconfigure(0, weight=1)
        ttk.Label(action_card, text="Engineering Caution", style="Card.TLabel", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w")
        self.caution_text = self._plain_text_widget(action_card, height=9)
        self.caution_text.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        self.contributors_tree = self._tree_tab(
            "Stack Contributors",
            ("no", "part", "dimension", "nominal", "tol_plus", "tol_minus", "signed_nominal", "worst_min", "worst_max", "status", "use"),
            (50, 150, 250, 80, 80, 80, 110, 90, 90, 150, 190),
        )
        self.references_tree = self._tree_tab(
            "Reference Values",
            ("name", "value", "plus", "minus", "unit", "source"),
            (250, 90, 70, 70, 60, 240),
        )
        self.relationships_tree = self._tree_tab(
            "Assembly Model",
            ("from", "to", "relationship", "surface_1", "surface_2", "confidence"),
            (140, 140, 120, 260, 260, 90),
        )
        self.actions_tree = self._tree_tab(
            "Open Actions",
            ("no", "part", "item", "status", "needed_before_final", "reason"),
            (50, 150, 260, 190, 190, 280),
        )
        self.parts_tree = self._tree_tab(
            "Extraction Parts",
            ("source_file", "part_id", "dimensions", "gdt", "datums", "materials", "confidence", "valid"),
            (220, 120, 90, 70, 70, 80, 90, 70),
        )
        self.dimensions_tree = self._tree_tab(
            "All Extracted Dimensions",
            ("source_file", "part_id", "id", "nominal", "unit", "feature", "tolerance", "confidence", "page", "review"),
            (180, 110, 70, 90, 60, 260, 140, 90, 60, 80),
        )
        self.errors_tree = self._tree_tab("Errors", ("location", "message"), (260, 640))
        self.chains_tree = self._tree_tab(
            "Chains",
            ("chain_id", "target", "nominal", "worst_min", "worst_max", "confidence", "links"),
            (180, 190, 90, 90, 90, 90, 280),
        )

    def _path_row(self, parent: ttk.Frame, row: int, label: str, variable: StringVar, command: object) -> None:
        ttk.Label(parent, text=label, style="Card.TLabel").grid(row=row, column=0, sticky="w", pady=(0 if row == 0 else 8, 0))
        ttk.Entry(parent, textvariable=variable, width=44).grid(row=row, column=1, sticky="ew", padx=(10, 6), pady=(0 if row == 0 else 8, 0))
        ttk.Button(parent, text="Browse", command=command).grid(row=row, column=2, sticky="e", pady=(0 if row == 0 else 8, 0))

    def _metric(self, parent: ttk.Frame, row: int, col: int, value: str, caption: str) -> StringVar:
        holder = ttk.Frame(parent, style="Card.TFrame", padding=(8, 6))
        holder.grid(row=row, column=col, sticky="ew", padx=(0 if col == 0 else 8, 8 if col == 0 else 0), pady=(0 if row == 0 else 8, 0))
        metric_value = StringVar(value=value)
        ttk.Label(holder, textvariable=metric_value, style="Metric.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(holder, text=caption, style="MetricCaption.TLabel").grid(row=1, column=0, sticky="w")
        return metric_value

    def _tree_tab(self, title: str, columns: tuple[str, ...], widths: tuple[int, ...]) -> ttk.Treeview:
        frame = ttk.Frame(self.tabs, padding=8)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        for column, width in zip(columns, widths, strict=True):
            tree.heading(column, text=column.replace("_", " ").title())
            tree.column(column, width=width, minwidth=50, stretch=True)
        self.tabs.add(frame, text=title)
        return tree

    def _text_widget(self, parent: ttk.Frame, height: int):
        from tkinter import Text

        text = Text(parent, height=height, wrap="word", relief="flat", padx=8, pady=8, font=("Consolas", 9))
        text.configure(bg="#101820", fg="#e9eef5", insertbackground="#e9eef5", state="disabled")
        return text

    def _choose_data_dir(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.data_dir.get() or str(PROJECT_ROOT))
        if selected:
            self.data_dir.set(selected)

    def _choose_config_file(self) -> None:
        selected = filedialog.askopenfilename(
            initialdir=str(PROJECT_ROOT),
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if selected:
            self.config_file.set(selected)

    def _choose_output_file(self) -> None:
        selected = filedialog.asksaveasfilename(
            initialdir=str(DEFAULT_OUTPUT.parent),
            defaultextension=".json",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if selected:
            self.output_file.set(selected)

    def _choose_stackup_file(self) -> None:
        selected = filedialog.askopenfilename(
            initialdir=str(DEFAULT_STACKUP.parent),
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if selected:
            self.stackup_file.set(selected)

    def _start_extraction(self) -> None:
        if self.process is not None:
            return
        error = self._validate_inputs()
        if error:
            messagebox.showerror("Cannot start extraction", error)
            return

        output_path = Path(self.output_file.get())
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            sys.executable,
            "-u",
            str(PROJECT_ROOT / "scripts" / "extract_dimensions_fast.py"),
            "--data-dir",
            self.data_dir.get(),
            "--config",
            self.config_file.get(),
            "--dpi",
            str(self.dpi.get()),
            "--workers",
            str(self.workers.get()),
            "--output",
            str(output_path),
        ]

        self._append_log(f"Starting: {' '.join(command)}\n")
        self.status.set("Extraction running")
        self._set_running(True)
        self.process = subprocess.Popen(
            command,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        threading.Thread(target=self._read_process_output, daemon=True).start()

    def _stop_extraction(self) -> None:
        if self.process is None:
            return
        self._append_log("Stopping extraction...\n")
        self.process.terminate()

    def _read_process_output(self) -> None:
        assert self.process is not None
        assert self.process.stdout is not None
        for line in self.process.stdout:
            self.output_queue.put(("line", line))
        return_code = self.process.wait()
        self.output_queue.put(("done", str(return_code)))

    def _poll_output_queue(self) -> None:
        try:
            while True:
                event, payload = self.output_queue.get_nowait()
                if event == "line":
                    self._append_log(payload)
                    if self.auto_refresh.get():
                        self._load_results_if_present(silent=True)
                        self._load_stackup_if_present(silent=True)
                elif event == "done":
                    self._set_running(False)
                    self.process = None
                    self._load_results_if_present(silent=True)
                    self._load_stackup_if_present(silent=True)
                    if payload == "0":
                        self.status.set("Extraction complete")
                        self._append_log("Extraction complete.\n")
                    else:
                        self.status.set(f"Extraction stopped or failed with exit code {payload}")
                        self._append_log(f"Process exited with code {payload}.\n")
        except queue.Empty:
            pass
        self.root.after(250, self._poll_output_queue)

    def _validate_inputs(self) -> str | None:
        data_dir = Path(self.data_dir.get())
        config_file = Path(self.config_file.get())
        if not data_dir.exists() or not data_dir.is_dir():
            return f"Data folder does not exist:\n{data_dir}"
        if not config_file.exists() or not config_file.is_file():
            return f"Config file does not exist:\n{config_file}"
        if self.dpi.get() <= 0:
            return "DPI must be greater than zero."
        if self.workers.get() <= 0:
            return "Workers must be greater than zero."
        return None

    def _set_running(self, running: bool) -> None:
        self.start_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _load_results_from_output(self) -> None:
        self._load_results_if_present(silent=False)

    def _load_stackup_from_file(self) -> None:
        self._load_stackup_if_present(silent=False)

    def _load_stackup_if_present(self, silent: bool = False) -> None:
        stackup_path = Path(self.stackup_file.get())
        if not stackup_path.exists():
            if not silent:
                messagebox.showinfo("No stack-up file", f"Stack-up JSON does not exist:\n{stackup_path}")
            return
        try:
            state = json.loads(stackup_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            if not silent:
                messagebox.showerror("Could not read stack-up", f"The stack-up JSON is invalid:\n{exc}")
            return
        self._populate_stackup(state)
        self.status.set(f"Loaded tolerance stack-up from {stackup_path}")

    def _populate_stackup(self, state: dict[str, object]) -> None:
        for tree in (self.contributors_tree, self.references_tree, self.relationships_tree, self.actions_tree):
            tree.delete(*tree.get_children())

        chain_name = str(state.get("stackup_chain") or "bolt_protrusion_at_flange_2_interface")
        self.stack_title.set(chain_name.replace("_", " ").title())

        provisional = state.get("provisional_calculation") or {}
        model = state.get("recommended_stackup_model") or {}
        ppt_values = list(state.get("ppt_reference_values", []) or [])
        contributors = list(state.get("relevant_dimensions", []) or [])
        relationships = list(state.get("assembly_relationships", []) or [])

        nominal = self._number(provisional.get("known_contributors_only_nominal_mm") if isinstance(provisional, dict) else None)
        worst_min = self._number(provisional.get("known_contributors_only_worst_min_mm") if isinstance(provisional, dict) else None)
        worst_max = self._number(provisional.get("known_contributors_only_worst_max_mm") if isinstance(provisional, dict) else None)
        ppt_nominal = self._number(model.get("ppt_nominal_result_mm") if isinstance(model, dict) else None)
        if ppt_nominal is None:
            ppt_nominal = self._first_reference_value(ppt_values, "nominal")
        stack_dimension = model.get("known_direct_stack_dimension", {}) if isinstance(model, dict) else {}
        stack_nominal = self._number(stack_dimension.get("nominal_mm") if isinstance(stack_dimension, dict) else None)
        stack_plus = self._number(stack_dimension.get("plus_mm") if isinstance(stack_dimension, dict) else None)
        stack_minus = self._number(stack_dimension.get("minus_mm") if isinstance(stack_dimension, dict) else None)

        self.metric_nominal.set(self._fmt_mm(nominal))
        self.metric_range.set(f"{self._fmt_mm(worst_min)} to {self._fmt_mm(worst_max)}")
        self.metric_ppt.set(self._fmt_mm(ppt_nominal))

        self.calc_rows["Known contributors nominal"].set(self._fmt_mm(nominal))
        self.calc_rows["Known worst-case minimum"].set(self._fmt_mm(worst_min))
        self.calc_rows["Known worst-case maximum"].set(self._fmt_mm(worst_max))
        self.calc_rows["PPT reference nominal"].set(self._fmt_mm(ppt_nominal))
        self.calc_rows["PPT shown stack thickness"].set(self._fmt_tolerance(stack_nominal, stack_plus, stack_minus))

        note = ""
        if isinstance(provisional, dict):
            note = str(provisional.get("note") or "")
        caution = str(model.get("caution") if isinstance(model, dict) else "") or note
        self.stack_formula.set("Signed chain: bolt length adds protrusion; nut, washer, flange, and bracket stack thicknesses subtract from protrusion.")
        self._set_text(self.caution_text, f"{caution}\n\n{note}".strip())

        open_count = 0
        for item in contributors:
            if not isinstance(item, dict):
                continue
            nominal_value = self._number(item.get("nominal_mm"))
            plus = self._number(item.get("plus_mm"))
            minus = self._number(item.get("minus_mm"))
            sign = self._number(item.get("sign"))
            signed_nominal = nominal_value * sign if nominal_value is not None and sign is not None else None
            signed_worst = self._signed_worst_bounds(nominal_value, plus, minus, sign)
            status = str(item.get("status", ""))
            use = str(item.get("stackup_use", ""))
            if "need" in use or "confirm" in status or "verify" in status or "requires" in status:
                open_count += 1
                self.actions_tree.insert(
                    "",
                    "end",
                    values=(
                        item.get("stack_no", ""),
                        item.get("part", ""),
                        item.get("dimension_name", ""),
                        status,
                        use,
                        item.get("reason", ""),
                    ),
                )
            self.contributors_tree.insert(
                "",
                "end",
                values=(
                    item.get("stack_no", ""),
                    item.get("part", ""),
                    item.get("dimension_name", ""),
                    self._fmt_mm(nominal_value),
                    self._fmt_mm(plus),
                    self._fmt_mm(minus),
                    self._fmt_mm(signed_nominal),
                    self._fmt_mm(signed_worst[0]),
                    self._fmt_mm(signed_worst[1]),
                    status,
                    use,
                ),
            )
        self.metric_confirm.set(str(open_count))

        for ref in ppt_values:
            if not isinstance(ref, dict):
                continue
            self.references_tree.insert(
                "",
                "end",
                values=(
                    ref.get("name", ""),
                    self._fmt_mm(self._number(ref.get("value_mm"))),
                    self._fmt_mm(self._number(ref.get("plus_mm"))),
                    self._fmt_mm(self._number(ref.get("minus_mm"))),
                    ref.get("unit", ""),
                    ref.get("source", ""),
                ),
            )

        for relationship in relationships:
            if not isinstance(relationship, dict):
                continue
            self.relationships_tree.insert(
                "",
                "end",
                values=(
                    relationship.get("part1_id", ""),
                    relationship.get("part2_id", ""),
                    relationship.get("relationship_type", ""),
                    relationship.get("mating_surface1", ""),
                    relationship.get("mating_surface2", ""),
                    self._fmt_float(relationship.get("confidence_score")),
                ),
            )

    def _load_results_if_present(self, silent: bool = False) -> None:
        output_path = Path(self.output_file.get())
        if not output_path.exists():
            if not silent:
                messagebox.showinfo("No results yet", f"Output file does not exist:\n{output_path}")
            return
        try:
            state = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            if not silent:
                messagebox.showerror("Could not read results", f"The output JSON is incomplete or invalid:\n{exc}")
            return
        self.last_loaded_output = output_path
        self._populate_results(state)
        self.status.set(f"Loaded results from {output_path}")

    def _populate_results(self, state: dict[str, object]) -> None:
        for tree in (self.parts_tree, self.dimensions_tree, self.errors_tree, self.chains_tree):
            tree.delete(*tree.get_children())

        parts = list(state.get("parts", []) or [])
        total_dimensions = 0
        for part in parts:
            if not isinstance(part, dict):
                continue
            dimensions = list(part.get("dimensions", []) or [])
            gdt = list(part.get("gdt_callouts", []) or [])
            datums = list(part.get("datums", []) or [])
            materials = list(part.get("material_specs", []) or [])
            total_dimensions += len(dimensions)
            validation = part.get("validation") or {}
            valid = validation.get("is_valid", "") if isinstance(validation, dict) else ""
            self.parts_tree.insert(
                "",
                "end",
                values=(
                    self._short_path(part.get("source_file")),
                    part.get("part_id", ""),
                    len(dimensions),
                    len(gdt),
                    len(datums),
                    len(materials),
                    self._fmt_float(part.get("confidence_score")),
                    valid,
                ),
            )
            for dimension in dimensions:
                if not isinstance(dimension, dict):
                    continue
                tolerance = dimension.get("tolerance") or {}
                self.dimensions_tree.insert(
                    "",
                    "end",
                    values=(
                        self._short_path(part.get("source_file")),
                        dimension.get("part_id") or part.get("part_id", ""),
                        dimension.get("id", ""),
                        self._fmt_float(dimension.get("nominal_value")),
                        dimension.get("unit", ""),
                        dimension.get("measured_feature", ""),
                        self._format_tolerance(tolerance),
                        self._fmt_float(dimension.get("confidence_score")),
                        dimension.get("source_page", ""),
                        dimension.get("requires_human_review", ""),
                    ),
                )

        errors = state.get("errors") or {}
        page_errors = state.get("page_errors") or {}
        error_count = self._insert_errors(errors) + self._insert_errors(page_errors)

        chains = list(state.get("dimensional_chains", []) or [])
        for chain in chains:
            if not isinstance(chain, dict):
                continue
            links = chain.get("contributing_dimensions", []) or []
            link_text = ", ".join(str(link.get("dimension_id", "")) for link in links if isinstance(link, dict))
            self.chains_tree.insert(
                "",
                "end",
                values=(
                    chain.get("chain_id", ""),
                    chain.get("target_measurement", ""),
                    self._fmt_float(chain.get("total_nominal")),
                    self._fmt_float(chain.get("worst_case_min")),
                    self._fmt_float(chain.get("worst_case_max")),
                    self._fmt_float(chain.get("confidence_score")),
                    link_text,
                ),
            )

        usage = state.get("usage") or {}
        cost = usage.get("total_estimated_cost", 0.0) if isinstance(usage, dict) else 0.0
        self._append_log(f"Loaded extraction results: {len(parts)} parts, {total_dimensions} dimensions, {error_count} errors, estimated cost ${float(cost):.4f}\n")

    def _insert_errors(self, errors: object, prefix: str = "") -> int:
        count = 0
        if isinstance(errors, dict):
            for key, value in errors.items():
                location = f"{prefix}{key}"
                if isinstance(value, dict):
                    count += self._insert_errors(value, prefix=f"{location} / ")
                else:
                    self.errors_tree.insert("", "end", values=(location, value))
                    count += 1
        return count

    def _open_output_folder(self) -> None:
        output_path = Path(self.output_file.get())
        folder = output_path.parent if output_path.suffix else output_path
        if not folder.exists():
            messagebox.showinfo("Folder not found", f"Output folder does not exist:\n{folder}")
            return
        os.startfile(folder)

    @staticmethod
    def _short_path(value: object) -> str:
        if value is None:
            return ""
        path = Path(str(value))
        return path.name or str(value)

    @staticmethod
    def _fmt_float(value: object) -> str:
        if value in (None, ""):
            return ""
        try:
            return f"{float(value):.3f}"
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _format_tolerance(value: object) -> str:
        if not isinstance(value, dict) or not value:
            return ""
        tolerance_type = value.get("tolerance_type") or value.get("type") or ""
        if value.get("lower_limit") is not None or value.get("upper_limit") is not None:
            return f"{tolerance_type} {value.get('lower_limit', '')}..{value.get('upper_limit', '')}"
        plus = value.get("plus")
        minus = value.get("minus")
        unit = value.get("unit") or ""
        if plus is not None or minus is not None:
            return f"{tolerance_type} +{plus or 0} / -{minus or 0} {unit}".strip()
        return str(tolerance_type)

    @staticmethod
    def _number(value: object) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _fmt_mm(value: float | None) -> str:
        if value is None:
            return "--"
        return f"{value:.3f} mm"

    @classmethod
    def _fmt_tolerance(cls, nominal: float | None, plus: float | None, minus: float | None) -> str:
        if nominal is None:
            return "--"
        if plus is None and minus is None:
            return cls._fmt_mm(nominal)
        return f"{nominal:.3f} +{plus or 0:.3f} / -{minus or 0:.3f} mm"

    @staticmethod
    def _signed_worst_bounds(nominal: float | None, plus: float | None, minus: float | None, sign: float | None) -> tuple[float | None, float | None]:
        if nominal is None or sign is None:
            return None, None
        plus = plus or 0.0
        minus = minus or 0.0
        low = nominal - minus
        high = nominal + plus
        signed_low = low * sign
        signed_high = high * sign
        return min(signed_low, signed_high), max(signed_low, signed_high)

    @classmethod
    def _first_reference_value(cls, values: list[object], keyword: str) -> float | None:
        for value in values:
            if isinstance(value, dict) and keyword.lower() in str(value.get("name", "")).lower():
                return cls._number(value.get("value_mm"))
        return None

    def _plain_text_widget(self, parent: ttk.Frame, height: int):
        from tkinter import Text

        text = Text(parent, height=height, wrap="word", relief="flat", padx=8, pady=8, font=("Segoe UI", 9))
        text.configure(bg="#ffffff", fg="#18202a", insertbackground="#18202a", state="disabled")
        return text

    @staticmethod
    def _set_text(widget: object, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", value)
        widget.configure(state="disabled")


def main() -> None:
    root = Tk()
    app = ExtractionGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
