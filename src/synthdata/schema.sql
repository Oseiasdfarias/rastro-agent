CREATE TABLE IF NOT EXISTS kna1 (kunnr text PRIMARY KEY, name1 text, ort01 text);
CREATE TABLE IF NOT EXISTS mara (matnr text PRIMARY KEY, maktx text, mtart text);
CREATE TABLE IF NOT EXISTS equi (equnr text PRIMARY KEY, eqktx text, arbpl text UNIQUE);
CREATE TABLE IF NOT EXISTS afko (aufnr text PRIMARY KEY, matnr text, arbpl text,
                                 gstrp timestamp, gltrp timestamp);
CREATE TABLE IF NOT EXISTS afpo (aufnr text, posnr text, charg text UNIQUE, matnr text,
                                 psmng int, PRIMARY KEY (aufnr, posnr));
CREATE TABLE IF NOT EXISTS vbak (vbeln text PRIMARY KEY, kunnr text, erdat date);
CREATE TABLE IF NOT EXISTS vbap (vbeln text, posnr text, matnr text, kwmeng int,
                                 PRIMARY KEY (vbeln, posnr));
CREATE TABLE IF NOT EXISTS likp (vbeln text PRIMARY KEY, kunnr text, wadat_ist date, vgbel text);
CREATE TABLE IF NOT EXISTS lips (vbeln text, posnr text, matnr text, charg text, lfimg int,
                                 PRIMARY KEY (vbeln, posnr));
CREATE TABLE IF NOT EXISTS qmel (qmnum text PRIMARY KEY, qmart text, equnr text, qmdat date,
                                 qmtxt text);
CREATE TABLE IF NOT EXISTS aufk (aufnr text PRIMARY KEY, auart text, equnr text, erdat date,
                                 ktext text);
CREATE TABLE IF NOT EXISTS crm_account (account_id text PRIMARY KEY, kunnr text, name text);
CREATE TABLE IF NOT EXISTS crm_case (case_id text PRIMARY KEY, account_id text, created_on date,
                                     matnr text, vbeln text, text text);
CREATE TABLE IF NOT EXISTS eval_truth (case_id text PRIMARY KEY, verdict text, equnr text,
                                       failure_mode text, window_start date, window_end date,
                                       vbeln text);
CREATE INDEX IF NOT EXISTS lips_charg ON lips (charg);
CREATE INDEX IF NOT EXISTS likp_kunnr ON likp (kunnr, wadat_ist);
CREATE INDEX IF NOT EXISTS qmel_equnr ON qmel (equnr, qmdat);
CREATE INDEX IF NOT EXISTS aufk_equnr ON aufk (equnr, erdat);
