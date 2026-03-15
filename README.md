# SageTeX helper functions
## Introduction
You may already know [SageTeX](https://mirrors.mit.edu/CTAN/macros/latex/contrib/sagetex/sagetex.pdf) from past experiences of having used LaTeX. With such a package, and the help of the [SageMath](https://www.sagemath.org/) computer algebra system (CAS), one can program equations directly into a LaTeX document:
```latex
\begin{sagesilent}
x = var('x')
y = 5
expr = 4*x + 2*y == 0
x_solved = solve(expr, x)[0].rhs()
\end{sagesilent}
Thus, the value of $x$ is $\sage{x_solved}$.
```
The result then gets printed out cleanly when you call `\sage{z}` later in your document. For example, the code above produces:
![Calculation result][https://raw.githubusercontent.com/tux-linux/sagetex-functions/refs/heads/main/assets/demo1.png]
## 
