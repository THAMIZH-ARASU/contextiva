from uuid import uuid4
import pytest

from src.domain.models.project import Project


def test_project_valid_minimal():
    owner_id = uuid4()
    p = Project(name="MyProject", owner_id=owner_id)
    assert p.name == "MyProject"
    assert p.owner_id == owner_id
    assert p.status == "Active"
    assert p.id is not None


@pytest.mark.parametrize("bad_name", ["", "   ", None])
def test_project_invalid_name(bad_name):
    with pytest.raises(ValueError):
        Project(name=bad_name, owner_id=uuid4())  # type: ignore[arg-type]


def test_project_invalid_status():
    with pytest.raises(ValueError):
        Project(name="X", owner_id=uuid4(), status="INVALID")


def test_project_tags_validation():
    owner_id = uuid4()
    Project(name="ok", owner_id=owner_id, tags=["alpha", "beta_1", "Tag-2"])  # ok
    Project(name="ok", owner_id=owner_id, tags=None)  # ok
    Project(name="ok", owner_id=owner_id, tags=[])  # ok
    with pytest.raises(ValueError):
        Project(name="ok", owner_id=owner_id, tags=["bad tag with space"])  # invalid chars

