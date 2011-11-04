CREATE TABLE srv_record (
	dns_record_id INTEGER CONSTRAINT "SRV_RECORD_DNS_RECORD_ID_NN" NOT NULL,
	priority INTEGER CONSTRAINT "SRV_RECORD_PRIORITY_NN" NOT NULL,
	weight INTEGER CONSTRAINT "SRV_RECORD_WEIGHT_NN" NOT NULL,
	port INTEGER CONSTRAINT "SRV_RECORD_PORT_NN" NOT NULL,
	target_id INTEGER CONSTRAINT "SRV_RECORD_TARGET_ID_NN" NOT NULL,
	CONSTRAINT "SRV_RECORD_PK" PRIMARY KEY (dns_record_id),
	CONSTRAINT "SRV_RECORD_DNS_RECORD_FK" FOREIGN KEY (dns_record_id) REFERENCES dns_record (id) ON DELETE CASCADE,
	CONSTRAINT "SRV_RECORD_TARGET_FK" FOREIGN KEY (target_id) REFERENCES fqdn (id)
);

QUIT;