from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html", active_page="dashboard")

@app.route("/ui")
def ui_showcase():
    return render_template("ui_showcase.html", active_page="ui")

if __name__ == "__main__":
    app.run(debug=True)
