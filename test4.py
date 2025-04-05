from flask import Flask, render_template, request, jsonify
import pymysql
from datetime import datetime
from collections import OrderedDict
app = Flask(__name__)

def get_db_connection():
    """Establish a connection to the MySQL database."""
    try:
        return pymysql.connect(
            host="localhost",
            user="root",
            password="12345678",
            database="traffic_db"
        )
    except pymysql.MySQLError as e:
        print(f"Database connection error: {e}")
        return None

def get_total_count(column, date=None):
    """Retrieve the total count of a specific column (e.g., car, bike) for a given date."""
    valid_columns = ["car", "bike", "bus", "pedestrian", "truck", "animals"]
    if column not in valid_columns:
        print(f"Invalid column name: {column}")
        return 0  # Return 0 if an invalid column is provided

    connection = get_db_connection()
    if not connection:
        return None

    try:
        with connection.cursor() as cursor:
            sql = f"SELECT SUM({column}) FROM traffic"
            params = []
            if date:
                sql += " WHERE `current_date` = %s"
                params.append(date)
            cursor.execute(sql, params)
            result = cursor.fetchone()[0]
            return result if result is not None else 0
    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return None
    finally:
        connection.close()
        
def get_hourly_counts():
    """Retrieve hourly count comparisons for all categories between today and yesterday."""
    connection = get_db_connection()
    if not connection:
        return None

    try:
        with connection.cursor() as cursor:
            categories = ["car", "bike", "bus", "pedestrian", "truck", "animals"]
            hourly_comparison = []

            for category in categories:
                sql_today = f"""
                    SELECT HOUR(`current_time`) AS hour, SUM({category}) AS total_count
                    FROM traffic 
                    WHERE DATE(`current_date`) = CURDATE()
                    GROUP BY HOUR(`current_time`)
                    ORDER BY hour;
                """
                cursor.execute(sql_today)
                today_data = cursor.fetchall()

                sql_yesterday = f"""
                    SELECT HOUR(`current_time`) AS hour, SUM({category}) AS total_count
                    FROM traffic 
                    WHERE DATE(`current_date`) = CURDATE() - INTERVAL 1 DAY
                    GROUP BY HOUR(`current_time`)
                    ORDER BY hour;
                """
                cursor.execute(sql_yesterday)
                yesterday_data = cursor.fetchall()

                today_dict = {row[0]: row[1] for row in today_data}
                yesterday_dict = {row[0]: row[1] for row in yesterday_data}

                for hour in range(24):
                    today_count = today_dict.get(hour, 0)
                    yesterday_count = yesterday_dict.get(hour, 0)
                    difference = today_count - yesterday_count

                    hourly_comparison.append({
                        "hour": hour,
                        "category": category,
                        "today": today_count,
                        "yesterday": yesterday_count,
                        "difference": difference
                    })

            return hourly_comparison

    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return None
    finally:
        connection.close()

def get_current_month_animal_count():
    """Retrieve the total number of animals detected in the current month."""
    connection = get_db_connection()
    if not connection:
        return 0

    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT COALESCE(SUM(animals), 0) FROM traffic
                WHERE MONTH(`current_date`) = MONTH(CURDATE())
                AND YEAR(`current_date`) = YEAR(CURDATE());
            """
            cursor.execute(sql)
            result = cursor.fetchone()[0]
            return result if result is not None else 0
    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return 0
    finally:
        connection.close()
        
def format_weekly_data(data):
    """
    Format the weekly vehicle count data to ensure correct order.
    """
    week_order = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    
    # Ensure all days are included, defaulting to 0 if missing
    formatted_data = OrderedDict((day, int(data.get(day, 0))) for day in week_order)
    
    return formatted_data

def get_weekly_vehicle_counts():
    connection = get_db_connection()
    if not connection:
        return None

    try:
        with connection.cursor() as cursor:
            sql_this_week = """
                WITH this_week_days AS (
                    SELECT DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) + 1 DAY) + INTERVAL (n - 1) DAY AS `date`
                    FROM (SELECT 1 AS n UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7) AS nums
                    WHERE DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) + 1 DAY) + INTERVAL (n - 1) DAY <= CURDATE()
                )
                SELECT DATE_FORMAT(twd.date, '%a') AS day_name, 
                    COALESCE(SUM(t.car + t.bus + t.bike + t.truck + t.pedestrian + t.animals), 0) AS total_vehicles
                FROM this_week_days twd
                LEFT JOIN traffic t ON twd.date = t.current_date
                GROUP BY twd.date
                ORDER BY twd.date;
            """
            cursor.execute(sql_this_week)
            this_week_data = {row[0]: row[1] for row in cursor.fetchall()}

            sql_last_week = """
                WITH last_week_days AS (
                    SELECT DATE_SUB(CURDATE(), INTERVAL (WEEKDAY(CURDATE()) + 1 + 7) DAY) + INTERVAL (n - 1) DAY AS `date`
                    FROM (SELECT 1 AS n UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7) AS nums
                )
                SELECT DATE_FORMAT(lwd.date, '%a') AS day_name, 
                    COALESCE(SUM(t.car + t.bus + t.bike + t.truck + t.pedestrian + t.animals), 0) AS total_vehicles
                FROM last_week_days lwd
                LEFT JOIN traffic t ON lwd.date = t.current_date
                GROUP BY lwd.date
                ORDER BY lwd.date;
            """
            cursor.execute(sql_last_week)
            last_week_data = {row[0]: row[1] for row in cursor.fetchall()}

            return {
                "this_week": format_weekly_data(this_week_data),
                "last_week": format_weekly_data(last_week_data),
            }

    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return None
    finally:
        connection.close()

@app.route('/live_total_vehicle_count', methods=['GET'])
def live_total_vehicle_count():
    """API to return the total vehicle count till the current minute."""
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        with connection.cursor() as cursor:
            current_time = datetime.now().strftime("%H:%M:%S")
            current_date = datetime.today().date()

            sql = """
                SELECT COALESCE(SUM(car + bus + bike + truck + pedestrian + animals), 0) 
                FROM traffic
                WHERE current_date = %s AND current_time <= %s
            """
            cursor.execute(sql, (current_date, current_time))
            result = cursor.fetchone()

            # Fix: Access the tuple using index 0
            total_vehicles = result[0] if result and result[0] is not None else 0

            return jsonify({"total_vehicles": total_vehicles})

    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Database query failed"}), 500
    finally:
        connection.close()


# ------------------ FLASK ROUTES ------------------
@app.route('/')
def index():
    """Render the main dashboard page with weekly and hourly traffic data."""
    columns = ["car", "bike", "bus", "pedestrian", "truck", "animals"]
    totals = {col: get_total_count(col, datetime.today().date()) for col in columns}

    data = get_weekly_vehicle_counts()  # Fetch weekly data
    hourly_comparison = get_hourly_counts()
    total_animals_month = get_current_month_animal_count()

    return render_template(
        "index.html",
        **totals,
        weekly_data=data,  # ✅ Pass weekly data
        hourly_comparison=hourly_comparison,
        total_animals_month=total_animals_month
    )


@app.route('/weekly_vehicle_counts', methods=['GET'])
def weekly_vehicle_counts():
    data = get_weekly_vehicle_counts()
    if data:
        return jsonify(data)
    return jsonify({"error": "Database error occurred."}), 500

@app.route('/live_data', methods=['GET'])
def live_data():
    """API to return the latest traffic counts dynamically."""
    columns = ["car", "bike", "bus", "pedestrian", "truck", "animals"]
    totals = {col: get_total_count(col, datetime.today().date()) for col in columns}
    
    print("Live Data Response:", totals)

    return jsonify(totals)

@app.route('/monthly_animal_count', methods=['GET'])
def monthly_animal_count():
    """API to get the total number of animals detected in the current month."""
    total_animals_month = get_current_month_animal_count()
    return jsonify({"total_animals_month": total_animals_month})


@app.route('/hourly_comparison', methods=['GET'])
def hourly_comparison():
    """API endpoint to get hourly comparison data for all categories."""
    data = get_hourly_counts()
    if data is not None:
        return jsonify(data)
    return jsonify({"error": "Database error occurred."}), 500

@app.route('/total_counts_today', methods=['GET'])
def total_counts_today():
    """API endpoint to get today's total vehicle counts for each category."""
    columns = ["car", "bike", "bus", "pedestrian", "truck", "animals"]
    totals = {col: get_total_count(col, datetime.today().date()) for col in columns}

    if None in totals.values():
        return jsonify({"error": "Database error occurred."}), 500

    totals["date"] = str(datetime.today().date())
    return jsonify(totals)

@app.route('/total_count', methods=['GET'])
def total_count():
    """API endpoint to get the total count of a specific type of vehicle."""
    column = request.args.get('type')
    date = request.args.get('date', str(datetime.today().date()))

    if column not in ["car", "bike", "bus", "pedestrian", "truck", "animals"]:
        return jsonify({"error": "Invalid type provided"}), 400

    total = get_total_count(column, date)
    return jsonify({column: total})

@app.route('/documentation')
def documentation():
    """Render the API documentation page."""
    return render_template("docs/documentation.html")

@app.route('/chartjs')
def chartjs():
    """Render the Chart.js visualization page."""
    return render_template("pages/charts/chartjs.html")

# ------------------ RUN FLASK APP ------------------
if __name__ == "__main__":  
    app.run(debug=True)