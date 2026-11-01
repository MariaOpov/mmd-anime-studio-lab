"""Small stand-alone Tk interface to MMD Lab. No repository integration or writes."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from .host import ExtensionHost


class LabWindow:
    def __init__(self, host: ExtensionHost):
        self.host = host
        self.root = tk.Tk()
        self.root.title('MMD Anime Studio | MMD Lab CP01')
        self.root.geometry('940x660')
        self.root.minsize(700, 520)
        self.root.configure(bg='#121b2b')
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.latest = None
        self._setup_styles()
        self._build()
        self.root.protocol('WM_DELETE_WINDOW', self._close)

    def _setup_styles(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('Primary.TButton', background='#5c81e8', foreground='white', padding=(12, 9), font=('Segoe UI', 10, 'bold'))
        style.map('Primary.TButton', background=[('active', '#3b64d1')])
        style.configure('Secondary.TButton', background='#273650', foreground='white', padding=(10, 9))
        style.configure('Lab.TCheckbutton', background='#1b283d', foreground='#ebeff8', font=('Segoe UI', 10))

    def _build(self):
        base = tk.Frame(self.root, bg='#121b2b', padx=22, pady=18)
        base.pack(fill='both', expand=True)
        tk.Label(base, text='MMD ANIME STUDIO', bg='#121b2b', fg='#8daafc', font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        tk.Label(base, text='MMD Lab  /  CP01', bg='#121b2b', fg='white', font=('Segoe UI', 25, 'bold')).pack(anchor='w', pady=(3, 0))
        tk.Label(base, text='Independent extension workspace  •  Offline  •  Read-only  •  No PMX/VMD changes',
                 bg='#121b2b', fg='#a6b5ca', font=('Segoe UI', 10)).pack(anchor='w', pady=(3, 14))
        panel = tk.Frame(base, bg='#1b283d', padx=14, pady=12)
        panel.pack(fill='x')
        tk.Label(panel, text='EXTENSION MANAGER', bg='#1b283d', fg='#aec6fa', font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        self.toggles = {}
        for ext in self.host.extensions.values():
            line = tk.Frame(panel, bg='#1b283d')
            line.pack(fill='x', pady=4)
            value = tk.BooleanVar(value=True)
            ttk.Checkbutton(line, text=f'{ext.name}  •  {ext.suffix.upper()}', variable=value,
                            style='Lab.TCheckbutton', command=self._apply_toggles).pack(side='left')
            tk.Label(line, text=ext.description, bg='#1b283d', fg='#93a6c0',
                     font=('Segoe UI', 9), wraplength=460, justify='left').pack(side='left', padx=16)
            self.toggles[ext.id] = value
        controls = tk.Frame(base, bg='#121b2b')
        controls.pack(fill='x', pady=(14, 11))
        self.selected = tk.StringVar(value='No file selected')
        ttk.Button(controls, text='Choose PMX / VMD', command=self._choose, style='Primary.TButton').pack(side='left')
        ttk.Button(controls, text='Inspect', command=self._inspect, style='Secondary.TButton').pack(side='left', padx=8)
        ttk.Button(controls, text='Demo PMX', command=lambda: self._demo('SYNTHETIC_DEMO.pmx'), style='Secondary.TButton').pack(side='left', padx=3)
        ttk.Button(controls, text='Demo VMD', command=lambda: self._demo('SYNTHETIC_DEMO.vmd'), style='Secondary.TButton').pack(side='left', padx=3)
        tk.Label(controls, textvariable=self.selected, fg='#c9d4e8', bg='#121b2b',
                 font=('Segoe UI', 9), anchor='w').pack(side='left', fill='x', expand=True, padx=7)
        self.status = tk.StringVar(value='CP01: synthetic demo files only')
        tk.Label(base, textvariable=self.status, bg='#121b2b', fg='#91b8ff', anchor='w',
                 font=('Segoe UI', 10, 'bold')).pack(fill='x', pady=(4, 6))
        output_frame = tk.Frame(base, bg='#1b283d', padx=10, pady=10)
        output_frame.pack(fill='both', expand=True)
        bar = ttk.Scrollbar(output_frame)
        bar.pack(side='right', fill='y')
        self.output = tk.Text(output_frame, bg='#152137', fg='#e4ebf5',
                              font=('Consolas', 10), insertbackground='white',
                              relief='flat', padx=13, pady=12, wrap='word',
                              yscrollcommand=bar.set)
        self.output.pack(side='left', fill='both', expand=True)
        bar.configure(command=self.output.yview)
        self._write('Welcome to MMD Lab CP01.\n\nSynthetic demos only in CP01. External model inspection is HOLD.\n\n'
                    'Current scope:\n  • PMX: metadata, geometry index validation and texture declarations\n'
                    '  • VMD: bone / morph track counts and maximum frame\n\n'
                    'Material, bone, morph-structure and full physics checks are NOT implemented yet.')

    def _apply_toggles(self):
        self.host.enabled = {name for name, value in self.toggles.items() if value.get()}
        self.status.set(f'{len(self.host.enabled)} trusted extensions enabled (session only)')

    def _choose(self):
        filename = filedialog.askopenfilename(title='Select MMD model / motion',
                                              filetypes=[('MMD assets', '*.pmx *.vmd'), ('All files', '*.*')])
        if filename:
            self.selected.set(filename)

    def _write(self, content):
        self.output.delete('1.0', 'end')
        self.output.insert('end', content)

    def _demo(self, name: str):
        self.selected.set(str(Path(__file__).resolve().parent / 'demo_synthetic' / name))
        self._inspect()

    def _inspect(self):
        filename = self.selected.get()
        if not Path(filename).is_file():
            messagebox.showwarning('MMD Lab', 'Select an existing local PMX/VMD file first.')
            return
        permitted = Path(__file__).resolve().parent / 'demo_synthetic'
        if not Path(filename).resolve().is_relative_to(permitted.resolve()):
            self.status.set('HOLD — external assets are not authorized in CP01')
            messagebox.showwarning('CP01 synthetic-only gate',
                'LAB-CP01 is synthetic-only. Use Demo PMX or Demo VMD.\n'
                'External PMX/VMD access requires separate Owner authorization.')
            return
        self.status.set('Inspecting offline...')
        self._write('Reading metadata and validating bounds. No source file writes.\n')
        future = self.pool.submit(self.host.run, filename)
        self._poll(future)

    def _poll(self, future):
        if not future.done():
            self.root.after(100, lambda: self._poll(future))
            return
        try:
            report = future.result()
        except Exception as ex:
            self.status.set('FAIL — unexpected inspector error')
            self._write(f'Unexpected failure: {type(ex).__name__}: {ex}')
            return
        self.latest = report
        self.status.set(f'{report.status}  •  {report.filename}  •  {len(report.findings)} findings')
        lines = [f'MMD Lab / {report.tool}', f'FILE: {report.filename}', f'STATUS: {report.status}', '', 'SUMMARY']
        lines += [f'  {key}: {value}' for key, value in report.summary.items()]
        lines += ['', 'FINDINGS']
        lines += [f'  [{f.severity}] {f.code}: {f.message}' for f in report.findings]
        lines += ['', 'RAW REPORT (structured)', json.dumps(report.as_dict(), ensure_ascii=False, indent=2)]
        self._write('\n'.join(lines))
        print(f'INSPECT_TOOL={report.tool} STATUS={report.status} FILE={report.filename}', flush=True)

    def _close(self):
        self.pool.shutdown(wait=False, cancel_futures=True)
        self.root.destroy()


def launch(host: ExtensionHost) -> None:
    app = LabWindow(host)
    app.root.mainloop()
