from uuid import uuid4
import pytest

from src.domain.models.project import Project


def test_project_valid_minimal():
    p = Project(name="MyProject")
    assert p.name == "MyProject"
    assert p.status == "Active"
    assert p.id is not None


@pytest.mark.parametrize("bad_name", ["", "   ", None])
def test_project_invalid_name(bad_name):
    with pytest.raises(ValueError):
        Project(name=bad_name)  # type: ignore[arg-type]


def test_project_invalid_status():
    with pytest.raises(ValueError):
        Project(name="X", status="INVALID")


def test_project_tags_validation():
    Project(name="ok", tags=["alpha", "beta_1", "Tag-2"])  # ok
    Project(name="ok", tags=None)  # ok
    Project(name="ok", tags=[])  # ok
    with pytest.raises(ValueError):
        Project(name="ok", tags=["bad tag with space"])  # invalid chars


