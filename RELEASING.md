# Releasing

Releases start by pushing a version tag. The workflow builds all packages, attaches them to a draft GitHub release, publishes both packages to PyPI, and publishes the GitHub release last. Do not publish a GitHub release manually. Once published, its tag and attachments are immutable.

## Prepare the release

Open a release PR that updates:

- `packages/conda-completer/pyproject.toml` and `packages/conda-completer/Cargo.toml` to the new version, with `Cargo.lock` updated accordingly.
- The minimum `conda-completer` version in the root `pyproject.toml`, then regenerate `pixi.lock` with `pixi lock`.
- The version in `recipe/recipe.yaml`.
- `CHANGELOG.md` and `docs/changelog.md`, including any upgrade instructions.

`conda-completion` derives its version from the Git tag. Both packages use the same release version.

Run `pixi run test` and `pixi run check`. Packaging and release workflow changes also build and check all eight package files in PR checks. These checks do not create releases or publish packages.

Merge the release PR after its checks pass. Fetch `main`, fast-forward the local branch, and wait for checks on the merged commit to pass. Create and push an annotated tag on that commit, using a bare version such as `0.3.2`:

```bash
git tag -a 0.3.2 -m "Release 0.3.2"
git push origin 0.3.2
```

## Follow publication

The `Release` workflow runs these stages in order:

1. Build five platform wheels and a source archive for `conda-completer`, plus a wheel and source archive for `conda-completion`.
2. Check the package metadata and confirm that all eight filenames match the release version.
3. Create a draft GitHub release and attach all eight files.
4. Publish `conda-completer`, then `conda-completion`, through their existing PyPI trusted publishers.
5. Publish the GitHub release, making the tag and attachments immutable.

The PyPI trusted publishers use `.github/workflows/release.yml` and the `pypi-completer` and `pypi-completion` GitHub environments. The workflow needs no PyPI API token.

Wait for the entire workflow to succeed. Check that both PyPI projects contain the new version and that the GitHub release has eight package attachments. Verify the release with `gh release verify VERSION` and compare the downloaded files with the PyPI files before calling the release complete. Edit the release notes to include the reviewed changelog and upgrade instructions.

## Retry a failed release

Use **Re-run failed jobs** on the original workflow run. This reuses its original build artifacts.

- A build or metadata failure prevents draft creation and publication.
- An attachment failure removes the draft created by that job and prevents both PyPI uploads.
- A PyPI failure leaves the fully populated GitHub release as a draft. Retrying skips files already on PyPI and uploads the remaining original files.
- If the final GitHub publication job fails, check the release state and retry that job if it is still a draft.

Do not rerun all jobs after an upload has started, overwrite draft attachments, move a release tag, or rebuild a version that has already reached PyPI. A complete rerun stops if the draft already exists. If the source or package contents must change, prepare a new version.
