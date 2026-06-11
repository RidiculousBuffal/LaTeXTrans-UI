from pathlib import Path

from backend.src.formats.latex.parser import LatexParser
from backend.src.formats.latex.utils import add_ctex_package, merge_tex_from_inputs


def test_add_ctex_package_skips_acmart() -> None:
    latex = r"""\documentclass[sigplan,10pt,nonacm]{acmart}
\usepackage{amsmath}
\begin{document}
hello
\end{document}
"""

    result = add_ctex_package(latex)

    assert r"\usepackage[UTF8]{ctex}" not in result


def test_add_ctex_package_injects_for_non_acmart() -> None:
    latex = r"""\documentclass{article}
\usepackage{amsmath}
\begin{document}
hello
\end{document}
"""

    result = add_ctex_package(latex)

    assert r"\usepackage[UTF8]{ctex}" in result


def test_merge_tex_from_inputs_ignores_same_name_directory(tmp_path: Path) -> None:
    main_file = tmp_path / "main.tex"
    appendix_dir = tmp_path / "appendix"
    appendix_dir.mkdir()
    appendix_file = tmp_path / "appendix.tex"

    main_file.write_text("Intro\n\\input{appendix}\n", encoding="utf-8")
    appendix_file.write_text("Appendix body\n", encoding="utf-8")

    result = merge_tex_from_inputs(str(main_file))

    assert "Appendix body" in result
    assert "\\input{appendix}" not in result


def test_latex_parser_merge_inputs_ignores_same_name_directory(tmp_path: Path) -> None:
    appendix_dir = tmp_path / "appendix"
    appendix_dir.mkdir()
    appendix_file = tmp_path / "appendix.tex"
    appendix_file.write_text("Appendix body\n", encoding="utf-8")

    parser = LatexParser(str(tmp_path), str(tmp_path / "out"))

    result = parser._merge_inputs("Intro\n\\input{appendix}\n")

    assert "Appendix body" in result
    assert parser.inputs_json == [
        {
            "command": "\\input{appendix}",
            "begin": "<PLACEHOLDER_appendix_begin>",
            "end": "<PLACEHOLDER_appendix_end>",
            "path": "appendix",
        }
    ]
