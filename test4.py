from flask import Flask, render_template, request, jsonify, make_response
import pymysql
from datetime import datetime
from collections import OrderedDict
from io import StringIO
import csv
from datetime import timedelta 
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
        
def get_comparison():
    """Compare today's data up to the current hour with yesterday's total data."""
    connection = get_db_connection()
    if not connection:
        return None

    try:
        with connection.cursor() as cursor:
            categories = ["bike", "car", "bus", "pedestrian", "truck", "animals"]
            comparison_data = []

            current_hour = datetime.now().hour

            for category in categories:
                # Fetch today's cumulative count up to the current hour
                sql_today = f"""
                    SELECT SUM({category}) AS total_count
                    FROM traffic 
                    WHERE DATE(`current_date`) = CURDATE() 
                    AND HOUR(`current_time`) <= {current_hour};
                """
                cursor.execute(sql_today)
                today_count = cursor.fetchone()[0] or 0  # Convert None to 0

                # Fetch yesterday's total count for the entire day
                sql_yesterday = f"""
                    SELECT SUM({category}) AS total_count
                    FROM traffic 
                    WHERE DATE(`current_date`) = CURDATE() - INTERVAL 1 DAY;
                """
                cursor.execute(sql_yesterday)
                yesterday_total = cursor.fetchone()[0] or 0  # Convert None to 0

                # Calculate percentage difference safely (avoid division by zero)
                if yesterday_total > 0:
                    percentage_difference = ((today_count - yesterday_total) / yesterday_total) * 100
                else:
                    percentage_difference = 0  # If yesterday's value is 0, avoid division error

                comparison_data.append({
                    "category": category,
                    "today": today_count,
                    "yesterday_total": yesterday_total,
                    "difference": today_count - yesterday_total,
                    "percentage_difference": round(percentage_difference, 2)  # Keep two decimal places
                })

            return comparison_data

    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return None
    finally:
        connection.close()

def get_vehicle_counts():
    connection = get_db_connection()
    if not connection:
        print("Database connection failed!")  # Debugging
        return {"daily_total": 0, "hourly_total": 0}

    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:  # ✅ Use DictCursor
            today = datetime.today().strftime('%Y-%m-%d')
            current_hour = int(datetime.now().strftime('%H'))

            # ✅ Debugging
            print(f"Today's Date: {today}, Current Hour: {current_hour}")

            # Query for daily total vehicle count
            daily_query = """
            SELECT SUM(car + bus + bike + truck) AS daily_total 
            FROM traffic 
            WHERE `current_date` = %s;
            """
            cursor.execute(daily_query, (today,))
            daily_result = cursor.fetchone()
            daily_total = daily_result["daily_total"] if daily_result and daily_result["daily_total"] is not None else 0

            # Query for hourly total vehicle count
            hourly_query = """
            SELECT SUM(car + bus + bike + truck) AS hourly_total 
            FROM traffic 
            WHERE `current_date` = %s AND HOUR(`current_time`) = %s;
            """
            cursor.execute(hourly_query, (today, current_hour))
            hourly_result = cursor.fetchone()
            hourly_total = hourly_result["hourly_total"] if hourly_result and hourly_result["hourly_total"] is not None else 0

            # ✅ Debugging output
            print(f"Daily Total: {daily_total}, Hourly Total: {hourly_total}")

            return {"daily_total": daily_total, "hourly_total": hourly_total}

    except Exception as e:
        print(f"Error fetching vehicle counts: {e}")
        return {"daily_total": 0, "hourly_total": 0}

    finally:
        if connection:
            connection.close()

def get_animal_counts():
    """Retrieve the total number of animals detected in the current month and year."""
    connection = get_db_connection()
    if not connection:
        return {"monthly_count": 0, "yearly_count": 0}

    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT 
                    COALESCE(SUM(CASE WHEN MONTH(`current_date`) = MONTH(CURDATE()) 
                                      AND YEAR(`current_date`) = YEAR(CURDATE()) 
                                      THEN animals ELSE 0 END), 0) AS monthly_count,
                    COALESCE(SUM(CASE WHEN YEAR(`current_date`) = YEAR(CURDATE()) 
                                      THEN animals ELSE 0 END), 0) AS yearly_count
                FROM traffic;
            """
            cursor.execute(sql)
            result = cursor.fetchone()
            return {
                "monthly_count": result[0] if result else 0,
                "yearly_count": result[1] if result else 0
            }
    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return {"monthly_count": 0, "yearly_count": 0}
    finally:
        connection.close()
def get_current_animal_count():
    """Retrieve the count of animals detected at the current time."""
    connection = get_db_connection()
    if not connection:
        return {"error": "Database connection failed"}

    try:
        with connection.cursor() as cursor:
            sql = """
            SELECT COALESCE(
                (SELECT animals FROM traffic WHERE `current_date` = CURDATE() AND TIME_FORMAT(`current_time`, '%H:%i') = TIME_FORMAT(NOW(), '%H:%i') ORDER BY `current_time` DESC LIMIT 1), 0) AS animal_count;

            """
            cursor.execute(sql)
            result = cursor.fetchone()
            return {"current_animal_count": result[0] if result else 0}

    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return {"error": "Database query failed"}
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
@app.route('/export', methods=['POST'])
def export_data():
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    
    # Validate dates
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        if start_dt > end_dt:
            return "End date must be after start date", 400
    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD", 400
    
    # Get database connection
    connection = get_db_connection()
    if not connection:
        return "Database connection failed", 500

    try:
        with connection.cursor() as cursor:
            # Query for raw data
            sql = """
                SELECT * FROM traffic
                WHERE `current_date` BETWEEN %s AND %s
                ORDER BY `current_date`, `current_time`
            """
            cursor.execute(sql, (start_date, end_date))
            results = cursor.fetchall()
            
            if not results:
                return "No data found for selected date range", 404
            
            # Generate CSV
            def generate_csv():
                data = StringIO()
                writer = csv.writer(data)
                
                # Write header
                if results:
                    writer.writerow(results[0].keys())
                    
                # Write data rows
                for row in results:
                    writer.writerow(row.values())
                    yield data.getvalue()
                    data.seek(0)
                    data.truncate(0)
            
            # Create response
            response = make_response(generate_csv())
            filename = f"traffic_data_{start_date}_to_{end_date}.csv"
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            response.headers['Content-type'] = 'text/csv'
            return response
            
    except pymysql.MySQLError as e:
        return f"Database error: {e}", 500
    finally:
        connection.close()

# def this_week_data():
#     days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
    
#     today = datetime.today()
#     weekday_index = today.weekday()
#     start_of_week = today - timedelta(days=weekday_index + 1)  # Start from last Sunday

#     # Ensure database connection
#     conn = get_db_connection()  # Assuming this function is defined elsewhere
#     cursor = conn.cursor()

#     query = """
#         SELECT DAYNAME(`current_date`), 
#                SUM(car + bike + bus + truck) AS total_vehicles
#         FROM traffic 
#         WHERE `current_date` BETWEEN %s AND %s 
#         GROUP BY DAYNAME(`current_date`)
#     """
    
#     cursor.execute(query, (start_of_week.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')))
    
#     db_results = {day: 0 for day in days}  # Initialize all days with zero
    
#     for day, value in cursor.fetchall():
#         db_results[day[:3].upper()] = value  # Convert MySQL day name to short form
    
#     conn.close()
    
#     # Set future days to zero
#     today_index = days.index(today.strftime("%a").upper())
#     for i in range(today_index + 1, len(days)):
#         db_results[days[i]] = 0
    
#     return [db_results[day] for day in days]

# def last_week_data():
#     days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
    
#     today = datetime.today()
#     weekday_index = today.weekday()
    
#     # Get the start and end of last week
#     last_sunday = today - timedelta(days=weekday_index + 8)  # Last week's Sunday
#     last_saturday = today - timedelta(days=weekday_index + 2)  # Last week's Saturday

#     # Ensure database connection
#     conn = get_db_connection()  # Assuming this function is defined elsewhere
#     cursor = conn.cursor()

#     query = """
#         SELECT DAYNAME(`current_date`), 
#                SUM(car + bike + bus + truck) AS total_vehicles
#         FROM traffic 
#         WHERE `current_date` BETWEEN %s AND %s 
#         GROUP BY DAYNAME(`current_date`)
#     """
    
#     cursor.execute(query, (last_sunday.strftime('%Y-%m-%d'), last_saturday.strftime('%Y-%m-%d')))
    
#     db_results = {day: 0 for day in days}  # Initialize all days with zero
    
#     for day, value in cursor.fetchall():
#         db_results[day[:3].upper()] = value  # Convert MySQL day name to short form
    
#     conn.close()
    
#     return [db_results[day] for day in days]

@app.route('/live_total_vehicle_count', methods=['GET'])
def live_total_vehicle_count():
    """API to return the total vehicle count till the current minute."""
    connection = get_db_connection()
    if not connection:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        with connection.cursor() as cursor:

            sql = """
                SELECT COALESCE(SUM(car + bus + bike + truck + pedestrian + animals), 0) AS total_vehicles
                FROM traffic
            """
            cursor.execute(sql)
            result = cursor.fetchone()
            if result:  # Ensure result is not None
                total_vehicles = result[0]  # Access by index, not by string key
            else:
                total_vehicles = 0
            return jsonify({"total_vehicles": total_vehicles})

    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Database query failed"}), 500
    finally:
        connection.close()

# ------------------ FLASK ROUTES ------------------
 # Home page with login button
@app.route('/') 
def index():
    """Render the main dashboard page with weekly and hourly traffic data."""
    columns = ["car", "bike", "bus", "pedestrian", "truck", "animals"]
    totals = {col: get_total_count(col, datetime.today().date()) for col in columns}
    #data_this_week = this_week_data()
    #data_last_week = last_week_data()  # Fetch last week's data
    hourly_comparison = get_comparison()
    animal_counts = get_animal_counts()
    total_animals_month = animal_counts.get("monthly_count", 0)
    total_animals_year = animal_counts.get("yearly_count", 0)
    live_animal_count = get_current_animal_count().get("current_animal_count", 0)
    vehicle_counts = get_vehicle_counts()
    daily_total_vehicles = vehicle_counts["daily_total"]
    hourly_total_vehicles = vehicle_counts["hourly_total"]

    return render_template(
        "index.html",
        **totals,
        #weekly_data=data_this_week,
        #last_week_data=data_last_week,  # Add last week's data to template
        hourly_comparison=hourly_comparison,
        total_animals_month=total_animals_month,
        total_animals_year=total_animals_year,
        live_animal_count=live_animal_count,
        daily_total_vehicles=daily_total_vehicles,
        hourly_total_vehicles=hourly_total_vehicles
    )


        
# @app.route('/get-this-weekly-data')
# def get_weekly_data():
#     return jsonify({
#         "thisWeek": this_week_data(),
#         "lastWeek": last_week_data()
#     })

@app.route('/fetch_vehicle_counts', methods=['GET'])
def fetch_vehicle_counts():
    try:
        vehicle_count = get_vehicle_counts()

        # ✅ Ensure JSON response
        return jsonify(vehicle_count), 200

    except Exception as e:
        print(f"Error in /fetch_vehicle_counts: {e}")  # Debugging
        return jsonify({"error": str(e)}), 500  # Return error message as JSON


@app.route('/weekly_vehicle_counts', methods=['GET'])
def weekly_vehicle_counts():
    data = get_weekly_vehicle_counts()
    if data:
        return jsonify(data)
    return jsonify({"error": "Database error occurred."}), 500
@app.route('/live_animal_count', methods=['GET'])
def live_animal_count():
    """API to fetch live animal count."""
    return jsonify(get_current_animal_count())
@app.route('/live_data', methods=['GET'])
def live_data():
    """API to return the latest traffic counts dynamically."""
    columns = ["car", "bike", "bus", "pedestrian", "truck", "animals"]
    totals = {col: get_total_count(col, datetime.today().date()) for col in columns}
    
    print("Live Data Response:", totals)

    return jsonify(totals)

@app.route('/animal_counts', methods=['GET'])
def animal_counts():
    """API to get the total number of animals detected in the current month and year."""
    counts = get_animal_counts()  # Call the updated function
    return jsonify({
        "total_animals_month": counts["monthly_count"],
        "total_animals_year": counts["yearly_count"]
    })


@app.route('/hourly_comparison', methods=['GET'])
def hourly_comparison():
    """API endpoint to get today's cumulative data compared to yesterday's total."""
    data = get_comparison()
    if data is not None:
        return jsonify(data)
    return jsonify({"error": "Database error occurred."}), 500

@app.route('/total_counts_today', methods=['GET'])
def total_counts_today():
    """API endpoint to get today's total vehicle counts for each category."""
    columns = ["car", "bike", "bus", "pedestrian", "truck", "animals"]
    totals = {col: get_total_count(col, datetime.today().date()) for col in columns}

    if None in totals.values():
        return jsonify({"error": "Database error occurred."}), 1000

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