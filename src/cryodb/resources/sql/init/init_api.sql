BEGIN;

------------------------------------------------------------------------------
-- Create database management table
------------------------------------------------------------------------------
CREATE TABLE api_keys (
    key_id          INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT DEFAULT NULL, -- alias for row_id in sqlite3
    name            TEXT UNIQUE, -- identifier or username
    type            TEXT NOT NULL, -- admin, user, service or IP
    hash            TEXT NOT NULL, -- private key value
    email           TEXT NOT NULL, -- user
    ip              TEXT, -- IP address if type is IP
    created         TEXT, -- timestamp
    last_accessed   TEXT  -- timestamp
);

CREATE TABLE api_key_permissions (
    key_id      INTEGER UNSIGNED NOT NULL,
    can_select  TINYINT NOT NULL DEFAULT 0,
    can_insert  TINYINT NOT NULL DEFAULT 0,
    can_update  TINYINT NOT NULL DEFAULT 0,
    campaign_id INTEGER UNSIGNED NOT NULL,
    -- assign foreign keys
    FOREIGN KEY (key_id) REFERENCES api_keys(key_id),
    FOREIGN KEY (campaign_id) REFERENCES campaign_table(campaign_id)
);

ALTER TABLE `api_key_permissions` ADD CONSTRAINT `api_key_permissions` UNIQUE(`key_id`, `campaign_id`);

COMMIT;