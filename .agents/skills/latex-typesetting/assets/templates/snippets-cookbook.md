# 国赛排版片段手册（提炼自 `example.tex`，`cumcmthesis.cls` 下直接可用）

> 用法：按需复制对应片段进 `cumcm-paper.tex`，一次一图/一表一编译。
> 标签唯一，命名见实义英文；引用只用 `\cref`。

## 编译

```text
latexmk -xelatex cumcm-paper
```

## 单图

```latex
\begin{figure}[htbp]
    \centering
    \includegraphics[width=.6\linewidth]{filename}
    \caption{图题}
    \label{fig:meaningful-name}
\end{figure}
```

引用：`\cref{fig:meaningful-name}`。位图用 `jpg/png`，矢量图用 `pdf`；文件名英文实义，不用 `1,2,3`。

## 并排图（等宽）

```latex
\begin{figure}[htbp]
    \centering
    \begin{minipage}[c]{0.3\linewidth}
        \centering
        \includegraphics[width=0.95\linewidth]{fig-a}
        \subcaption{子图题}
        \label{fig:group-a}
    \end{minipage}
    \begin{minipage}[c]{0.3\linewidth}
        \centering
        \includegraphics[width=0.95\linewidth]{fig-b}
        \subcaption{子图题}
        \label{fig:group-b}
    \end{minipage}
    \caption{大图题}
    \label{fig:group}
\end{figure}
```

## 并排图（等高，原图高不同）

```latex
\includegraphics[height=0.2\textheight]{fig-a}
```

## 标准三线表

```latex
\begin{table}[htbp]
    \caption{中文标题}\label{tab:001} \centering
    \begin{tabular}{ccccc}
        \toprule[0.8pt]
        表头1 & 表头2 & 表头3 \\
        \midrule[0.5pt]
        数据 & 数据 & 数据 \\
        \bottomrule[0.8pt]
    \end{tabular}
\end{table}
```

`booktabs` 已加载，不重复加载；线宽按本模板约定不过粗。

## 公式

行内 `$ \theta $`；无编号行间 `\[ E=mc^2 \]`；被引用才编号：

```latex
\begin{equation}
E=mc^2
\label{eq:energy}
\end{equation}
```

引用：式`\cref{eq:energy}`。多行对齐：

```latex
\begin{align}
P & = UI \\
  & = I^2R
\end{align}
```

矩阵：

```latex
\[
\mathbf{X} = \left(
    \begin{array}{cccc}
    x_{11} & x_{12} & \ldots & x_{1n}\\
    x_{21} & x_{22} & \ldots & x_{2n}\\
    \end{array} \right)
\]
```

分段函数（`cases` 放数学环境内，文字用 `\text{}`）：

```latex
\[
f(x) =
    \begin{cases}
        0 &  x \text{为无理数} ,\\
        1 &  x \text{为有理数} .
    \end{cases}
\]
```

加粗符号：`$\bm{\alpha}$`。

## 定理族（12 环境，按需取用）

`definition theorem lemma corollary assumption conjecture axiom principle problem example proof solution`，写法一致：

```latex
\begin{theorem}
    这是一个定理。
    \label{thm:example}
\end{theorem}
```

引用：`\cref{thm:example}`。

## 代码附录（`listings` 已配好样式）

```latex
\begin{lstlisting}[language=matlab]
% 全部完整、可运行源程序全文
\end{lstlisting}
```

`language=` 按实际语言换（`matlab/python/c` 等）。

## 参考文献

```latex
正式论文应在正文引用处使用 \verb|\cite{bibkey}| 标注文献，例如规范\cite{mathematical-modeling}。

\begin{thebibliography}{9}
    \bibitem[1]{mathematical-modeling}
    全国大学生数学建模竞赛论文格式规范（2026 年修订稿）, 2026 年 3 月 3 日.
\end{thebibliography}
```

## 脚注 / 列表 / 强调

- 脚注：`\footnote{补充说明}`。
- 无序 `itemize`，有序 `enumerate`（`enumitem` 已配好间距）。
- 加粗 `\textbf{}`；中文无斜体，英文斜体 `\textit{}` 慎用。
