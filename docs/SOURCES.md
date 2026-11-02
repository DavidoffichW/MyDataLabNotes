# Sources for "How do we know an algorithm worked?"

The notebook cites these entries directly:

- **S002** — FPWM Lab at commit
  `4385a7bde30ca1dd34c65994fe7691599e0da12a`, used only as a presentation and
  execution-method precedent. No FPWM source, data, figures, or domain claims
  are copied.
- **S005** — Cormen, Leiserson, Rivest, and Stein, *Introduction to
  Algorithms*, 4th edition, MIT Press, 2022. Used for loop-invariant,
  correctness, and asymptotic-analysis foundations.
- **S060** — [nbclient documentation](https://nbclient.readthedocs.io/), used
  for fresh-kernel execution.
- **S061** — Python's
  [`timeit` documentation](https://docs.python.org/3/library/timeit.html), used
  for the limits of small timing experiments.
- **S062** — NumPy's
  [random sampling documentation](https://numpy.org/doc/stable/reference/random/),
  used for explicit generator and seed recording.
- **S063** — [pyperf system guidance](https://pyperf.readthedocs.io/en/latest/system.html),
  used to qualify environmental timing noise.
- **S064** — [Hypothesis documentation](https://hypothesis.readthedocs.io/),
  used for generated cases and minimized counterexamples.

These are citations, not copied implementation sources. Publisher and project
terms remain with their respective works.

# Sources for "The Same Value, Different Bytes"

- **S066** — ISO/IEC JTC 1/SC 22/WG14,
  [N1570, Committee Draft — ISO/IEC 9899:201x](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf).
  Used for the C object-representation, alignment, structure, and character-byte
  rules that C17 retains for this experiment.
- **S067** — ISO/IEC JTC 1/SC 22/WG14,
  [C language project status](https://open-std.org/jtc1/sc22/wg14/www/projects.html).
  Used to identify C17 as ISO/IEC 9899:2018.
- **S068** — GNU Compiler Collection,
  [Language Standards Supported by GCC](https://gcc.gnu.org/onlinedocs/gcc/Standards.html).
  Used to qualify the `-std=c17` compiler mode.
- **S069** — Microsoft,
  [Install C11 and C17 support in Visual Studio](https://learn.microsoft.com/en-us/cpp/overview/install-c17-support?view=msvc-170).
  Used to qualify `/std:c17` on the Windows CI toolchain.
- **S070** — Python Software Foundation,
  [`struct` — Interpret bytes as packed binary data](https://docs.python.org/3/library/struct.html).
  Used for the independent explicit-width, big-endian packet oracle.

The native source and diagrams are independently authored for this repository.
The FNV-1a state fingerprint is used only as a compact error-detection aid; it
is not treated as authentication or proof of an uncorrupted history.
