# $\text{Sage\TeX}$ helper functions
## Introduction
You may already know [$\text{Sage\TeX}$](https://mirrors.mit.edu/CTAN/macros/latex/contrib/sagetex/sagetex.pdf) from past experiences of having used $\text{\LaTeX}$. With such a package, and the help of the [SageMath](https://www.sagemath.org/) computer algebra system (CAS), one can program equations (and have them solved) directly into a LaTeX document:
```latex
\begin{sagesilent}
x = var('x')
y = 5
expr = 4*x + 2*y == 0
x_solved = solve(expr, x)[0].rhs()
\end{sagesilent}
Thus, the value of $x$ is $\sage{x_solved}$.
```
For example, the above code produces:
<div style="text-align: center;">
<img src="https://raw.githubusercontent.com/tux-linux/sagetex-functions/refs/heads/main/assets/demo1.png" width="346" height="90"/>
</div>

## Limitations about extensive $\text{Sage\TeX}$ use
Suppose you have an physics assignment about your favourite class subject to hand in. As you just discovered $\text{Sage\TeX}$ by visiting this repository or because some high-tech friend told you about it, you immediately see the potential it could have to help you mitigate the risks of having your quirky brain inevitably commit mathematical mistakes wherever it sees fit (a forgotten exponent or multiplication, or a mere sign issue, for example). But you soon realize that $\text{Sage\TeX}$ is not necessarily perfect.

### How it can get messy

Consider the following physics problem, which has been oversimplified to get to the point as fast as possible:

*Some person randomly decides to drop a ball in the middle of nowhere. The ball falls down vertically and is only subject to the force of gravity. The ball has an initial velocity of 1 m/s. If the ball has covered 4 m in distance and has a final velocity of 8 m/s, find what is the vertical acceleration provided by gravity.*

It can be quickly summarized in a few lines of Python/Sage code inside our LaTeX document, and then typeset using a standard syntax:

```latex
\begin{sagesilent}
v_o = 1         # m/s
v = 8           # m/s
a = var('a')    # m/s^2
L = 4           # m

a = solve(v^2 == v_o^2 + 2 * a * L, a)[0].rhs()
\end{sagesilent}
We know that
\[
    v^2 = v_o^2 + 2aL
\]
Substituting the given values, we obtain:
\[
    \sage{v} = \sage{v_o} + 2\sage{a*L}
\]
```
This will produce the following LaTeX output:
<div style="text-align: center;">
<img src="https://raw.githubusercontent.com/tux-linux/sagetex-functions/refs/heads/main/assets/demo2.png" width="700" height="228"/>
</div>

#### This works fine. Where's the problem, then?

Suppose you broke the laws of physics and that suddenly, the given equation that's been known for centuries does not hold up anymore. Provided that you haven't caused a worldwide meltdown and that you are still alive, you now have to modify your LaTeX document for it to be as up-to-date as possible with the current laws of physics.

#### How can that be *so* bad?

In this example, there was only **one** equation to adapt. Note though that if you care enough about your readers, you will want to change not only the equation's definition in the Sage code, but also the one in the actual LaTeX code that is typeset, where you defined the equation **and** then monkey-patched it by substituting in your values at the last step, leaving the actual operators defined once more in another place than in the environment where the computation actually happens. In the end, this means you have to modify your document at **three** different places for the **same change**.

So, how to tweak our code so that we only have to change the equation at a single place with the rest of the document automatically updating at the next compilation?

#### Well, I understand. I could define the equations in Sage without numerical values and substitute them only at the very end.

Fair enough, let's try that out.
```latex
\begin{sagesilent}
v_o = var('v_o')
v = var('v')
a = var('a')
L = var('L')

expr = v^2 == v_o^2 + 2 * a * L
\end{sagesilent}
We know that
\[
    \sage{expr}
\]
```
Don't get me wrong, it *will* print this equation correctly (notice, though, that Sage rearranged the presentation according to its own free will). Now, suppose we want to procedurally generate the LaTeX output *exactly* as it was in the previous method:
```latex
\begin{sagesilent}
    expr = expr.subs(v_o = 1, v = 8, L = 4)
\end{sagesilent}
Substituting the given values, we obtain:
\[
    \sage{expr}\Longrightarrow a=\sage{solve(expr, a)[0].rhs()}\:\text{m/s$^2$}
\]
```
This finally produces:
<div style="text-align: center;">
<img src="https://raw.githubusercontent.com/tux-linux/sagetex-functions/refs/heads/main/assets/demo3.png" width="688" height="265.33333333"/>
</div>
There are several issues with this approach:

- **Missing verbosity**: while manually typesetting our equation in the previous example, we took the liberty to put parentheses around `a * 4` and a `\cdot` (multiplication dot) between the two members inside the parentheses. Note how Sage did not notice it and simplified the equation right away. It may not seem significant with this example, but provided that you have a more complicated equation containing square roots and multiple fractions, Sage *will* automatically simplify them as soon as it can. This may render your formula unrecognizable from the textbooks' and may lead to confusion among your readers.
- We were forced to systematically declare all of our variables, which is something that gets clunky over time.
- Sage rearranges the equation's layout as it sees fit, and does not at all consider the form of the input that the user entered into it. Hence, when it calls `latex()` on an expression, the layout it returns follows Sage's formatting rules and not yours.

## So, what can we do?

### Standard expressions
To get around such issues, I have designed specific Python functions that simultaneously return a verbose LaTeX expression as well as the actual Sage expression to be used for internal calculation purposes. For example, if we take a look at the following expression:

$$\frac{3x\sqrt{yx\cdot\frac{4}{87}\cdot\frac{x^2}{53\cdot 8}}}{4\sqrt{yx^2}}$$

In plain LaTeX, we would typeset it out as:
```latex
\frac{3x\sqrt{yx\cdot\frac{4}{87}\cdot\frac{x^2}{53\cdot 8}}}{4\sqrt{yx^2}}
```
With standard Sage syntax, we would instead write
```latex
\begin{sagesilent}
x = var('x')
y = var('y')

expr = 3*x * sqrt(y*x * 4/87 * x^2 / (53 * 8)) / (4 * sqrt(y*x^2))
\end{sagesilent}
\[
    \sage{expr}
\]
```
which would yield the following:
<div style="text-align: center;">
<img src="https://raw.githubusercontent.com/tux-linux/sagetex-functions/refs/heads/main/assets/demo4.png" width="181" height="117"/>
</div>

I think everyone can agree on the fact that this does not look like the original expression *at all*.

Now consider this:
```latex
\begin{sagesilent}
x = var('x')
y = var('y')
z = var('z')

expr, _expr = dexpr([3,TIMES,x,TIMES,[[y,TIMES,x,TIMES,4,TIMES,x^2],DIV,[87,TIMES,53,TIMES,8]],POW,1/2,DIV,[4,TIMES,[y,TIMES,x,POW,2],POW,1/2]])
\end{sagesilent}
\begin{gather*}
	\text{Custom \LaTeX\:expression: }\sage{_expr}\\
	\text{Native Sage\TeX\:expression: }\sage{expr}
\end{gather*}
```
It now renders as:
<div style="text-align: center;">
<img src="https://raw.githubusercontent.com/tux-linux/sagetex-functions/refs/heads/main/assets/demo5.png" width="467" height="212.5"/>
</div>

Notice how the $\text{Sage\TeX}$ expression is exactly the same as the one obtained before, yet we have only written it out **once** (albeit having achieved that with a slightly more convoluted syntax) **and** we were able to enforce its formatting correctly.

#### The `dexpr` function
This function, which is the main building block of the framework I have designed, takes standard Python lists as arguments. If you want an equation to be returned, you provide it with two arguments, the left-hand side (LHS) and the right-hand side (RHS) of the equation. If you only want an expression to be returned, you only need to provide the LHS.

Take this straightforward example:

$$5x+4x+y=8$$

$\text{Sage\TeX}$ wouldn't allow us to display it this way (it would automatically add the terms with $x$ together, resulting in $9x+y=8$). Thus, let's use the `dexpr` function for this:

```latex
\begin{sagesilent}
	x = var('x')
	y = var('y')
    expr, _expr = dexpr([5*x, 4*x, y], [8])
\end{sagesilent}
The expression is $\sage{_expr}$.

The Sage\TeX\:representation of this expression is instead $\sage{expr}$.
```
We obtain:
<div style="text-align: center;">
<img src="https://raw.githubusercontent.com/tux-linux/sagetex-functions/refs/heads/main/assets/demo6.png" width="719.25" height="84"/>
</div>

Note that although you can use standard operators everywhere (`PLUS`, `MINUS`, `TIMES`, `DIV`, for example), if we are on the first level of a list, the function assumes addition between elements by default.

### Matrices
Suppose that you follow a course about electrical circuits and that you have to use the formula

$$GV=I$$

where $G$ is the conductance matrix, $V$ is the voltage matrix and $I$ is the electric current matrix. Knowing that the elements of $G$ are of the form

$$G_{ij}=\frac{1}{R_1}+\frac{1}{R_2}+\dots+\frac{1}{R_n}$$

we typically see such matrices in textbooks written out as:

$$G=\begin{pmatrix}\frac{1}{1}+\frac{1}{2}&-1\\-1&\frac{1}{1}+\frac{1}{3}\end{pmatrix}$$

How would we do this with vanilla $\text{Sage\TeX}$? We might be tempted to write the following:

```latex
\begin{sagesilent}
    M = matrix([[1/1+1/2, -1],[-1, 1/1+1/3]])
\end{sagesilent}
We obtain the following matrix:
\[
    G=\sage{M}
\]
```
This gives us:
<div style="text-align: center;">
<img src="https://raw.githubusercontent.com/tux-linux/sagetex-functions/refs/heads/main/assets/demo7.png" width="592" height="137.6"/>
</div>

That is obviously *not* what we wanted. Instead, what about this:
```latex
\begin{sagesilent}
    M, _M = matdexpr([[dexpr([1,DIV,1,1,DIV,2]),-1],[-1,dexpr([1,DIV,1,1,DIV,3])]])
\end{sagesilent}
We obtain the following matrix:
\[
    G=\sage{M}
\]
```

That instead yields:
<div style="text-align: center;">
<img src="https://raw.githubusercontent.com/tux-linux/sagetex-functions/refs/heads/main/assets/demo8.png" width="592" height="137.6"/>
</div>
