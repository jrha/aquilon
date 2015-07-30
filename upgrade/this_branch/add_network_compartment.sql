CREATE SEQUENCE network_compartment_id_seq;
CREATE TABLE network_compartment (
	id INTEGER CONSTRAINT "NET_COMP_ID_NN" NOT NULL,
	name VARCHAR2(64 CHAR) CONSTRAINT "NET_COMP_NAME_NN" NOT NULL,
	creation_date DATE CONSTRAINT "NET_COMP_CR_DATE_NN" NOT NULL,
	comments VARCHAR(255 CHAR),
	CONSTRAINT "NETWORK_COMPARTMENT_PK" PRIMARY KEY (id),
	CONSTRAINT "NET_COMP_NAME_UK" UNIQUE (name)
);

QUIT;
