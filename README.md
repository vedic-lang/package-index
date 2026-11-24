# Vedic package index

Install a registered library by its short name, for example `vedic install ganita`. The CLI reads the index from this repository's `main` branch. Each stable version identifies one exact Git commit in a public GitHub repository. Projects record their versions in `vedic.toml`.

## Publish a library

1. Give your Vedic library a lowercase name starting with a letter. Use letters, digits and hyphens, up to 64 characters.
2. Commit a root `lib.ved` and a root `vedic.toml` to your public GitHub repository. Set `[package].name` to the index name and `[package].version` to a stable version such as `0.1.0`. Put any dependencies under `[dependencies]` using their index names and exact versions.
3. Choose a commit that will remain available from your repository, for example one reachable from a release tag. Copy its full SHA with `git rev-parse HEAD`.
4. Open a pull request adding `packages/<name>.toml` to this index. Set `repository` to your GitHub owner and repository and add the version and its lowercase 40-character SHA under `[releases]`. See [the Ganita entry](packages/ganita.toml).
5. For each subsequent release, open a PR adding a new version to the same table. Existing versions retain their original commit. The CLI selects the highest indexed stable version on an explicit install.

Reviewers should check repository ownership and inspect the Vedic source at the proposed commit. CI checks manifest identity, the entry point, dependency versions and the immutability of previously indexed releases. The package becomes available when the index PR merges.

## Try an installed package

```vedic
आवाहन "pkg:ganita";
वद(वर्ग(७));
```

Ganita prints `४९` in this example. Package installation requires a Vedic CLI with the `install` command.
