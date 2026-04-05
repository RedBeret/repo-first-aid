# Research Notes

`repo-first-aid` focuses on the part of repo quality most public checklists skip: the trust signals somebody sees in the first minute on GitHub.

## Primary references

- GitHub repository security quickstart:
  - <https://docs.github.com/en/code-security/getting-started/quickstart-for-securing-your-repository>
  - Used to ground checks around `SECURITY.md`, dependency-aware repo hygiene, and public trust expectations.
- GitHub issue and pull request templates:
  - <https://docs.github.com/en/enterprise-server%403.15/communities/using-templates-to-encourage-useful-issues-and-pull-requests>
  - Used to ground the issue-template and PR-template checks.
- GitHub licensing docs:
  - <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository>
  - Used to ground `LICENSE` checks.

## Practical rule philosophy

The project does not try to be a generic static analyzer. It focuses on the public-facing pain points that make a repo feel unfinished:

- missing community-health files
- starter/template residue
- screenshots missing from UI repos
- deployment docs that do not match actual project setup
- test commands without tests
- tracked junk that makes the repo look messy

Those checks are intentionally opinionated because they are aimed at GitHub discoverability and public trust, not just local correctness.
