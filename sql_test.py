# import pymysql
# from datetime import datetime  # ✅ Import datetime

# def get_db_connection():
#     try:
#         connection = pymysql.connect(
#             host="localhost",
#             user="root",
#             password="12345678",
#             database="traffic_db"
#         )
#         return connection
#     except pymysql.MySQLError as e:
#         print(f"❌ Database connection error: {e}")
#         return None

# def get_total_counts_today():
#     connection = get_db_connection()
#     if not connection:
#         return None

#     try:
#         with connection.cursor() as cursor:
#             sql = """
#                 SELECT SUM(car), SUM(bike), SUM(bus), SUM(animals), SUM(pedestrian) 
#                 FROM traffic 
#                 WHERE `current_date` = '2025-03-18';
#             """
#             cursor.execute(sql)
#             result = cursor.fetchone()  # Fetch all counts
#             return result if result is not None else (0, 0, 0, 0, 0)  # Return zero if no data
#     except pymysql.MySQLError as e:
#         print(f"Database error: {e}")
#         return None
#     finally:
#         connection.close()

# if __name__ == "__main__":
#     totals = get_total_counts_today()
#     if totals:
#         cars, bikes, buses, animals, pedestrians = totals
#         print(f"📅 Date: {datetime.today().date()}")
#         print(f"🚗 Cars: {cars}, 🚲 Bikes: {bikes}, 🚌 Buses: {buses}, 🐾 Animals: {animals}, 🚶 Pedestrians: {pedestrians}")
#     else:
#         print("⚠️ Failed to retrieve data.")

# import pymysql
# from collections import OrderedDict

# # Function to establish a database connection
# def get_db_connection():
#     try:
#         return pymysql.connect(
#             host="localhost",
#             user="root",
#             password="12345678",
#             database="traffic_db",
#             cursorclass=pymysql.cursors.Cursor
#         )
#     except pymysql.MySQLError as e:
#         print(f"Error connecting to database: {e}")
#         return None

# # Function to format weekly data in correct order
# def format_weekly_data(data):
#     correct_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
#     return OrderedDict((day, data.get(day, 0)) for day in correct_order)

# # Function to retrieve traffic data for this week and last week
# def get_weekly_vehicle_counts():
#     connection = get_db_connection()
#     if not connection:
#         return None

#     try:
#         with connection.cursor() as cursor:
#             # SQL Query for this week's data
#             sql_this_week = """
#                 WITH this_week_days AS (
#                     SELECT DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY) + INTERVAL n DAY AS `date`
#                     FROM (SELECT 0 AS n UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6) AS nums
#                 )
#                 SELECT DATE_FORMAT(twd.date, '%a') AS day_name, 
#                     COALESCE(SUM(t.car + t.bus + t.bike + t.truck + t.pedestrian + t.animals), 0) AS total_vehicles
#                 FROM this_week_days twd
#                 LEFT JOIN traffic t ON DATE(twd.date) = DATE(t.current_date)
#                 GROUP BY twd.date
#                 ORDER BY twd.date;
#             """
#             cursor.execute(sql_this_week)
#             this_week_data = {row[0]: row[1] for row in cursor.fetchall()}

#             # SQL Query for last week's data
#             sql_last_week = """
#                 WITH last_week_days AS (
#                     SELECT DATE_SUB(CURDATE(), INTERVAL (WEEKDAY(CURDATE()) + 7) DAY) + INTERVAL n DAY AS `date`
#                     FROM (SELECT 0 AS n UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6) AS nums
#                 )
#                 SELECT DATE_FORMAT(lwd.date, '%a') AS day_name, 
#                     COALESCE(SUM(t.car + t.bus + t.bike + t.truck + t.pedestrian + t.animals), 0) AS total_vehicles
#                 FROM last_week_days lwd
#                 LEFT JOIN traffic t ON DATE(lwd.date) = DATE(t.current_date)
#                 GROUP BY lwd.date
#                 ORDER BY lwd.date;
#             """
#             cursor.execute(sql_last_week)
#             last_week_data = {row[0]: row[1] for row in cursor.fetchall()}

#             return {
#                 "this_week": format_weekly_data(this_week_data),
#                 "last_week": format_weekly_data(last_week_data),
#             }

#     except pymysql.MySQLError as e:
#         print(f"Database error: {e}")
#         return None
#     finally:
#         connection.close()

# # Running the function and printing results
# weekly_data = get_weekly_vehicle_counts()
# if weekly_data:
#     print("🚗 **Traffic Data This Week** 🚗")
#     for day, count in weekly_data["this_week"].items():
#         print(f"{day}: {count} vehicles")

#     print("\n🚦 **Traffic Data Last Week** 🚦")
#     for day, count in weekly_data["last_week"].items():
#         print(f"{day}: {count} vehicles")
# else:
#     print("❌ Error retrieving data!")
from flask import Flask, jsonify
import pymysql
from datetime import datetime, timedelta

app = Flask(__name__)

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
        print(f"Database error: {e}")
        return None

def last_week_data():
    days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
    
    today = datetime.today()
    weekday_index = today.weekday()
    
    # Get the start and end of last week
    last_sunday = today - timedelta(days=weekday_index + 8)  # Last week's Sunday
    last_saturday = today - timedelta(days=weekday_index + 2)  # Last week's Saturday

    db_results = {day: 0 for day in days}  # Initialize all days with zero
    
    conn = get_db_connection()
    if conn is None:
        return db_results  # Return zero data if connection fails

    with conn.cursor() as cursor:
        query = """
            SELECT DAYNAME(`current_date`) AS day_name, 
                   SUM(car + bike + bus + truck) AS total_vehicles
            FROM traffic 
            WHERE `current_date` BETWEEN %s AND %s 
            GROUP BY DAYNAME(`current_date`)
            ORDER BY FIELD(DAYNAME(`current_date`), 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday')
        """
        cursor.execute(query, (last_sunday.strftime('%Y-%m-%d'), last_saturday.strftime('%Y-%m-%d')))
        
        for row in cursor.fetchall():
            db_results[row["day_name"][:3].upper()] = row["total_vehicles"]  # Convert to short format
    
    conn.close()
    return [db_results[day] for day in days]

def this_week_data():
    days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
    
    today = datetime.today()
    weekday_index = today.weekday()
    
    # Get the start and end of this week
    this_sunday = today - timedelta(days=weekday_index)  # This week's Sunday
    this_saturday = this_sunday + timedelta(days=6)  # This week's Saturday

    db_results = {day: 0 for day in days}  # Initialize all days with zero
    
    conn = get_db_connection()
    if conn is None:
        return db_results  # Return zero data if connection fails

    with conn.cursor() as cursor:
        query = """
            SELECT DAYNAME(`current_date`) AS day_name, 
                   SUM(car + bike + bus + truck) AS total_vehicles
            FROM traffic 
            WHERE `current_date` BETWEEN %s AND %s 
            GROUP BY DAYNAME(`current_date`)
            ORDER BY FIELD(DAYNAME(`current_date`), 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday')
        """
        cursor.execute(query, (this_sunday.strftime('%Y-%m-%d'), this_saturday.strftime('%Y-%m-%d')))
        
        for row in cursor.fetchall():
            db_results[row["day_name"][:3].upper()] = row["total_vehicles"]  # Convert to short format
    
    conn.close()
    return [db_results[day] for day in days]

@app.route('/get-this-weekly-data')
def get_weekly_data():
    return jsonify({
        "thisWeek": this_week_data(),
        "lastWeek": last_week_data()
    })

if __name__ == '__main__':
    app.run(debug=True)
