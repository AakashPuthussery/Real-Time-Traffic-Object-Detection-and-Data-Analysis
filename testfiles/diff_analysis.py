import pymysql

def get_db_connection():
    try:
        connection = pymysql.connect(
            host="localhost",
            user="root",
            password="12345678",
            database="traffic_db"
        )
        return connection
    except pymysql.MySQLError as e:
        print(f"Database connection error: {e}")
        return None

def get_hourly_car_counts():
    connection = get_db_connection()
    if not connection:
        return None

    try:
        with connection.cursor() as cursor:
            sql_today = """
                SELECT HOUR(`current_time`) AS hour, SUM(car) AS total_cars
                FROM traffic 
                WHERE DATE(`current_date`) = CURDATE()
                GROUP BY HOUR(`current_time`)
                ORDER BY hour;
            """
            cursor.execute(sql_today)
            today_data = cursor.fetchall()

            sql_yesterday = """
                SELECT HOUR(`current_time`) AS hour, SUM(car) AS total_cars
                FROM traffic 
                WHERE DATE(`current_date`) = CURDATE() - INTERVAL 1 DAY
                GROUP BY HOUR(`current_time`)
                ORDER BY hour;
            """
            cursor.execute(sql_yesterday)
            yesterday_data = cursor.fetchall()

            # Convert results to dictionaries for comparison
            today_dict = {row[0]: row[1] for row in today_data}
            yesterday_dict = {row[0]: row[1] for row in yesterday_data}

            hourly_comparison = []
            for hour in range(24):
                today_count = today_dict.get(hour, 0)
                yesterday_count = yesterday_dict.get(hour, 0)
                difference = today_count - yesterday_count

            hourly_comparison.append({
                "hour": hour,
                "today": int(today_count),
                "yesterday": int(yesterday_count),
                "difference": int(difference)
            })

            return hourly_comparison

    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return None
    finally:
        if connection:
            connection.close()

# Run the function and print the output
if __name__ == "__main__":
    results = get_hourly_car_counts()
    if results:
        for row in results:
            print(row)
    else:
        print("No data retrieved.")
