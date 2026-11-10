import os
from decimal import Decimal
from datetime import date, datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "transport_db")
}


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def convert_data(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [convert_data(item) for item in value]
    if isinstance(value, dict):
        return {key: convert_data(val) for key, val in value.items()}
    return value


def query(sql, params=(), one=False, write=False):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(sql, params)

        if write:
            conn.commit()
            return cursor.lastrowid

        result = cursor.fetchone() if one else cursor.fetchall()
        return convert_data(result)

    finally:
        cursor.close()
        conn.close()


def ok(data=None, msg="success"):
    return jsonify({
        "status": "ok",
        "message": msg,
        "data": convert_data(data)
    }), 200


def err(msg, code=400):
    return jsonify({
        "status": "error",
        "message": msg
    }), code


@app.route("/")
def index():
    return send_from_directory(app.root_path, "index.html")


@app.route("/api/dashboard")
def dashboard():
    try:
        counts = {}

        for table in (
            "drivers", "vehicles", "routes",
            "trips", "passengers", "bookings"
        ):
            result = query(
                f"SELECT COUNT(*) AS n FROM {table}",
                one=True
            )
            counts[table] = result["n"]

        recent_trips = query(
            "SELECT * FROM v_trip_details ORDER BY trip_id DESC LIMIT 5"
        )

        recent_bookings = query(
            "SELECT * FROM v_booking_details ORDER BY booking_id DESC LIMIT 5"
        )

        return ok({
            "counts": counts,
            "recent_trips": recent_trips,
            "recent_bookings": recent_bookings
        })

    except Error as e:
        return err(str(e), 500)


# DRIVERS

@app.route("/api/drivers", methods=["GET"])
def get_drivers():
    try:
        return ok(query("SELECT * FROM drivers ORDER BY driver_id DESC"))
    except Error as e:
        return err(str(e), 500)


@app.route("/api/drivers", methods=["POST"])
def add_driver():
    d = request.get_json(silent=True) or {}

    name = (d.get("name") or "").strip()
    license_no = (d.get("license_no") or "").strip()
    phone = (d.get("phone") or "").strip()

    if not all([name, license_no, phone]):
        return err("Name, license number and phone are required")

    try:
        driver_id = query(
            "INSERT INTO drivers (name, license_no, phone) VALUES (%s,%s,%s)",
            (name, license_no, phone),
            write=True
        )
        return ok({"driver_id": driver_id}, "Driver added successfully")

    except Error as e:
        return err(str(e))


@app.route("/api/drivers/<int:did>", methods=["DELETE"])
def delete_driver(did):
    try:
        query("DELETE FROM drivers WHERE driver_id=%s", (did,), write=True)
        return ok(msg="Driver deleted")
    except Error as e:
        return err(str(e))


# VEHICLES

@app.route("/api/vehicles", methods=["GET"])
def get_vehicles():
    try:
        return ok(query("SELECT * FROM vehicles ORDER BY vehicle_id DESC"))
    except Error as e:
        return err(str(e), 500)


@app.route("/api/vehicles", methods=["POST"])
def add_vehicle():
    d = request.get_json(silent=True) or {}

    vehicle_no = (d.get("vehicle_no") or "").strip()
    vehicle_type = (d.get("type") or "Bus").strip()
    capacity = d.get("capacity")

    if not vehicle_no or capacity is None:
        return err("Vehicle number and capacity are required")

    try:
        vehicle_id = query(
            "INSERT INTO vehicles (vehicle_no, type, capacity) VALUES (%s,%s,%s)",
            (vehicle_no, vehicle_type, int(capacity)),
            write=True
        )
        return ok({"vehicle_id": vehicle_id}, "Vehicle added successfully")

    except (Error, ValueError) as e:
        return err(str(e))


@app.route("/api/vehicles/<int:vid>", methods=["DELETE"])
def delete_vehicle(vid):
    try:
        query("DELETE FROM vehicles WHERE vehicle_id=%s", (vid,), write=True)
        return ok(msg="Vehicle deleted")
    except Error as e:
        return err(str(e))


# ROUTES

@app.route("/api/routes", methods=["GET"])
def get_routes():
    try:
        return ok(query("SELECT * FROM routes ORDER BY route_id DESC"))
    except Error as e:
        return err(str(e), 500)


@app.route("/api/routes", methods=["POST"])
def add_route():
    d = request.get_json(silent=True) or {}

    source = (d.get("source") or "").strip()
    destination = (d.get("destination") or "").strip()
    distance = d.get("distance")

    if not source or not destination or distance is None:
        return err("Source, destination and distance are required")

    try:
        route_id = query(
            "INSERT INTO routes (source, destination, distance) VALUES (%s,%s,%s)",
            (source, destination, float(distance)),
            write=True
        )
        return ok({"route_id": route_id}, "Route added successfully")

    except (Error, ValueError) as e:
        return err(str(e))


@app.route("/api/routes/<int:rid>", methods=["DELETE"])
def delete_route(rid):
    try:
        query("DELETE FROM routes WHERE route_id=%s", (rid,), write=True)
        return ok(msg="Route deleted")
    except Error as e:
        return err(str(e))


# TRIPS

@app.route("/api/trips", methods=["GET"])
def get_trips():
    try:
        return ok(query(
            "SELECT * FROM v_trip_details ORDER BY trip_id DESC"
        ))
    except Error as e:
        return err(str(e), 500)


@app.route("/api/trips", methods=["POST"])
def add_trip():
    d = request.get_json(silent=True) or {}

    driver_id = d.get("driver_id")
    vehicle_id = d.get("vehicle_id")
    route_id = d.get("route_id")
    trip_date = (d.get("trip_date") or "").strip()

    if not all([driver_id, vehicle_id, route_id, trip_date]):
        return err("Driver, vehicle, route and trip date are required")

    try:
        trip_id = query(
            """INSERT INTO trips
            (driver_id, vehicle_id, route_id, trip_date)
            VALUES (%s,%s,%s,%s)""",
            (int(driver_id), int(vehicle_id), int(route_id), trip_date),
            write=True
        )
        return ok({"trip_id": trip_id}, "Trip scheduled successfully")

    except (Error, ValueError) as e:
        return err(str(e))


@app.route("/api/trips/<int:tid>", methods=["DELETE"])
def delete_trip(tid):
    try:
        query("DELETE FROM trips WHERE trip_id=%s", (tid,), write=True)
        return ok(msg="Trip deleted")
    except Error as e:
        return err(str(e))


# PASSENGERS

@app.route("/api/passengers", methods=["GET"])
def get_passengers():
    try:
        return ok(query(
            "SELECT * FROM passengers ORDER BY passenger_id DESC"
        ))
    except Error as e:
        return err(str(e), 500)


@app.route("/api/passengers", methods=["POST"])
def add_passenger():
    d = request.get_json(silent=True) or {}

    name = (d.get("name") or "").strip()
    phone = (d.get("phone") or "").strip()

    if not name or not phone:
        return err("Name and phone are required")

    try:
        passenger_id = query(
            "INSERT INTO passengers (name, phone) VALUES (%s,%s)",
            (name, phone),
            write=True
        )
        return ok(
            {"passenger_id": passenger_id},
            "Passenger added successfully"
        )

    except Error as e:
        return err(str(e))


@app.route("/api/passengers/<int:pid>", methods=["DELETE"])
def delete_passenger(pid):
    try:
        query(
            "DELETE FROM passengers WHERE passenger_id=%s",
            (pid,),
            write=True
        )
        return ok(msg="Passenger deleted")
    except Error as e:
        return err(str(e))


# BOOKINGS

@app.route("/api/bookings", methods=["GET"])
def get_bookings():
    try:
        return ok(query(
            "SELECT * FROM v_booking_details ORDER BY booking_id DESC"
        ))
    except Error as e:
        return err(str(e), 500)


@app.route("/api/bookings", methods=["POST"])
def add_booking():
    d = request.get_json(silent=True) or {}

    passenger_id = d.get("passenger_id")
    trip_id = d.get("trip_id")
    seat_no = d.get("seat_no")
    booking_date = (d.get("booking_date") or "").strip()

    if not all([
        passenger_id, trip_id,
        seat_no is not None, booking_date
    ]):
        return err("Passenger, trip, seat number and booking date are required")

    try:
        trip = query(
            "SELECT vehicle_id FROM trips WHERE trip_id=%s",
            (int(trip_id),),
            one=True
        )

        if not trip:
            return err("Trip not found")

        vehicle = query(
            "SELECT capacity FROM vehicles WHERE vehicle_id=%s",
            (trip["vehicle_id"],),
            one=True
        )

        booked = query(
            "SELECT COUNT(*) AS n FROM bookings WHERE trip_id=%s",
            (int(trip_id),),
            one=True
        )["n"]

        if booked >= vehicle["capacity"]:
            return err("Vehicle is at full capacity")

        booking_id = query(
            """INSERT INTO bookings
            (passenger_id, trip_id, seat_no, booking_date)
            VALUES (%s,%s,%s,%s)""",
            (
                int(passenger_id),
                int(trip_id),
                int(seat_no),
                booking_date
            ),
            write=True
        )

        return ok(
            {"booking_id": booking_id},
            "Booking confirmed successfully"
        )

    except (Error, ValueError) as e:
        if "Duplicate" in str(e):
            return err("Seat already booked on this trip")
        return err(str(e))


@app.route("/api/bookings/<int:bid>", methods=["DELETE"])
def delete_booking(bid):
    try:
        query(
            "DELETE FROM bookings WHERE booking_id=%s",
            (bid,),
            write=True
        )
        return ok(msg="Booking cancelled")
    except Error as e:
        return err(str(e))


if __name__ == "__main__":
    app.run(debug=False, port=5000)