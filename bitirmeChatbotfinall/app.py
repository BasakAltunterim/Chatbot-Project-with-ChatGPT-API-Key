from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
import json
import os


from bot.openkey import chatbot_response1
from bot.simularity import chatbot_response

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Flash messages

# Route for the main page
@app.route("/")
def index():
    return render_template("home.html")

# Chat endpoint
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")
    simularity_enabled = data.get("simularity_enabled", False)

    try:
        
        if simularity_enabled:
            response = chatbot_response(user_message)  
        else:
            response = chatbot_response1(user_message)  # OpenAI GPT chatbot

        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"response": f"An error occurred: {e}"})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if os.path.exists("users.json"):
            with open("users.json", "r") as file:
                users = json.load(file)
        else:
            users = []

       
        for user in users:
            if user["username"] == username and user["password"] == password:
                return redirect(url_for("index"))

        flash("Invalid username or password!")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        new_user = {
            "username": username,
            "email": email,
            "password": password
        }

        if os.path.exists("users.json"):
            with open("users.json", "r") as file:
                users = json.load(file)
        else:
            users = []

        for user in users:
            if user["username"] == username:
                flash("This username is already taken.")
                return redirect(url_for("signup"))

        users.append(new_user)

        with open("users.json", "w") as file:
            json.dump(users, file, indent=4)

        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        username = request.form.get("username")
        new_password = request.form.get("new_password")

        if os.path.exists("users.json"):
            with open("users.json", "r") as file:
                users = json.load(file)
        else:
            users = []

        user_found = False
        for user in users:
            if user["username"] == username:
                user["password"] = new_password
                user_found = True
                break

        if user_found:
            with open("users.json", "w") as file:
                json.dump(users, file, indent=4)

            flash("Password successfully updated. Please login.")
            return redirect(url_for("login"))
        else:
            flash("User not found.")

    return render_template("reset_password.html")

if __name__ == "__main__":
    app.run(debug=True)
