-- Attachments live in the database so the prototype needs no storage bucket
-- and no object permissions. A certificate is a few kilobytes of PDF.
create table if not exists files (
  id           uuid primary key default gen_random_uuid(),
  name         text not null,
  content_type text not null default 'application/pdf',
  data         bytea not null,
  created_at   timestamptz not null default now()
);

alter table coas add column if not exists file_id uuid references files(id);
alter table messages add column if not exists attachment_file_id uuid references files(id);
