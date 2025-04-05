from flask import Flask, render_template, jsonify
import pymysql
from datetime import datetime

app = Flask(__name__)

# ✅ Function to Establish Database Connection
def get_db_connection():
    try:
        return pymysql.connect(
            host="localhost",
            user="root",
            password="12345678",
            database="traffic_db",
            cursorclass=pymysql.cursors.DictCursor
        )
    except pymysql.MySQLError as e:
        print(f"Database connection error: {e}")
        return None

# ✅ Function to Get Today's Latest Count
def get_latest_count(column):
    """Retrieve the latest count of a specific column (e.g., car, bike) for today."""
    connection = get_db_connection()
    if not connection:
        return None

    try:
        with connection.cursor() as cursor:
            sql = f"""
                SELECT {column} FROM traffic 
                WHERE current_date = CURDATE() 
                ORDER BY current_time DESC 
                LIMIT 1;
            """
            print(f"Executing SQL: {sql}")  # Debugging log

            cursor.execute(sql)
            result = cursor.fetchone()
            print(f"Latest count for {column}: {result}")  # Debugging log

            return result[column] if result else 0
    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return None
    finally:
        connection.close()

# ✅ Function to Get Total Count for Today
def get_total_count(column):
    """Retrieve the total count of a specific column (e.g., car, bike) for today."""
    connection = get_db_connection()
    if not connection:
        return None

    try:
        with connection.cursor() as cursor:
            sql = f"SELECT COALESCE(SUM({column}), 0) AS total FROM traffic WHERE current_date = CURDATE();"
            print(f"Executing SQL: {sql}")  # Debugging log

            cursor.execute(sql)
            result = cursor.fetchone()
            total_count = result["total"] if result else 0
            print(f"Total {column} count for today: {total_count}")  # Debugging log

            return total_count
    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return None
    finally:
        connection.close()

# ✅ API Endpoint to Get Live Data for All Categories
@app.route('/live_data', methods=['GET'])
def live_data():
    """Fetch real-time traffic data for today (latest recorded values)."""
    columns = ["car", "bike", "bus", "pedestrian", "truck", "animals"]
    
    # Get the latest count instead of summing up all values
    live_metrics = {col: get_latest_count(col) for col in columns}

    if None in live_metrics.values():
        return jsonify({"error": "Database error occurred."}), 500

    return jsonify(live_metrics)

# ✅ API Endpoint to Get Total Count for Today
@app.route('/total_counts_today', methods=['GET'])
def total_counts_today():
    """API to fetch total count for all categories today."""
    columns = ["car", "bike", "bus", "pedestrian", "truck", "animals"]
    
    # Get total count for today
    totals = {col: get_total_count(col) for col in columns}

    if None in totals.values():
        return jsonify({"error": "Database error occurred."}), 500

    return jsonify(totals)

# ✅ Render Dashboard with Car Count
@app.route('/')
def index():
    car_count_today = get_latest_count('car')  # Latest car count
    total_car_count = get_total_count('car')  # Total car count for today
    return render_template("index.html", car_count_today=car_count_today, total_car_count=total_car_count)

# ✅ API Endpoint for Live Car Count
@app.route('/car_count_live', methods=['GET'])
def car_count_live():
    """API to fetch only the latest car count"""
    total_cars = get_latest_count('car')  # Fetch latest recorded car count
    return jsonify({"car_count_today": total_cars})

@app.route('/documentation')
def documentation():
    """Render the API documentation page."""
    return render_template("docs/documentation.html")

@app.route('/chartjs')
def chartjs():
    """Render the Chart.js visualization page."""
    return render_template("pages/charts/chartjs.html")

# ✅ Run Flask App
if __name__ == "__main__":
    app.run(debug=True)
