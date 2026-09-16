# Backend

## Organization Guide Storage

Organization permission guides are runtime Markdown files, not source-code files. Set `ORGANIZATION_GUIDE_STORAGE_PATH` to a persistent storage volume when deploying the backend. If it is not set, local development uses:

```text
~/.catalyst/organization-guides
```

The database stores guide metadata and a storage-relative file key. The platform-admin guide page selects organizations from the organizations table before saving a guide.
