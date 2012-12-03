ALTER SESSION ENABLE PARALLEL DML;

CREATE TABLE xtn2 (
    xtn_id CHAR(32) CONSTRAINT xtn2_xtn_id_nn NOT NULL,
    username VARCHAR2(65) CONSTRAINT xtn2_username_nn NOT NULL,
    command VARCHAR2(64) CONSTRAINT xtn2_command_nn NOT NULL,
    is_readonly NUMBER(*,0) CONSTRAINT xtn2_is_readonly_nn NOT NULL,
    start_time DATE CONSTRAINT xtn2_start_time_nn NOT NULL,
    CONSTRAINT xtn2_is_readonly CHECK (is_readonly IN (0, 1)),
    CONSTRAINT xtn2_pk PRIMARY KEY (xtn_id)
)
PARTITION BY RANGE (start_time)
(
   PARTITION xtn_2011_q2 VALUES LESS THAN (TO_DATE('01-07-2011', 'DD-MM-YYYY')),
   PARTITION xtn_2011_q3 VALUES LESS THAN (TO_DATE('01-10-2011', 'DD-MM-YYYY')),
   PARTITION xtn_2011_q4 VALUES LESS THAN (TO_DATE('01-01-2012', 'DD-MM-YYYY')),
   PARTITION xtn_2012_q1 VALUES LESS THAN (TO_DATE('01-04-2012', 'DD-MM-YYYY')),
   PARTITION xtn_2012_q2 VALUES LESS THAN (TO_DATE('01-07-2012', 'DD-MM-YYYY')),
   PARTITION xtn_2012_q3 VALUES LESS THAN (TO_DATE('01-10-2012', 'DD-MM-YYYY')),
   PARTITION xtn_2012_q4 VALUES LESS THAN (TO_DATE('01-01-2013', 'DD-MM-YYYY')),
   PARTITION xtn_2013_q1 VALUES LESS THAN (TO_DATE('01-04-2013', 'DD-MM-YYYY')),
   PARTITION xtn_2013_q2 VALUES LESS THAN (TO_DATE('01-07-2013', 'DD-MM-YYYY')),
   PARTITION xtn_2013_q3 VALUES LESS THAN (TO_DATE('01-10-2013', 'DD-MM-YYYY')),
   PARTITION xtn_2013_q4 VALUES LESS THAN (TO_DATE('01-01-2014', 'DD-MM-YYYY')),
   PARTITION xtn_2014_q1 VALUES LESS THAN (TO_DATE('01-04-2014', 'DD-MM-YYYY')),
   PARTITION xtn_2014_q2 VALUES LESS THAN (TO_DATE('01-07-2014', 'DD-MM-YYYY')),
   PARTITION xtn_2014_q3 VALUES LESS THAN (TO_DATE('01-10-2014', 'DD-MM-YYYY')),
   PARTITION xtn_2014_q4 VALUES LESS THAN (TO_DATE('01-01-2015', 'DD-MM-YYYY')),
   PARTITION xtn_2015_q1 VALUES LESS THAN (TO_DATE('01-04-2015', 'DD-MM-YYYY')),
   PARTITION xtn_2015_q2 VALUES LESS THAN (TO_DATE('01-07-2015', 'DD-MM-YYYY')),
   PARTITION xtn_2015_q3 VALUES LESS THAN (TO_DATE('01-10-2015', 'DD-MM-YYYY')),
   PARTITION xtn_2015_q4 VALUES LESS THAN (TO_DATE('01-01-2016', 'DD-MM-YYYY')),
   PARTITION xtn_2016_q1 VALUES LESS THAN (TO_DATE('01-04-2016', 'DD-MM-YYYY')),
   PARTITION xtn_2016_q2 VALUES LESS THAN (TO_DATE('01-07-2016', 'DD-MM-YYYY')),
   PARTITION xtn_2016_q3 VALUES LESS THAN (TO_DATE('01-10-2016', 'DD-MM-YYYY')),
   PARTITION xtn_2016_q4 VALUES LESS THAN (TO_DATE('01-01-2017', 'DD-MM-YYYY')),
   PARTITION xtn_2017_q1 VALUES LESS THAN (TO_DATE('01-04-2017', 'DD-MM-YYYY')),
   PARTITION xtn_2017_q2 VALUES LESS THAN (TO_DATE('01-07-2017', 'DD-MM-YYYY')),
   PARTITION xtn_2017_q3 VALUES LESS THAN (TO_DATE('01-10-2017', 'DD-MM-YYYY')),
   PARTITION xtn_2017_q4 VALUES LESS THAN (TO_DATE('01-01-2018', 'DD-MM-YYYY'))
) COMPRESS;

ALTER TABLE xtn2 DISABLE CONSTRAINT xtn2_pk;
ALTER TABLE xtn2 DISABLE CONSTRAINT xtn2_xtn_id_nn;
ALTER TABLE xtn2 DISABLE CONSTRAINT xtn2_username_nn;
ALTER TABLE xtn2 DISABLE CONSTRAINT xtn2_command_nn;
ALTER TABLE xtn2 DISABLE CONSTRAINT xtn2_is_readonly_nn;
ALTER TABLE xtn2 DISABLE CONSTRAINT xtn2_start_time_nn;
ALTER TABLE xtn2 DISABLE CONSTRAINT xtn2_is_readonly;

INSERT /*+ APPEND PARALLEL */ INTO xtn2 SELECT * FROM xtn;
COMMIT;

ALTER TABLE xtn2 ENABLE CONSTRAINT xtn2_xtn_id_nn;
ALTER TABLE xtn2 ENABLE CONSTRAINT xtn2_pk;
ALTER TABLE xtn2 ENABLE CONSTRAINT xtn2_username_nn;
ALTER TABLE xtn2 ENABLE CONSTRAINT xtn2_command_nn;
ALTER TABLE xtn2 ENABLE CONSTRAINT xtn2_is_readonly_nn;
ALTER TABLE xtn2 ENABLE CONSTRAINT xtn2_start_time_nn;
ALTER TABLE xtn2 ENABLE CONSTRAINT xtn2_is_readonly;

CREATE TABLE xtn2_detail (
    xtn_id CHAR(32) CONSTRAINT xtn2_detail_xtn_id_nn NOT NULL,
    name VARCHAR2(255) CONSTRAINT xtn2_detail_name_nn NOT NULL,
    value VARCHAR2(255) CONSTRAINT xtn2_detail_value_nn NOT NULL,
    CONSTRAINT xtn2_dtl_pk PRIMARY KEY (xtn_id, name, value),
    CONSTRAINT xtn2_dtl_xtn_fk FOREIGN KEY (xtn_id) REFERENCES xtn2 (xtn_id)
)
PARTITION BY REFERENCE (xtn2_dtl_xtn_fk) COMPRESS;

-- ALTER TABLE xtn2_detail DISABLE CONSTRAINT xtn2_dtl_xtn_fk;
ALTER TABLE xtn2_detail DISABLE CONSTRAINT xtn2_dtl_pk;
-- ALTER TABLE xtn2_detail DISABLE CONSTRAINT xtn2_detail_xtn_id_nn;
ALTER TABLE xtn2_detail DISABLE CONSTRAINT xtn2_detail_name_nn;
ALTER TABLE xtn2_detail DISABLE CONSTRAINT xtn2_detail_value_nn;

CREATE TABLE xtn2_end (
    xtn_id CHAR(32) CONSTRAINT xtn2_end_xtn_id_nn NOT NULL,
    return_code NUMBER(*,0) CONSTRAINT xtn2_end_return_code_nn NOT NULL,
    end_time DATE CONSTRAINT xtn2_end_end_time_nn NOT NULL,
    CONSTRAINT xtn2_end_pk PRIMARY KEY (xtn_id),
    CONSTRAINT xtn2_end_xtn_fk FOREIGN KEY (xtn_id) REFERENCES xtn2 (xtn_id)
)
PARTITION BY REFERENCE (xtn2_end_xtn_fk) COMPRESS;

-- ALTER TABLE xtn2_end DISABLE CONSTRAINT xtn2_end_xtn_fk;
ALTER TABLE xtn2_end DISABLE CONSTRAINT xtn2_end_pk;
-- ALTER TABLE xtn2_end DISABLE CONSTRAINT xtn2_end_xtn_id_nn;
ALTER TABLE xtn2_end DISABLE CONSTRAINT xtn2_end_return_code_nn;
ALTER TABLE xtn2_end DISABLE CONSTRAINT xtn2_end_end_time_nn;

QUIT;
