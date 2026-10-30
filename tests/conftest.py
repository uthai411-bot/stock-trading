import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tfexflow.config import DEFAULT  # noqa: E402
from tfexflow.data import synthetic  # noqa: E402
from tfexflow.data.loaders import load  # noqa: E402
from tfexflow.features import build_features  # noqa: E402


@pytest.fixture(scope="session")
def sample_dir(tmp_path_factory):
    return synthetic.write(tmp_path_factory.mktemp("sample"), years=3, seed=7, flow_effect=0.0015)


@pytest.fixture(scope="session")
def feats(sample_dir):
    return build_features(load(sample_dir), DEFAULT.features)
