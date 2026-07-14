import os
import subprocess
from typing import Any, Dict, Mapping

from backend.app.core.task_runtime import TaskTimeoutError, build_task_timeout_message, ensure_time_remaining

from .utils import *


class LaTexCompiler:
    def __init__(self, output_latex_dir: str, config: Mapping[str, Any] | None = None):
        self.output_latex_dir = output_latex_dir
        self.config = config or {}

    def compile(self):
        """
        Compile the LaTeX document .
        """
        tex_file_to_compile = find_main_tex_file(self.output_latex_dir)
        if not tex_file_to_compile:
            print("⚠️ Warning: There is no main tex file to compile in this directory.")
            return None
        print("Start compiling with xelatex...⏳")
        compile_out_dir_xelatex = os.path.join(self.output_latex_dir, "build_xelatex")
        self._compile_with_xelatex(tex_file_to_compile, compile_out_dir_xelatex, engine="xelatex")
        pdf_files = [os.path.join(compile_out_dir_xelatex, file) for file in os.listdir(compile_out_dir_xelatex) if file.lower().endswith('.pdf')]
        if pdf_files:
            print("✅ Successfully generated PDF file!")
            return pdf_files[0]
        print("⚠️ Failed to generate PDF with xelatex. Please check the log.")
        log_files_xelatex = [
            os.path.join(compile_out_dir_xelatex, file)
            for file in os.listdir(compile_out_dir_xelatex)
            if file.lower().endswith(".log")
        ]
        if log_files_xelatex:
            print(f"📄 Log files for xelatex: {log_files_xelatex}")
        return None
    

    def compile_ja(self):
        """
        Compile the LaTeX document .
        """
        tex_file_to_compile = find_main_tex_file(self.output_latex_dir)
        if not tex_file_to_compile:
            print("⚠️ Warning: There is no main tex file to compile in this directory.")
            return None
        print("Start compiling with lualatex...⏳")
        compile_out_dir_lualatex = os.path.join(self.output_latex_dir, "build_lualatex")
        self._compile_with_lualatex(tex_file_to_compile, compile_out_dir_lualatex, engine="lualatex")
        pdf_files = [os.path.join(compile_out_dir_lualatex, file) for file in os.listdir(compile_out_dir_lualatex) if file.lower().endswith('.pdf')]
        if pdf_files:

            print(f"✅  Successfully generated PDF file !") 
            return pdf_files[0]
        else:
            print(f"⚠️  Failed to generate PDF with xelatex. Please check the log.")
            # log_files_xelatex = [os.path.join(compile_out_dir_xelatex, file) for file in os.listdir(compile_out_dir_xelatex) if file.lower().endswith('.log')]
            log_files_lualatex = [os.path.join(compile_out_dir_lualatex, file) for file in os.listdir(compile_out_dir_lualatex) if file.lower().endswith('.log')]
            if log_files_lualatex:
                print(f"📄 Log files for lualatex: {log_files_lualatex}")
            return None

    def compile_source(self, pdf_dir):
        if pdf_dir is None:
            pdf_dir = self.output_latex_dir
        os.makedirs(pdf_dir, exist_ok=True)  # Ensure directory exists

        tex_file_to_compile = find_main_tex_file(self.output_latex_dir)
        if not tex_file_to_compile:
            print("⚠️ Warning: No main .tex file found in directory.")
            return None

        print("Start compiling with xelatex...⏳")
        self._compile_with_xelatex(
            tex_file_to_compile,
            out_dir=pdf_dir,
            engine="xelatex"
        )

        pdf_files = [
            f for f in os.listdir(pdf_dir)
            if f.lower().endswith('.pdf') and not f.startswith('._')
        ]

        if pdf_files:
            pdf_path = os.path.join(pdf_dir, pdf_files[0])
            print(f"✅ Successfully generated PDF at: {pdf_path}")
            return pdf_path

        print("⚠️ Failed to generate PDF with xelatex.")
        log_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.log')]
        if log_files:
            print("📄 Compilation logs:")
            for log in log_files:
                print(f"  - {os.path.join(pdf_dir, log)}")

        return None

    def _compile_with_xelatex(self,
                              tex_file: str, 
                              out_dir: str, 
                              engine: str = "xelatex"):
        out_dir = os.path.abspath(out_dir)
        os.makedirs(out_dir, exist_ok=True)
        tex_file = os.path.abspath(tex_file)
        tex_file_name = os.path.basename(tex_file)
        cwd = os.path.dirname(tex_file)
        
        cmd = [
            "latexmk",
            f"-{engine}",                
            "-interaction=nonstopmode",   # no stop on errors
            f"-outdir={out_dir}",  
            f"-file-line-error",       
            f"-synctex=1",
            f"-f",                        # force mode
            tex_file_name
        ]
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                cwd=cwd,
                timeout=self._get_timeout_seconds(),
            )
            print("✅  Compilation successful!") #compile success!
        except subprocess.TimeoutExpired as exc:
            raise self._build_timeout_error() from exc
        except subprocess.CalledProcessError as e:
            print("⚠️  Somthing went wrong during compiling with xelatex.")


    def _compile_with_lualatex(self,
                              tex_file: str, 
                              out_dir: str, 
                              engine: str = "lualatex"):
        out_dir = os.path.abspath(out_dir)
        os.makedirs(out_dir, exist_ok=True)
        tex_file = os.path.abspath(tex_file)
        tex_file_name = os.path.basename(tex_file)
        cwd = os.path.dirname(tex_file)
        
        cmd = [
            "latexmk",
            f"-{engine}",                
            "-interaction=nonstopmode",   # no stop on errors
            f"-outdir={out_dir}",  
            f"-file-line-error",       
            f"-synctex=1",
            f"-f",                        # force mode
            tex_file_name
        ]
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                cwd=cwd,
                timeout=self._get_timeout_seconds(),
            )
            print("✅  Compilation successful!") #compile success!

            output_path = os.path.join(self.output_latex_dir, "success.txt")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("Compilation successful\n")
                
        except subprocess.TimeoutExpired as exc:
            raise self._build_timeout_error() from exc
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Somthing went wrong during compiling with lualatex. \n {e}")

    def _get_timeout_seconds(self) -> float:
        runtime = self.config.get("runtime", {})
        return ensure_time_remaining(
            self.config,
            default_timeout_seconds=int(runtime.get("task_timeout_seconds", 20 * 60)),
            context="Translation task",
        )

    def _build_timeout_error(self) -> TaskTimeoutError:
        timeout_seconds = int(self.config.get("runtime", {}).get("task_timeout_seconds", 20 * 60))
        return TaskTimeoutError(
            build_task_timeout_message(timeout_seconds=timeout_seconds, context="Translation task")
        )
