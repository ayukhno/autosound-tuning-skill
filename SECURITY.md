# Security Policy

If you discover a security vulnerability in this repository, thank you for responsibly
reporting it so we can address it quickly.

## How to report

Use GitHub Security Advisories (private vulnerability reporting):
https://github.com/ayukhno/autosound-tuning-skill/security/advisories/new

Include: affected file(s), reproduction steps, severity, proof-of-concept (if safe),
and any suggested remediation. This channel lets maintainers coordinate a fix and
a coordinated disclosure privately.

## How we handle reports

- We acknowledge receipt within 3 business days.
- We triage and communicate a timeline for remediation.
- We coordinate disclosure timing and provide credit in the repository unless you request anonymity.

Do not publish vulnerability details publicly until a fix or coordinated disclosure is agreed.

## Signed releases

From `v3.0.64` every release tag is signed with the author's SSH key, and the installers (`install.sh`,
`install.ps1`) and the update path TCC calls (`scripts/upkeep.py clone`) refuse to install a release tag that does
not verify against it. Older tags predate signing and still install; the installer says so. The desktop app's tags
are signed with the same key from TCC `v0.1.45`, and the installers check the app's tag the same way before `uv`
installs it: one that does not verify is not installed, and the method's install goes on without it. The key:

- fingerprint `SHA256:nSazijzZf///QKgfVXJBRd2fl7QMd2Xu4uwjc7MGbSo` (ED25519)
- in [`allowed_signers`](allowed_signers), so anyone can check a tag by hand -- the good answer is the line that
  starts `Good "git" signature for ayukhno with`:
  `git -c gpg.ssh.program=ssh-keygen -c gpg.ssh.allowedSignersFile=allowed_signers verify-tag v3.0.64`

The installers carry the same key as a constant rather than reading this repository's file, so a tag cannot vouch
for itself. All three checks accept the author's SSH signature only, whatever the person's git or GPG configuration
says: git's success and that one line, nothing else. They name `ssh-keygen` for the check, so a signing helper set as
`gpg.ssh.program` (1Password's, for one) does not do the verifying; and a tag signed with an OpenPGP key is refused
even when the person's own keyring vouches for it -- git picks the verifier from the signature, and says "Good" for
that one too. `AUTOSOUND_SKIP_TAG_VERIFY=1` turns the check off for one run and says so in the log; it exists for
development and is never needed to install a release.

## Encrypted reports

If you prefer to send an encrypted report, request contact instructions via a GitHub
Security Advisory and we will provide them.
