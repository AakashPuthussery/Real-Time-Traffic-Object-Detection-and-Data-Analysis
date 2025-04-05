from flask import Flask, render_template, request, jsonify
import pymysql
from datetime import datetime
import os

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

            print(f"Executing SQL: {sql} with params: {params}")  # Debug log

            cursor.execute(sql, params)
            result = cursor.fetchone()[0]
            print(f"Query result for {column}: {result}")  # Debug log

            return result if result is not None else 0
    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return None
    finally:
        connection.close()

# def get_total_count(column, date=None):
#     """Retrieve the total count of a specific column (e.g., car, bike) for a given date."""
#     connection = get_db_connection()
#     if not connection:
#         return None

#     try:
#         with connection.cursor() as cursor:
#             sql = f"SELECT SUM({column}) FROM traffic"
#             params = []
#             if date:
#                 sql += " WHERE `current_date` = %s"
#                 params.append(date)
#             cursor.execute(sql, params)
#             result = cursor.fetchone()[0]
#             return result if result is not None else 0
#     except pymysql.MySQLError as e:
#         print(f"Database error: {e}")
#         return None
#     finally:
#         connection.close()
        
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
                # Query for today's hourly count with missing hours filled
                sql_today = f"""
                    WITH RECURSIVE hours AS (
                        SELECT 0 AS hour
                        UNION ALL
                        SELECT hour + 1 FROM hours WHERE hour < 23
                    )
                    SELECT h.hour, COALESCE(SUM(t.{category}), 0) AS total_count
                    FROM hours h
                    LEFT JOIN traffic t ON HOUR(t.current_time) = h.hour 
                        AND DATE(t.current_date) = CURDATE()
                    GROUP BY h.hour
                    ORDER BY h.hour;
                """
                cursor.execute(sql_today)
                today_data = cursor.fetchall()

                # Query for yesterday's hourly count with missing hours filled
                sql_yesterday = f"""
                    WITH RECURSIVE hours AS (
                        SELECT 0 AS hour
                        UNION ALL
                        SELECT hour + 1 FROM hours WHERE hour < 23
                    )
                    SELECT h.hour, COALESCE(SUM(t.{category}), 0) AS total_count
                    FROM hours h
                    LEFT JOIN traffic t ON HOUR(t.current_time) = h.hour 
                        AND DATE(t.current_date) = CURDATE() - INTERVAL 1 DAY
                    GROUP BY h.hour
                    ORDER BY h.hour;
                """
                cursor.execute(sql_yesterday)
                yesterday_data = cursor.fetchall()

                # Convert results into dictionaries for easy lookup
                today_dict = {row[0]: row[1] for row in today_data}
                yesterday_dict = {row[0]: row[1] for row in yesterday_data}

                # Store comparison for each hour
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
        if connection:
            connection.close()

# ------------------ FLASK ROUTES ------------------

@app.route('/')
def index():
    """Render the main dashboard page with hourly car count comparison."""
    columns = ["car", "bike", "bus", "pedestrian", "truck", "animals"]
    totals = {col: get_total_count(col, datetime.today().date()) for col in columns}
    
    # Get hourly car comparison data
    hourly_comparison = get_hourly_counts()

    return render_template("index.html", **totals, hourly_comparison=hourly_comparison)

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

@app.route('/live_data', methods=['GET'])
def live_data():
    """Fetch real-time traffic data for today only."""
    columns = ["car", "bike", "bus", "pedestrian", "truck", "animals"]
    live_metrics = {col: get_total_count(col, datetime.today().date()) for col in columns}

    if None in live_metrics.values():
        return jsonify({"error": "Database error occurred."}), 500

    return jsonify(live_metrics)

# @app.route('/live_data', methods=['GET'])
# def live_data():
#     """Fetch latest real-time data for the entire dashboard."""
    
#     # Define the metrics to be updated
#     columns = ["car", "bike", "bus", "pedestrian", "truck", "animals"]
    
#     # Fetch data dynamically for each metric
#     live_metrics = {col: get_total_count(col) for col in columns}

#     if None in live_metrics.values():
#         return jsonify({"error": "Database error occurred."}), 500

#     return jsonify(live_metrics)


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
    app.run(debug=True)  # Set debug=True for development mode
