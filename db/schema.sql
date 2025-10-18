-- See canvas spec; same DDL
CREATE TABLE IF NOT EXISTS members (
  guild_id        BIGINT NOT NULL,
  user_id         BIGINT NOT NULL,
  nickname        TEXT,
  age_text        TEXT,
  gender_text     TEXT,
  birthday_text   TEXT,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS verification_requests (
  id               BIGSERIAL PRIMARY KEY,
  guild_id         BIGINT NOT NULL,
  user_id          BIGINT NOT NULL,
  message_id       BIGINT,
  channel_id       BIGINT,
  nickname         TEXT,
  age_text         TEXT,
  gender_text      TEXT,
  birthday_text    TEXT,
  account_age_days INT,
  account_risk     TEXT,
  sent_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  status           TEXT NOT NULL DEFAULT 'SUBMITTED',
  decided_by       BIGINT,
  decided_at       TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS vr_guild_user_idx ON verification_requests(guild_id, user_id, id DESC);
CREATE INDEX IF NOT EXISTS vr_msg_idx ON verification_requests(guild_id, message_id);

CREATE TABLE IF NOT EXISTS approval_index (
  guild_id   BIGINT NOT NULL,
  user_id    BIGINT NOT NULL,
  message_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS age_refresh_runs (
  guild_id BIGINT NOT NULL,
  tag      TEXT   NOT NULL,
  ran_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (guild_id, tag)
);

CREATE TABLE IF NOT EXISTS hbd_sent (
  guild_id   BIGINT NOT NULL,
  user_id    BIGINT NOT NULL,
  date_local DATE NOT NULL,
  message_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (guild_id, user_id, date_local)
);

CREATE TABLE IF NOT EXISTS age_role_changes (
  id        BIGSERIAL PRIMARY KEY,
  guild_id  BIGINT NOT NULL,
  user_id   BIGINT NOT NULL,
  old_role  BIGINT,
  new_role  BIGINT,
  reason    TEXT,
  at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
