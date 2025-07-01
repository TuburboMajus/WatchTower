/******************************\
 *  INITIALIZE
\******************************/ 

drop database IF EXISTS $database;
create database $database;
use $database;


/******************************\
 * TABLES
\******************************/ 


/***** APP *****/

create table if not exists watchtower(
    version varchar(20) primary key not null
);

create table if not exists language(
    code varchar(2) primary key not null,
    name varchar(50) not null
);

create table if not exists job(
    name varchar(50) primary key not null,
    state varchar(20) not null default "IDLE",
    last_exit_code int
);


-- User table
create table if not exists privilege(
    id varchar(36) primary key not null,
    label varchar(256) not null unique,
    roles varchar(256) not null,
    editable bool not null default 1
);

create table if not exists user(
    id varchar(36) primary key not null,
    privilege varchar(36) not null,
    email varchar(320) not null,
    password binary(60) not null,
    is_authenticated bool not null default 0,
    is_active bool not null default 0,
    is_disabled bool not null default 0,
    language varchar(256) not null default "en",
    foreign key (language) references language(code),
    foreign key (privilege) references privilege(id)
);

-- Service table
CREATE TABLE if not exists Service (
    service_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    type ENUM('webserver', 'database', 'program') NOT NULL,
    details VARCHAR(2000) NOT NULL,
    check_interval INTEGER NOT NULL CHECK (check_interval > 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- HealthCheck table
CREATE TABLE if not exists HealthCheck (
    check_id INTEGER PRIMARY KEY AUTO_INCREMENT,
    service_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status ENUM('healthy', 'unhealthy', 'unknown') NOT NULL,
    response_time FLOAT CHECK (response_time >= 0),
    error_message TEXT,
    FOREIGN KEY (service_id) REFERENCES Service(service_id) ON DELETE CASCADE
);

-- AlertSubscription table (for user-service notification relationships)
CREATE TABLE if not exists AlertSubscription (
    user_id VARCHAR(36) NOT NULL,
    service_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, service_id),
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES Service(service_id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX idx_service_active ON Service(is_active);
CREATE INDEX idx_healthcheck_service ON HealthCheck(service_id);
CREATE INDEX idx_healthcheck_timestamp ON HealthCheck(timestamp);
CREATE INDEX idx_healthcheck_status ON HealthCheck(status);
CREATE INDEX idx_alert_subscription_user ON AlertSubscription(user_id);
CREATE INDEX idx_alert_subscription_service ON AlertSubscription(service_id);