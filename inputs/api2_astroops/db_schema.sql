-- Auto-exported from astroops.db

CREATE TABLE maneuvers (
	id INTEGER NOT NULL, 
	satellite_id INTEGER NOT NULL, 
	delta_v FLOAT NOT NULL, 
	direction VARCHAR NOT NULL, 
	scheduled_start DATETIME NOT NULL, 
	scheduled_end DATETIME NOT NULL, 
	status VARCHAR NOT NULL, 
	authorized_by VARCHAR, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(satellite_id) REFERENCES satellites (id)
);

CREATE TABLE payloads (
	id INTEGER NOT NULL, 
	satellite_id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	type VARCHAR NOT NULL, 
	power_draw FLOAT NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	data_format VARCHAR NOT NULL, 
	is_sensitive BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(satellite_id) REFERENCES satellites (id)
);

CREATE TABLE satellites (
	id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	orbit_type VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	power_capacity FLOAT NOT NULL, 
	current_power FLOAT NOT NULL, 
	in_signal BOOLEAN NOT NULL, 
	next_window_start DATETIME, 
	download_count INTEGER NOT NULL, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE telemetry (
	id INTEGER NOT NULL, 
	satellite_id INTEGER NOT NULL, 
	timestamp DATETIME NOT NULL, 
	battery_level FLOAT NOT NULL, 
	temperature_c FLOAT NOT NULL, 
	radiation_msv FLOAT NOT NULL, 
	signal_strength_dbm FLOAT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(satellite_id) REFERENCES satellites (id)
);

