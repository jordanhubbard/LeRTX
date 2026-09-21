# Merged Python package custody qualification

The operator authorized adopting the merged fix and retrying LeRTX admission.
Qualification targets upstream PR #477, revision
`aa3a58689fa5b1c585dd532939ef1869ab6bea20`, which includes the package custody
fix from PR #474 and corrects its failing provider-role test fixture.
The original qualified build and application source are preserved.

## Reviewed implementation

The packager now includes the non-export Python artifact resources, including
the installed dependency runtime and manifest, as explicit package inputs.
It rejects links, checks the original artifact seal before and after resource
capture, verifies the copied artifact identity, and observes copied dependency
custody. Packaged execution registers a relocated seal only after checking that
tree and its dependency observer. The strict sealed-artifact validator remains
in force. No project-local production patch or review-pin override was made.

## Evidence

- The merge tree and CI head `4a817054c79a7f95a932a7a4651e2ae948549061`
  both have tree identity `dab80e2fdfd03815f93c0bb7f4946eb1759fc6fe`.
- [Upstream CI run 35324091520](https://github.com/NVIDIA-dev/literate-ai/actions/runs/35324091520)
  completed successfully: all 19 checks, including Linux, macOS, and Windows
  test matrices, installed-wheel checks, and native C++ checks.
- Local `make driver-review documentation-review` passes with current pins:
  driver `sha256:ca71879981eb2b2d62d2706c481a00ab24fbafb7e5d037828d5cd81b3f4a60be`;
  documentation `sha256:d664c5f7957b7374e88dee3678fadc60dfaf18b611112d9ed3399cf17460ecd2`.
- All 11 local `test_standard_python_lifecycle.py` tests pass in 37.525 seconds,
  including relocated-package execution and artifact mutation rejection.
- Local lint, formatting (1,250 files), and repository layout checks pass.
- Installed-wheel qualification passes (exit 0), including clean-install
  reproducibility, tamper rejection, project initialization/update, and source
  admission lifecycle checks. Retained manifest:
  `parents/literate-ai/_build/ci-wheels/run-5clmzrgw/manifest.json`.
  Wheel: `sha256:17842314aa2f513483175e85610372b06c7222c63812203533fe40410509aaeb`
  (3,040,428 bytes). Installed distribution:
  `sha256:b616288d5bfd067566a5d36633a501c6f4d1913805735fb01cc3408982099433`
  (943 members). Full output is retained in parent evidence run
  `20260919T011852Z-c235cb/n0001/stdout.log`.
  The identical distribution and all 943 members were independently observed on
  the Linux admission host. Both isolated installations pass `pip check`.

Local commands use Make-managed environment key `qualify-473`. Broad-suite
qualification above is exact-tree upstream CI, not a new full local suite run.
The superseded native-SDK test run on the earlier PR #474 tree was interrupted
before checkout advanced; it is not passing evidence.

## Applied binding review

Supported plan `package-standard-rebind-plan.json`, identity
`sha256:58fcb84935cfe912cdd1f12ed565bafd683f3bbdb7c5b5b68821ab1740be5aa6`,
changes only the framework distribution and receipt runner binding. Policy,
required evidence kinds, suite version, and minimum test count are unchanged.
The installed wheel truthfully retains the checkout's historical GitLab origin
metadata; the qualified revision/tree was fetched and checked against the
user-designated GitHub upstream. No origin metadata was rewritten.

The supported apply command succeeded. The new project configuration identity is
`sha256:941d44a4fae2c8f34183e182671d2c41817d7d09546671c76363bdd41eff8be1`.
Supported documentation review records authority
`sha256:bd192a44aabf6311ba6372794be90de94837fedf962963d5ac865af27bac6831`.
The CLI is `_build/local-litai-package-aa3a5868/venv/bin/litai`.
Application admission was attempted and remains blocked by the separate
256-artifact directory-package limit. See `package-file-count-blocker.md`.
The old receipt is not current evidence for this binding.

## Boundaries

Linux staging uses a fresh persistent-disk workspace, avoiding the 80%-full
RAM-backed `/tmp`. Existing application processes and environments are preserved.
No global installation, physical actuation, or Windows package install is included.
Application acceptance must pass independently; framework CI alone cannot admit
the desktop source or prove cold-start rendering reliability.

The subsequent full native suite completes with 156/157 passing in 212.590
seconds; the existing-scene fresh-process CLI case fails to deliver a frame.
Its trace shows renderer destruction during scene opening. No warm rerun was
substituted for this failure. Detailed outcome:
`native/linux/package-adoption-regression.json`. Authority and locks still pass;
the receipt gate correctly fails as stale. No framework production code was
changed to address the newly discovered package-count blocker.
