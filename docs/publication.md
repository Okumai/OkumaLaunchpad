# Source publication and local testing

This repository contains no GitHub Actions workflows. GitHub is used to host source
code; clone or pull it onto a separate device and run tests locally. Git push and
pull do not require Actions, and the plugin does not require Actions to run.

## Local checks

Run from the repository root on your test device:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q .
python3 -m json.tool manifest.json > /dev/null
python3 -m json.tool examples/plugin-settings.json > /dev/null
omarchy plugin validate .
```

Portable tests do not replace desktop/QML loading or real hardware testing. Review
source before running any installer: plugins run unsandboxed as your user. See
CONTRIBUTING.md for the manual desktop checklist.

## Before uploading

- In repository Settings > Actions > General, select Disable actions. This also
  prevents workflows left on older branches or tags from running in this repository.
  Removing workflow files from this checkout alone does not remove other refs or
  cancel runs already queued or in progress; review and cancel those separately.
- Upload the workflow deletions as part of the same commit if the remote repository
  already contains them. Other devices must pull that commit to receive the changes.
- Review the actual diff, and scan both the working tree and Git history for secrets.
  Never upload private settings or unreviewed diagnostics. Revoke/rotate previously
  exposed credentials at their issuer; deleting stored copies does not revoke them.
- Confirm that GitHub permits the account and repository to use the platform. Changes
  to code, IDs, repository names, or CI do not resolve an account suspension. Do not
  use another account or repository to bypass restrictions; contact GitHub Support.
- Marketplace submissions can still trigger automation in a third-party repository.
  This project does not automate submissions. Follow the maintainers' process, avoid
  duplicate submissions/retries, and review the submission requirements.

Disabling Actions does not disable GitHub Apps, webhooks, or third-party services.
Review those integrations separately if configured. This source-only setup reduces
Actions-related exposure, but is not a guarantee against account restrictions or
other policy violations.

## References

- https://docs.github.com/en/actions/administering-github-actions/usage-limits-billing-and-administration/disabling-or-limiting-github-actions-for-a-repository
- https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies
- https://docs.github.com/en/site-policy/acceptable-use-policies/github-appeal-and-reinstatement
