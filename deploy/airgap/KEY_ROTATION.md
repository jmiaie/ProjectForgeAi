# GPG key rotation for air-gapped bundles

Runbook for rotating ProjectForge release signing keys without breaking offline verification.

## When to rotate

- Scheduled rotation (recommended annually)
- Private key compromise or personnel change
- Compliance audit requirement

## Prerequisites

- Access to current and new GPG keypairs on the connected build machine
- `gpg` installed on build and target air-gapped hosts
- Change window coordinated with operations

## Rotation steps

### 1. Generate or designate the new key

```bash
gpg --full-generate-key
# note the new key id / email
```

### 2. Export and publish the new public key

```bash
python3 scripts/rotate_airgap_gpg_key.py \
  --new-key-id release@projectforge.internal \
  --old-key-id previous@projectforge.internal \
  --notes "Scheduled 2026 rotation"
```

This writes:

- `deploy/airgap/keys/release.pub.asc` — distribute to air-gapped hosts
- `deploy/airgap/keys/rotation.json` — rotation audit manifest

### 3. Import on air-gapped targets

```bash
gpg --import deploy/airgap/keys/release.pub.asc
# update env
AIRGAP_GPG_PUBLIC_KEY_PATH=deploy/airgap/keys/release.pub.asc
```

### 4. Re-sign pending bundles

```bash
python3 scripts/build_airgap_bundle.py --version 14.1.0 --sign-key-id release@projectforge.internal
```

Or sign an existing archive:

```bash
python3 scripts/sign_airgap_bundle.py dist/airgap/projectforge-airgap-14.1.0-abc.tar.gz \
  --key-id release@projectforge.internal
```

### 5. Verify before apply

```bash
python3 scripts/apply_airgap_bundle.py dist/airgap/projectforge-airgap-14.1.0-abc.tar.gz \
  --public-key deploy/airgap/keys/release.pub.asc \
  --require-signature
```

### 6. Retire the old key

Keep the previous public key available for historical bundle verification until all environments are upgraded. Document retirement date in `rotation.json`.

## Dual-key verification window

During migration, import **both** public keys on air-gapped hosts. Bundles signed with either key will verify until the old key is removed.

## Production enforcement

Set in on-prem / Helm env:

```env
AIRGAP_REQUIRE_SIGNATURE=true
AIRGAP_GPG_PUBLIC_KEY_PATH=/opt/projectforge/keys/release.pub.asc
```

Check enforcement via `GET /api/v1/deploy/status`.

## Rollback

If a new key causes verification failures:

1. Re-import the previous public key
2. Point `AIRGAP_GPG_PUBLIC_KEY_PATH` back to the old key file
3. Apply bundles signed with the old key
4. Record incident in `rotation.json` notes
