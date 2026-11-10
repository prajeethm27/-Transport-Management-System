-- ============================================================
--  TRANSPORT MANAGEMENT SYSTEM — MySQL Schema
--  Run this script once to set up the database
-- ============================================================

CREATE DATABASE IF NOT EXISTS transport_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE transport_db;

-- ─── DRIVERS ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS drivers (
  driver_id   INT           PRIMARY KEY AUTO_INCREMENT,
  name        VARCHAR(100)  NOT NULL,
  license_no  VARCHAR(50)   NOT NULL UNIQUE,
  phone       VARCHAR(20)   NOT NULL,
  created_at  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

-- ─── VEHICLES ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS vehicles (
  vehicle_id  INT           PRIMARY KEY AUTO_INCREMENT,
  vehicle_no  VARCHAR(30)   NOT NULL UNIQUE,
  type        ENUM('Bus','Mini-Bus','Van','Car','Truck') NOT NULL DEFAULT 'Bus',
  capacity    INT           NOT NULL CHECK (capacity > 0),
  created_at  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

-- ─── ROUTES ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS routes (
  route_id    INT           PRIMARY KEY AUTO_INCREMENT,
  source      VARCHAR(100)  NOT NULL,
  destination VARCHAR(100)  NOT NULL,
  distance    DECIMAL(8,2)  NOT NULL CHECK (distance > 0),
  created_at  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

-- ─── TRIPS ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS trips (
  trip_id     INT           PRIMARY KEY AUTO_INCREMENT,
  driver_id   INT           NOT NULL,
  vehicle_id  INT           NOT NULL,
  route_id    INT           NOT NULL,
  trip_date   DATE          NOT NULL,
  created_at  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (driver_id)  REFERENCES drivers(driver_id)  ON DELETE RESTRICT,
  FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id) ON DELETE RESTRICT,
  FOREIGN KEY (route_id)   REFERENCES routes(route_id)    ON DELETE RESTRICT
);

-- ─── PASSENGERS ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS passengers (
  passenger_id INT          PRIMARY KEY AUTO_INCREMENT,
  name         VARCHAR(100) NOT NULL,
  phone        VARCHAR(20)  NOT NULL,
  created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- ─── BOOKINGS ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bookings (
  booking_id   INT          PRIMARY KEY AUTO_INCREMENT,
  passenger_id INT          NOT NULL,
  trip_id      INT          NOT NULL,
  seat_no      INT          NOT NULL,
  booking_date DATE         NOT NULL,
  created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id) ON DELETE RESTRICT,
  FOREIGN KEY (trip_id)      REFERENCES trips(trip_id)           ON DELETE RESTRICT,
  UNIQUE KEY uq_seat (trip_id, seat_no)   -- one seat per trip
);

-- ─── VIEWS (handy for reporting) ────────────────────────────
CREATE OR REPLACE VIEW v_trip_details AS
  SELECT
    t.trip_id,
    t.trip_date,
    d.name        AS driver_name,
    d.license_no,
    v.vehicle_no,
    v.type        AS vehicle_type,
    v.capacity,
    r.source,
    r.destination,
    r.distance
  FROM trips t
  JOIN drivers  d ON t.driver_id  = d.driver_id
  JOIN vehicles v ON t.vehicle_id = v.vehicle_id
  JOIN routes   r ON t.route_id   = r.route_id;

CREATE OR REPLACE VIEW v_booking_details AS
  SELECT
    b.booking_id,
    b.booking_date,
    b.seat_no,
    p.name        AS passenger_name,
    p.phone       AS passenger_phone,
    t.trip_date,
    r.source,
    r.destination,
    v.vehicle_no
  FROM bookings b
  JOIN passengers p ON b.passenger_id = p.passenger_id
  JOIN trips      t ON b.trip_id      = t.trip_id
  JOIN routes     r ON t.route_id     = r.route_id
  JOIN vehicles   v ON t.vehicle_id   = v.vehicle_id;
SELECT * FROM vehicles