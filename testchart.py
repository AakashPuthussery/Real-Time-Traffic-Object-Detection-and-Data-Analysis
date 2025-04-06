# import numpy as np
# import matplotlib.pyplot as plt
# from sklearn.metrics import roc_curve, auc

# # Generate synthetic data for a perfect classifier
# np.random.seed(42)

# # Perfectly separable data
# y_true = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])  # True labels (0: negative, 1: positive)
# y_scores = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])  # Predicted scores (higher for positive class)

# # Compute ROC curve and AUC
# fpr, tpr, thresholds = roc_curve(y_true, y_scores)
# roc_auc = auc(fpr, tpr)

# # Plot the perfect ROC curve
# plt.figure(figsize=(8, 6))
# plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'Perfect ROC curve (AUC = {roc_auc:.2f})')
# plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--', label='Random Guess (AUC = 0.50)')
# plt.xlim([0.0, 1.0])
# plt.ylim([0.0, 1.05])
# plt.xlabel('False Positive Rate (FPR)')
# plt.ylabel('True Positive Rate (TPR)')
# plt.title('Perfect ROC Curve')
# plt.legend(loc='lower right')
# plt.grid(True)
# plt.show()

import pymysql
from datetime import datetime
from flask import Flask, jsonify, render_template

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

def get_comparison():
    """Compare today's current time data with yesterday's entire day data."""
    connection = get_db_connection()
    if not connection:
        return None

    try:
        with connection.cursor() as cursor:
            categories = ["bike", "car", "bus", "pedestrian", "truck", "animals"]
            comparison_data = []
            
            # Get current hour (to filter today's data up to now)
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
                print(f"✅ Today's {category} data (up to hour {current_hour}): {today_count}")

                # Fetch yesterday's total count for the entire day
                sql_yesterday = f"""
                    SELECT SUM({category}) AS total_count
                    FROM traffic 
                    WHERE DATE(`current_date`) = CURDATE() - INTERVAL 1 DAY;
                """
                cursor.execute(sql_yesterday)
                yesterday_total = cursor.fetchone()[0] or 0  # Convert None to 0
                print(f"✅ Yesterday's {category} total data: {yesterday_total}")

                # Calculate percentage difference
                percentage_difference = ((today_count - yesterday_total) / (yesterday_total)) * 100
                
                comparison_data.append({
                    "category": category,
                    "today": today_count,
                    "yesterday_total": yesterday_total,
                    "percentage_difference": round(percentage_difference, 2)
                })

            return comparison_data

    except pymysql.MySQLError as e:
        print(f"❌ Database error: {e}")
        return None
    finally:
        connection.close()

@app.route('/hourly_comparison', methods=['GET'])
def hourly_comparison():
    """API endpoint to get today's cumulative data compared to yesterday's total."""
    data = get_comparison()
    if data is not None:
        return jsonify(data)
    return jsonify({"error": "Database error occurred."}), 500

# ------------------ RUN FLASK APP ------------------
if __name__ == "__main__":  
    app.run(debug=True)
