from flask import Flask
from datetime import datetime
import pymysql

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

@app.route('/test_time')
def test_time():
    """Check Flask server time and MySQL time."""
    # Get server time (Flask)
    flask_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Get MySQL time
    connection = get_db_connection()
    if not connection:
        return {"error": "Database connection failed"}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT NOW();")
            mysql_time = cursor.fetchone()[0]
    finally:
        connection.close()

    return {
        "flask_server_time": flask_time,
        "mysql_server_time": str(mysql_time)
    }

if __name__ == "__main__":
    app.run(debug=True)
