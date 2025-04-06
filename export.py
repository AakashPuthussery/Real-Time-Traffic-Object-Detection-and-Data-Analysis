from flask import Flask, render_template, request, make_response
import pymysql
from io import StringIO
import csv
from datetime import datetime

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
        print(f"Database connection error: {e}")
        return None

@app.route('/')
def home():
    return '''
    <h1>Traffic Data Export</h1>
    <p><a href="/export">Export Data</a></p>
    '''

@app.route('/export', methods=['GET', 'POST'])
def export_data():
    if request.method == 'GET':
        # Show the export form
        return '''
        <h2>Export Traffic Data</h2>
        <form method="POST">
            <label>Start Date: <input type="date" name="start_date" required></label><br>
            <label>End Date: <input type="date" name="end_date" required></label><br>
            <button type="submit">Export CSV</button>
        </form>
        '''
    
    # Handle POST request
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    
    # Validate dates
    try:
        datetime.strptime(start_date, '%Y-%m-%d')
        datetime.strptime(end_date, '%Y-%m-%d')
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
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            response.headers['Content-type'] = 'text/csv'
            return response
            
    except pymysql.MySQLError as e:
        return f"Database error: {e}", 500
    finally:
        connection.close()

if __name__ == '__main__':
    app.run(debug=True)