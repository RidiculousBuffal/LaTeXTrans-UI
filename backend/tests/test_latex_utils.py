from backend.src.formats.latex.utils import add_ctex_package


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
