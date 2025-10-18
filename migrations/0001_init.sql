-- ผู้ใช้ + ข้อมูลยืนยัน
create table if not exists users (
  guild_id      bigint not null,
  user_id       bigint not null,
  nickname      text,
  gender_raw    text,
  birthday      date,
  age_raw       text,
  sent_at       timestamptz,
  approved_at   timestamptz,
  rejected_at   timestamptz,
  last_msg_id   bigint,
  primary key (guild_id, user_id)
);

-- กันยิง HBD ซ้ำต่อวัน
create table if not exists hbd_sent (
  guild_id  bigint not null,
  user_id   bigint not null,
  date_utc  date   not null,
  primary key (guild_id, user_id, date_utc)
);

-- กันกดปุ่มซ้ำ / audit การตัดสินใจ
create table if not exists decisions (
  message_id bigint primary key,
  guild_id   bigint not null,
  user_id    bigint not null,  -- คนที่ถูกพิจารณา
  actor_id   bigint not null,  -- แอดมินที่กดปุ่ม
  decision   text   not null check (decision in ('approve','reject')),
  decided_at timestamptz not null default now()
);

-- ดัชนีช่วยค้น
create index if not exists idx_users_last_msg on users (guild_id, last_msg_id);
