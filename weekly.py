import pymysql
import pandas as pd
from datetime import datetime, timedelta

def fetch_weekly_data():
    # Database connection
    connection = pymysql.connect(
        host='localhost',
        user='aakash',
        password='12345678',
        database='traffic_db'
    )
    
    cursor = connection.cursor()
    
    # Get the current date and calculate start dates
    today = datetime.today()
    start_this_week = today - timedelta(days=today.weekday())  # Monday of this week
    start_last_week = start_this_week - timedelta(days=7)  # Monday of last week
    
    # Fetch data for this week
    query_this_week = """
        SELECT DAYNAME(current_date) AS day, SUM(car + bus + bike + truck + pedestrian + animals)
        FROM traffic
        WHERE current_date >= %s AND current_date <= %s
        GROUP BY DAYNAME(current_date)
        ORDER BY FIELD(DAYNAME(current_date), 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday')
    """
    cursor.execute(query_this_week, (start_this_week, today))
    this_week_data = cursor.fetchall()
    
    # Fetch data for last week
    query_last_week = """
        SELECT DAYNAME(current_date) AS day, SUM(car + bus + bike + truck + pedestrian + animals)
        FROM traffic
        WHERE current_date >= %s AND current_date < %s
        GROUP BY DAYNAME(current_date)
        ORDER BY FIELD(DAYNAME(current_date), 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday')
    """
    cursor.execute(query_last_week, (start_last_week, start_this_week))
    last_week_data = cursor.fetchall()
    
    # Close the connection
    cursor.close()
    connection.close()
    
    # Process data
    days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    this_week_dict = {day: 0 for day in days}
    last_week_dict = {day: 0 for day in days}
    
    for row in this_week_data:
        this_week_dict[row[0]] = row[1]
    
    for row in last_week_data:
        last_week_dict[row[0]] = row[1]
    
    return list(this_week_dict.values()), list(last_week_dict.values())

if __name__ == "__main__":
    this_week, last_week = fetch_weekly_data()
    print("This week:", this_week)
    print("Last week:", last_week)
