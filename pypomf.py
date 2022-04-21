import os
from flask import Flask, request, redirect, url_for, flash, send_from_directory, g, render_template
import sqlite3
import secrets
from config import Config as Configvalues
import random
import time
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = Configvalues.UPLOAD_FOLDER
DATABASE = Configvalues.DATABASE
random.seed()



def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def allowed_file(filename):
    return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in Configvalues.ALLOWED_EXTENSIONS

@app.route('/')
def home():
   return redirect("/signup")



@app.route('/process')
def process():
    print("process started")
    req = requests.get("https://submissions.patsa.org/public/finalists.php")
    print("site loaded")
    soup = BeautifulSoup(req.text, "html.parser")
    list = [tag for tag in soup.find_all("button")]
    final = {}
    processedlist = query_db("SELECT * FROM processed", ())
    for i in list:
        if i.get_text()[0:3] not in str(processedlist):
            final[i.get_text()] = i.find_next_sibling("div")
            query_db("INSERT INTO processed (eventid) VALUES (?)", (i.get_text()[0:3],))
            print("added1")
        else:
            print("In processed list")
    user_list = query_db("SELECT * FROM registrations WHERE enabled = \"yes\"")
    for x in user_list:
        for y,z in final.items():
            from_email = Configvalues.FROMEMAIL
            to_email = x[1]
            subject = y
            content = z
            myobj = {'to': [to_email], 'from': from_email, 'subject': subject,
                     'html_body': str(content)}
            url = "https://postal.theendlessweb.com/api/v1/send/message"
            headers = {'Content-Type': "application/json", 'X-Server-API-Key': "MH8hLnmN82jBm9jINCz8SpgQ",
                       "Accept": '*/*'}
            requests.post(url, json=myobj, headers=headers)
            print("sent")
    db = getattr(g, '_database', None)
    db.commit()
    return str(final)



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    if request.method == "POST":
        verifkey = secrets.token_hex(10)
        values = (request.form['email'], "No", verifkey)
        query_db("INSERT INTO registrations (email, enabled, authtoken) VALUES (?, ?, ?);", values)
        db = getattr(g, '_database', None)
        db.commit()
        print("added")
        from_email = Configvalues.FROMEMAIL
        to_email = request.form['email']
        subject = "PA-TSA Notifier Email Verification"
        content = "Hello from Notifier! <br>\n \nHere is your verification link!\n" + Configvalues.SITEURL + "/signup/verify/" + verifkey
        myobj = {'to': [to_email], 'from': from_email, 'subject': subject,
                 'html_body': content}
        url = "https://postal.theendlessweb.com/api/v1/send/message"
        headers = {'Content-Type': "application/json", 'X-Server-API-Key': "MH8hLnmN82jBm9jINCz8SpgQ", "Accept": '*/*'}
        res = requests.post(url, json=myobj, headers=headers)
        print("sent")
        if res.status_code != 200:
            print(res)
        return '''<h2>Email sent sucessfully. Check your email for the verification code</h2>'''


@app.route('/signup/verify/<string:veriftoken>')
def verify(veriftoken):
    validtoken = query_db("SELECT * FROM registrations WHERE authtoken = ?", (veriftoken,))
    if not validtoken:
        return '''<h2>verification key unknown</h2>'''
    else:
        query_db("UPDATE registrations SET enabled = \"yes\" WHERE authtoken = ?;", (veriftoken,))
        db = getattr(g, '_database', None)
        db.commit()
        return '''<h2>Success. You will now receive emails when events are posted</h2>'''



if __name__ == '__main__':
    app.run(port=8000)
