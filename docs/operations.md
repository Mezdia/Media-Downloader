# Operations: Hidden Group Cache

This bot stores canonical cached videos in `GROUP_CHAT_ID` and serves users using `copyMessage` or `file_id` sends (no forwarded header).

## 1) Verify cache group health

- Confirm bot is a member of `GROUP_CHAT_ID`.
- Confirm bot has permission to send media in that group.
- If cache upload fails, bot sets cache disabled (`cache_enabled=0`) and logs an admin error.

## 2) Inspect cache entries

### Option A: Admin command (recommended)

- Add item manually:
  - `/admin_cache_add <youtube_id> <quality> <group_message_id> <file_id> <size_bytes> [group_chat_id]`
- Remove item:
  - `/admin_cache_remove <youtube_id> <quality>`

### Option B: SQLite query

```sql
SELECT youtube_id, quality, group_chat_id, group_message_id, file_id, filesize_bytes, uploaded_at
FROM cache
ORDER BY uploaded_at DESC;
```

## 3) Clear a single cached item

- Admin command:
  - `/admin_cache_remove <youtube_id> <quality>`

Or SQL:

```sql
DELETE FROM cache WHERE youtube_id = 'VIDEO_ID' AND quality = 720;
```

## 4) Re-enable cache after fixing group permissions

- Set group again:
  - `/admin_set_group -1001234567890`

This re-enables cache for subsequent uploads.

## 5) Force-copy cached item to any chat

- `/admin_force_copy <youtube_id> <quality> <target_chat_id>`

## 6) Inspect rolling quota usage

- `/admin_usage <user_id>`
- `/admin_reset_usage <user_id>`

24h rolling usage is derived from `usage_events`.

SQL example:

```sql
SELECT user_id, SUM(bytes) AS used_bytes
FROM usage_events
WHERE created_at >= datetime('now', '-24 hours')
GROUP BY user_id;
```

## 7) Data retention and cleanup

- Downloaded files are temporary and removed after processing.
- Empty per-job download folders are pruned automatically.
- Database file location is configured via `DATABASE_URI`.