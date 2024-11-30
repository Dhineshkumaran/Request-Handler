from flask import Flask, request, jsonify, send_file
from pymongo import MongoClient
import pandas as pd
from flask_mail import Mail, Message
import os

app = Flask(__name__)

# MongoDB configuration
MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URI)
db = client['request_handler']  # Database name
collection = db['requests']  # Collection name

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'  # Use your mail server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USER')  # Add your email
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASS')  # Add your email password

mail = Mail(app)


# Route to serve the HTML form
@app.route('/')
def serve_form():
    return send_file("index.html")

# Route to serve the Update HTML
@app.route('/update')
def serve_update_html():
    return send_file("update.html")

# Route to handle form submission
@app.route('/submit', methods=['POST'])
def handle_form_submission():
    try:
        # Extract form data
        id = request.form.get("id")
        description = request.form.get("description")
        status = request.form.get("status")
        assigner_name = request.form.get("assigner_name")
        assignee_name = request.form.get("assignee_name")
        email = request.form.get("email")

        # Data to store in MongoDB
        data = {
            "_id": id,
            "description": description,
            "status": status,
            "assigned_by": assigner_name,
            "assigned_to": assignee_name,
            "email": email
        }

        # Insert data into MongoDB
        collection.insert_one(data)

        # Send email notification
        send_email_notification(email, assigner_name, description)

        return "Form submitted successfully!", 200
    except Exception as e:
        print(f"Error: {e}")
        return "Error occurred while submitting the form!", 500

def send_email_notification(to_email, assigner_name, description):
    try:
        subject = "New Request Assigned"
        body = f"""
        Hello,

        A new request has been assigned to you by {assigner_name}.
        Description: {description}

        Please check your dashboard for more details.

        Regards,
        Request Manager
        """
        msg = Message(subject, sender=os.getenv('EMAIL_USER'), recipients=[to_email])
        msg.body = body
        mail.send(msg)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error while sending email: {e}")
    
# Route to serve the request data
@app.route('/api/v1/requests', methods=['GET'])
def get_requests():
    try:
        cursor = collection.find({})
        # Convert cursor to a list of dictionaries
        requests = list(cursor)
        return jsonify({"status": "success", "data": requests}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/api/v1/requests/<id>', methods=['PATCH'])
def update_status(id):
    try:
        data = request.json
        new_status = data.get('status')

        # Validate the new status
        if new_status not in ['In progress', 'Completed']:
            return jsonify({'error': 'Invalid status'}), 400

        # Fetch the request to get email and other details
        request_data = collection.find_one({'_id': id})
        if not request_data:
            return jsonify({'error': 'Request not found'}), 404

        # Update the status in MongoDB
        result = collection.update_one({'_id': id}, {'$set': {'status': new_status}})
        if result.matched_count == 0:
            return jsonify({'error': 'Request not found'}), 404

        # Send email notification
        to_email = request_data['email']
        assignee_name = request_data['assigned_to']
        description = request_data['description']
        send_status_update_email(to_email, assignee_name, description, new_status)

        return jsonify({'message': 'Status updated successfully and email sent!'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
def send_status_update_email(to_email, assignee_name, description, new_status):
    try:
        subject = "Request Status Updated"
        body = f"""
        Hello {assignee_name},

        The status of the request assigned to you has been updated.

        Description: {description}
        New Status: {new_status}

        Please check your dashboard for more details.

        Regards,
        Request Manager
        """
        msg = Message(subject, sender=os.getenv('EMAIL_USER'), recipients=[to_email])
        msg.body = body
        mail.send(msg)
        print("Status update email sent successfully!")
    except Exception as e:
        print(f"Error while sending status update email: {e}")
        
@app.route('/download')
def get_csv():
    client = MongoClient(MONGO_URI)
    db = client['request_handler']  # Database name
    collection = db['requests']  # Collection name
    cursor = collection.find() 
    data = list(cursor)
    df = pd.DataFrame(data)
    df.to_csv('request_data.csv', index=False)
    return send_file('request_data.csv', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=3000)