"""Read-only framework diagnostic using its existing tiny wheel fixture.

Run with the parent's Make-managed interpreter, src/tests on PYTHONPATH, and
LITAI_TEST_PIP_WHEEL set to its pinned installer. Writes only fixture-owned
temporary directories. Does not patch framework code or grant acceptance.
"""

import json
from types import SimpleNamespace

from literate_ai.adapters.lifecycle import LocalStandardLifecycleError
from literate_ai.adapters.lifecycle.standard_local import local_tree_identity
from literate_ai.application.artifact_graph import (
    create_artifact_build_graph,
    realize_manifest,
)
from tests.unit.test_standard_python_lifecycle import StandardPythonLifecycleTests


def main():
    StandardPythonLifecycleTests.setUpClass()
    fixture = StandardPythonLifecycleTests()
    try:
        fixture.setUp()
        output = fixture.build()
        ports = fixture.ports
        before = local_tree_identity(fixture.artifact)
        ports.test(fixture.plan, output.exports)
        ports.execute(fixture.plan, output.exports)
        manifest = realize_manifest(fixture.plan.manifest, output.exports)
        graph = create_artifact_build_graph(
            build_system_driver_identity=manifest.build_system_driver_identity,
            manifests=(manifest,),
            link_roots=(output.exports[0].identity,),
        )
        plan, result = ports.create_project_package(
            fixture.snapshot.authority.lock,
            fixture.execution,
            SimpleNamespace(),
            graph,
            graph.link_plans[0],
        )
        custody = ports.project_package_custody(plan, result)
        packaged_root = custody.artifact_paths[output.exports[0].identity.uri].parent
        report = {
            "schema": "lertx/python-package-custody-diagnostic@1",
            "component_test_and_execute": "passed",
            "original_artifact_unchanged": (
                local_tree_identity(fixture.artifact) == before
            ),
            "packaged_dependency_runtime_present": (
                packaged_root / "python-runtime"
            ).exists(),
            "packaged_dependency_manifest_present": (
                packaged_root / "python-dependencies.json"
            ).exists(),
            "packaged_execution_seal_registered": (
                str(packaged_root.resolve()) in ports._python_execution_trees
            ),
        }
        try:
            ports.test_root_integration(
                fixture.snapshot.authority.lock,
                fixture.execution,
                SimpleNamespace(),
                plan,
                result,
            )
        except LocalStandardLifecycleError as error:
            report["packaged_root_integration_error"] = str(error)
        print(json.dumps(report, indent=2))
    finally:
        fixture.doCleanups()


if __name__ == "__main__":
    main()
