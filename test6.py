from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import pymysql
from datetime import datetime
from collections import OrderedDict
app = Flask(__name__)
app.secret_key = "trafficsecretkey123"  # Required for session management

# Dummy user data for authentication
DUMMY_USERS = {
    "admin": "password123",
    "user": "user123"
}

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

# ---------- AUTHENTICATION AND SESSION MANAGEMENT ----------

# Login required decorator
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ---------- FLASK ROUTES ----------

@app.route('/')
def home():
    """Display the home page with login button"""
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if username exists and password is correct
        if username in DUMMY_USERS and DUMMY_USERS[username] == password:
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid credentials. Please try again.'
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    """Handle user logout"""
    session.pop('username', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Render the main dashboard page with traffic data."""
    columns = ["car", "bike", "bus", "pedestrian", "truck", "animals"]
    totals = {col: get_total_count(col, datetime.today().date()) for col in columns}
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
        hourly_comparison=hourly_comparison,
        total_animals_month=total_animals_month,
        total_animals_year=total_animals_year,
        live_animal_count=live_animal_count,
        daily_total_vehicles=daily_total_vehicles,
        hourly_total_vehicles=hourly_total_vehicles,
        username=session.get('username', '')
    )

# ---------- API ROUTES ----------

@app.route('/live_total_vehicle_count', methods=['GET'])
@login_required
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

@app.route('/fetch_vehicle_counts', methods=['GET'])
@login_required
def fetch_vehicle_counts():
    try:
        vehicle_count = get_vehicle_counts()
        return jsonify(vehicle_count), 200
    except Exception as e:
        print(f"Error in /fetch_vehicle_counts: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/weekly_vehicle_counts', methods=['GET'])
@login_required
def weekly_vehicle_counts():
    data = get_weekly_vehicle_counts()
    if data:
        return jsonify(data)
    return jsonify({"error": "Database error occurred."}), 500

@app.route('/live_animal_count', methods=['GET'])
@login_required
def live_animal_count():
    """API to fetch live animal count."""
    return jsonify(get_current_animal_count())

@app.route('/live_data', methods=['GET'])
@login_required
def live_data():
    """API to return the latest traffic counts dynamically."""
    columns = ["car", "bike", "bus", "pedestrian", "truck", "animals"]
    totals = {col: get_total_count(col, datetime.today().date()) for col in columns}
    return jsonify(totals)

@app.route('/animal_counts', methods=['GET'])
@login_required
def animal_counts():
    """API to get the total number of animals detected in the current month and year."""
    counts = get_animal_counts()
    return jsonify({
        "total_animals_month": counts["monthly_count"],
        "total_animals_year": counts["yearly_count"]
    })

@app.route('/hourly_comparison', methods=['GET'])
@login_required
def hourly_comparison():
    """API endpoint to get today's cumulative data compared to yesterday's total."""
    data = get_comparison()
    if data is not None:
        return jsonify(data)
    return jsonify({"error": "Database error occurred."}), 500

@app.route('/total_counts_today', methods=['GET'])
@login_required
def total_counts_today():
    """API endpoint to get today's total vehicle counts for each category."""
    columns = ["car", "bike", "bus", "pedestrian", "truck", "animals"]
    totals = {col: get_total_count(col, datetime.today().date()) for col in columns}

    if None in totals.values():
        return jsonify({"error": "Database error occurred."}), 1000

    totals["date"] = str(datetime.today().date())
    return jsonify(totals)

@app.route('/total_count', methods=['GET'])
@login_required
def total_count():
    """API endpoint to get the total count of a specific type of vehicle."""
    column = request.args.get('type')
    date = request.args.get('date', str(datetime.today().date()))

    if column not in ["car", "bike", "bus", "pedestrian", "truck", "animals"]:
        return jsonify({"error": "Invalid type provided"}), 400

    total = get_total_count(column, date)
    return jsonify({column: total})

@app.route('/documentation')
@login_required
def documentation():
    """Render the API documentation page."""
    return render_template("docs/documentation.html")

@app.route('/chartjs')
@login_required
def chartjs():
    """Render the Chart.js visualization page."""
    return render_template("pages/charts/chartjs.html")

# ------------------ RUN FLASK APP ------------------
if __name__ == "__main__":  
    app.run(debug=True)