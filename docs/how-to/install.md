# Install

staketracker needs Python 3.12 or later. It is not on PyPI yet, so install it from the repository.

## With uv (recommended)

```bash
git clone https://github.com/glacioraide/staketracker.git
cd staketracker
uv sync
source .venv/bin/activate
```

uv installs the exact versions from `uv.lock`.

## With pip

```bash
git clone https://github.com/glacioraide/staketracker.git
cd staketracker
python -m venv .venv
source .venv/bin/activate
pip install .
```

pip ignores `uv.lock`, so you may get newer dependency versions than the tested ones.

## Optional extras

| Extra | Adds | Install |
| --- | --- | --- |
| `jupyter` | JupyterLab, to run the notebooks | `uv sync --extra jupyter` |
| `dev` | ruff and pytest | `uv sync --extra dev` |
| `docs` | Zensical, to build this site | `uv sync --extra docs` |

With pip: `pip install ".[jupyter]"`.
