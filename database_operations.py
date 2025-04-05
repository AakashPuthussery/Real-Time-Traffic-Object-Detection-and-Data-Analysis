import pymysql

def insert_data(car, bus, bike, truck, pedestrian, animals, current_date, current_time):
    try:
        print("Connecting to database...")
        connection = pymysql.connect(
            host="localhost",
            user="root",
            password="12345678",
            database="traffic_db"
        )
        print("Connected successfully!")

        with connection.cursor() as cursor:
            sql = """
                INSERT INTO traffic (`car`, `bus`, `bike`, `truck`, `pedestrian`, `animals`, `current_date`, `current_time`) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (car, bus, bike, truck, pedestrian, animals, current_date, current_time)
            print("Executing query...")
            cursor.execute(sql, values)
            print("Query executed!")

        connection.commit()
        print("Data inserted successfully!")

    except pymysql.MySQLError as e:
        print(f"Database error: {e}")

    finally:
        connection.close()
        print("Connection closed.")

# Example usage:
insert_data(6, 2, 10, 3, 4, 1, '2025-03-21', '05:30:00')
