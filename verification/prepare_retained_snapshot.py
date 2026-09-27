"""Prepare declarative metadata before exact-source review; never grant admission.

Run on the admission worker using the qualified project-local Litai interpreter
and the same coding-provider selection as rebuild. Existing application modules
are copied byte-for-byte into a new snapshot; the manifest recipe is updated,
requirements markers are resolved for the target, and current pre-build
SBOM/wheel-lock declarations are added. Package
hashes and aliases come from separately verified archive/installation reports.
The actual lifecycle must reverify target, archives and installed payloads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from literate_ai.adapters.dependencies import build_cyclonedx_bom
from literate_ai.adapters.dependencies.python_lock import (
    SCHEMA,
    parse_python_wheel_lock,
)
from literate_ai.adapters.generation_preparation import (
    FilesystemLockedGenerationApplicationAdapter,
    LockedComponentNodePreparationAdapter,
)
from literate_ai.adapters.standard_project import (
    FilesystemStandardProjectPlanningAdapter,
)
from literate_ai.adapters.models.coding_cli import (
    _recipe_authority_sbom,
    _require_recipe_authority_sbom,
)
from literate_ai.application.generation_preparation import GenerationPreparationRequest
from literate_ai.contracts import CycloneDxLifecycle, canonical_json_bytes
from literate_ai.generated_tests import validate_generated_test_suite
from literate_ai.projects import discover_project


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def prepare(
    project_root: Path, output: Path, target_report: Path, install_report: Path,
    flavor_selectors: tuple[str, ...] = (), target_profile: str = "host",
):
    project_root = project_root.resolve(strict=True)
    source = project_root / "desktop/source"
    output = output.absolute()
    if output.exists() or output.is_relative_to(source):
        raise ValueError("Snapshot must be a new directory outside retained source")
    project = discover_project(project_root)
    component = project_root / "components/desktop"
    prepared = FilesystemLockedGenerationApplicationAdapter().prepare(
        GenerationPreparationRequest(
            component, target_profile, project.flavor_selectors_for(component, flavor_selectors)
        )
    )
    # Standard rebuild projects a model-bound node recipe, not the standalone
    # preparation recipe. Use its own planner and projector, without generation.
    planning = FilesystemStandardProjectPlanningAdapter()
    snapshot = prepared.locked_authority_snapshot
    planned = planning.plan(snapshot)
    if len(planned.execution_plan.generation_plans) != 1:
        raise ValueError("Retained preparation requires exactly one Component")
    recipe = (
        LockedComponentNodePreparationAdapter(
            model_selector=planning.model_selector,
            coding_cli=planned.coding_cli.name,
        )
        .project(snapshot, planned.execution_plan.generation_plans[0])
        .recipe
    )
    target = json.loads(target_report.read_bytes())
    installed = json.loads(install_report.read_bytes())
    if (
        target["schema"] != "lertx/native-python-target-review@1"
        or installed["status"] != "pass"
    ):
        raise ValueError("Require successful independent target/package reports")
    fields = (
        "name",
        "version",
        "filename",
        "sha256",
        "requires_python",
        "requires_dist",
    )
    requirements = []
    for line in source.joinpath("requirements.txt").read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        requirement = Requirement(line)
        if requirement.marker is None or requirement.marker.evaluate(target["environment"]):
            requirement.marker = None
            requirement.name = canonicalize_name(requirement.name)
            requirements.append(str(requirement))
    requirements.sort()
    lock_value = {
        "schema": SCHEMA,
        "environment": target["environment"],
        "tags": target["tags"],
        "requirements": requirements,
        "packages": sorted(
            ({key: item[key] for key in fields} for item in installed["packages"]),
            key=lambda item: item["name"],
        ),
    }
    lock_bytes = encoded(lock_value)
    lock = parse_python_wheel_lock(lock_bytes.decode())
    lock.require_target(target["environment"], target["tags"])
    observations = {item["name"]: item for item in installed["components"]}
    packages = []
    for package in lock.packages:
        observed = observations[package.name]
        if observed["version"] != package.version:
            raise ValueError("Alias observation does not match the declared package")
        packages.append(
            {
                "type": "library",
                "bom-ref": f"pkg:pypi/{package.name}",
                "name": package.name,
                "version": package.version,
                "purl": f"pkg:pypi/{package.name}@{package.version}",
                "properties": [
                    item
                    for item in observed["properties"]
                    if item["name"]
                    in {
                        "literate-ai:dependency-kind",
                        "literate-ai:dependency-scope",
                        "literate-ai:python-top-level-import",
                    }
                ],
            }
        )
    graph = recipe.managed_sbom_graph
    authority, authority_edges = _recipe_authority_sbom(recipe)
    refs = {
        "@root": graph.root_ref,
        **{p.name: f"pkg:pypi/{p.name}" for p in lock.packages},
    }
    sbom, binding = build_cyclonedx_bom(
        lifecycle=CycloneDxLifecycle.SOURCE,
        managed_graph=graph,
        additional_components=(*authority, *packages),
        additional_edges=(
            *authority_edges,
            *((refs[a], refs[b]) for a, b in lock.edges),
        ),
    )
    _require_recipe_authority_sbom(sbom, recipe)
    from robot_asset_wheel import verify, FILENAME
    resource_root=source/"lertx/resources/so101"
    wheel=project_root/"desktop/wheels"/FILENAME
    verify(resource_root,wheel)
    asset_package=next(p for p in lock.packages if p.name=="lertx-robot-assets")
    if hashlib.sha256(wheel.read_bytes()).hexdigest()!=asset_package.sha256:
        raise ValueError("Asset wheel does not match verified dependency closure")
    original = {}
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ValueError("Source links are not eligible for copying")
        if path.is_relative_to(resource_root):continue
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.is_file():
            data = path.read_bytes()
            data.decode("utf-8")
            original[path.relative_to(source).as_posix()] = data
    files = dict(original)
    files["requirements.txt"] = ("\n".join(requirements) + "\n").encode()
    manifest = json.loads(files["tests/manifest.json"])
    previous_recipe = manifest["recipe_identity"]
    manifest["recipe_identity"] = recipe.identity
    files["tests/manifest.json"] = canonical_json_bytes(manifest)
    suite = validate_generated_test_suite(
        files["tests/manifest.json"],
        recipe_identity=recipe.identity,
        specification_references=recipe.non_acceptance_document_paths,
    )
    files["python-wheel-lock.json"] = lock_bytes
    files[".literate/sbom.cdx.json"] = sbom
    output.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(data)
    for name, data in original.items():
        if source.joinpath(name).read_bytes() != data:
            raise ValueError("Source changed during snapshot preparation")
    verify(resource_root,wheel)
    if hashlib.sha256(wheel.read_bytes()).hexdigest()!=asset_package.sha256:
        raise ValueError("Asset wheel changed during snapshot preparation")
    return {
        "schema": "lertx/retained-snapshot-preparation@1",
        "admitted": False,
        "externalized_resources": {"path":"lertx/resources/so101","wheel_sha256":asset_package.sha256},
        "recipe_identity": recipe.identity,
        "coding_provider": planned.coding_cli.name,
        "previous_recipe_identity": previous_recipe,
        "original_files": len(original),
        "snapshot_files": len(files),
        "preserved_files": sum(files[name] == data for name, data in original.items()),
        "test_cases": len(suite.cases),
        "metadata_changes": [
            "requirements.txt",
            "tests/manifest.json",
            "python-wheel-lock.json",
            ".literate/sbom.cdx.json",
        ],
        "source_sbom": binding.to_dict(),
        "files": {
            name: hashlib.sha256(data).hexdigest()
            for name, data in sorted(files.items())
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--installation", type=Path, required=True)
    parser.add_argument("--flavor", action="append", default=[])
    parser.add_argument("--profile", default="host")
    args = parser.parse_args()
    print(
        json.dumps(
            prepare(args.project, args.output, args.target, args.installation,
                    tuple(args.flavor), args.profile), indent=2
        )
    )
