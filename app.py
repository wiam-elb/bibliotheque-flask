from dbm import error
from sqlite3 import dump
from tkinter.constants import INSERT
from MySQLdb import cursors
import os
from flask import Flask,flash,request,render_template,redirect,url_for,session, g
from flask_mysqldb import MySQL
import MySQLdb.cursors
from flask_bcrypt import Bcrypt
from flask import send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm
from io import BytesIO
from flask_mail import Mail, Message
import re
from werkzeug.utils import secure_filename
from reportlab.lib.utils import ImageReader




app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'wiamelbadaoui97@gmail.com'
app.config['MAIL_PASSWORD'] = 'TON_MOT_DE_PASSE_APPLICATION'
app.config['MAIL_DEFAULT_SENDER'] = 'wiamelbadaoui97@gmail.com'
mail = Mail(app)

app.secret_key = 'wiam07'
bcrypt = Bcrypt(app)

app.config['DEVELOPMENT'] = True
app.config['DEBUG'] = True

app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'wiam2007'
app.config['MYSQL_DB'] = 'biblio'

mysql = MySQL(app)

@app.before_request
def load_loggedin_user():
    g.user = None
    if "userid" in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("select * from users where id=%s", (session['userid'],))
        g.user = cursor.fetchone()

def login_check():
    if "userid" not in session:
        flash('you must logged in to access this page', 'error')
        return redirect(url_for("login"))

@app.route('/')
def index():
         cur = mysql.connection.cursor()
         cur.execute("select * from users")
         data = cur.fetchall()
         cur.close()
         return render_template('index.html')


@app.route('/login', methods=["GET", "POST"])
def login():

    if request.method == 'POST':
        email = request.form["email"]
        password = request.form["password"]

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        account = cursor.fetchone()

        if account and bcrypt.check_password_hash(account["password"], password):

            session["userid"] = account["id"]
            session["login"] = True

            if account["usertype"] == "admin":
                return redirect("/admin/dashboard", code=302)
            else:
                return redirect("/user/dashboard", code=302)

        else:
            flash("Email ou mot de passe incorrect", "error")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == 'POST':
        prenom = request.form["prenom"]
        nom  = request.form["nom"]
        email     = request.form["email"]
        password  = request.form["password"]
        confirm_password = request.form["confirm_password"]

        hashed_password = bcrypt.generate_password_hash(password)

        if password !=confirm_password :
            flash('password doesnt match confirm_password', 'error')
            return redirect(url_for('register'))

        cursor = mysql.connection.cursor()

        cursor.execute("select id  from users where email=%s ",(email,))
        exist = cursor.fetchone()
        if exist:
            cursor.close()
            flash('email already exist', 'error')
            return redirect(url_for('register'))

        cursor.execute('INSERT INTO users (prenom,nom,email,password) VALUES (%s,%s,%s,%s)',(prenom,nom,email,hashed_password))
        mysql.connection.commit()
        cursor.close()
        flash('you have seccussefly registred please login', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/admin/dashboard')
def dashboard_admin():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT COUNT(*) AS total FROM livres")
    total_livres = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM users WHERE usertype='etudiant'")
    total_users = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM reservations")
    total_reservations = cursor.fetchone()["total"]

    return render_template(
        "admin/dashboard.html",
        total_livres=total_livres,
        total_users=total_users,
        total_reservations=total_reservations,
    )

@app.route('/admin/users')
def users():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    search = request.args.get("search", "").strip()
    if search:
        cursor.execute("""  SELECT * FROM users WHERE id = %s
         OR nom LIKE %s OR prenom LIKE %s """, (search, "%" + search + "%", "%" + search + "%"))
    else:
        cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    cursor.close()
    return render_template('admin/users/users.html', users=users)


@app.route('/admin/users/modifier_user/<int:id>', methods=['GET', 'POST'])
def modifier_user(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if request.method == 'POST':
        nom = request.form['nom']
        prenom = request.form['prenom']
        email = request.form['email']
        usertype = request.form['usertype']
        cursor.execute("UPDATE users SET nom=%s,prenom=%s,email=%s,usertype=%s WHERE id=%s", (nom, prenom, email, usertype, id))
        mysql.connection.commit()
        return redirect(url_for('users'))
    cursor.execute("SELECT * FROM users WHERE id=%s", (id,))
    user = cursor.fetchone()
    return render_template("admin/users/modifier_user.html", user=user)


@app.route('/admin/users/supprimer_user<int:id>')
def supprimer_user(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM reservations WHERE user_id=%s", (id,))
    cursor.execute("DELETE FROM users WHERE id=%s", (id,))
    mysql.connection.commit()
    return redirect(url_for('users'))


@app.route('/admin/reservations')
def reservations():

    recherche = request.args.get("search", "").strip()
    statut = request.args.get("statut", "").strip()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if recherche and statut:
        cursor.execute(""" SELECT * FROM reservations WHERE (id = %s OR livre_id = %s OR user_id = %s
         OR reservation.user_nom =%s OR reservation.user_prenom =%s) AND statut = %s """, (recherche, recherche, recherche
        ,recherche,recherche, statut))

    elif recherche:
        cursor.execute(""" SELECT * FROM reservations WHERE id = %s OR livre_id = %s
         OR user_id = %s OR reservation.user_nom =%s OR reservation.user_prenom =%s """, (recherche, recherche, recherche,recherche,recherche))

    elif statut:
        cursor.execute(""" SELECT * FROM reservations WHERE statut = %s """, (statut,))
    else:
        cursor.execute("""SELECT * FROM reservations """)
    reservations = cursor.fetchall()
    cursor.close()
    return render_template('admin/reservations/reservations.html', reservations=reservations)


@app.route('/admin/reservations/detail_reservation/<int:id>')
def detail_reservation(id):
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM reservations JOIN users ON reservations.user_id = users.id JOIN livres ON reservations.livre_id = livres.id WHERE reservations.id = %s", (id,))
        mysql.connection.commit()
        reservation = cursor.fetchone()
        return render_template(
        "admin/reservations/detail_reservation.html",
        reservation=reservation )


@app.route('/admin/reservations/detail_reservation/accepter_reservation/<int:id>', methods=['GET', 'POST'])
def accepter_reservation(id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("select * from reservations where id = %s", (id,))
    reservation = cursor.fetchone()

    cursor.execute("UPDATE reservations SET statut = 'accepte' WHERE id = %s", (id,))
    mysql.connection.commit()

    cursor.execute("UPDATE livres SET quantite=quantite-1 WHERE id = %s",  (reservation['livre_id'],))
    mysql.connection.commit()
    return redirect(url_for('detail_reservation', id=id)
                    )


@app.route('/admin/reservations/detail_reservation/refuser_reservation/<int:id>', methods=['GET', 'POST'])
def refuser_reservation(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("UPDATE reservations SET statut = 'refuse' WHERE id = %s", (id,))
    mysql.connection.commit()
    return redirect(url_for('detail_reservation',id=id))


@app.route('/admin/reservations/detail_reservation/livre_retourne/<int:id>', methods=['GET', 'POST'])
def livre_retourne(id):

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("select * from reservations where id = %s", (id,))
        reservation = cursor.fetchone()

        cursor.execute("UPDATE reservations SET statut = 'retourne' WHERE id = %s", (id,))
        mysql.connection.commit()

        cursor.execute("UPDATE livres SET quantite=quantite+1 WHERE id = %s", (reservation['id'],))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('detail_reservation',id=id))

@app.route('/admin/categories')
def categories():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM categories  ORDER BY id ASC ")
    categories = cursor.fetchall()
    cursor.close()
    return render_template('admin/categories/categories.html', categories=categories)


@app.route('/admin/categories/ajouter_categorie', methods=['GET', 'POST'])
def ajouter_categorie():
        if request.method == 'POST':
            nom = request.form['nom']
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO categories (nom) VALUES (%s) ",(nom,) )
            mysql.connection.commit()
            return redirect(url_for('categories'))
        return render_template('admin/categories/ajouter_categorie.html')


@app.route('/supprimer_categorie/<int:id>')
def supprimer_categorie(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM categories WHERE id=%s", (id,))
    mysql.connection.commit()
    return redirect(url_for('categories'))


@app.route("/admin/livres/create_livre", methods=["GET", "POST"])
def create_livre():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':

        titre = request.form["titre"]
        auteur = request.form["auteur"]
        image = request.files["image"]
        ISBN = request.form["ISBN"]
        nombre_de_pages = request.form["nombre_de_pages"]
        langue = request.form["langue"]
        annee_publication = request.form["annee_publication"]
        quantite = request.form["quantite"]
        description = request.form["description"]
        publiee = request.form["publiee"]
        categorie = request.form["categorie"]

        image.save(os.path.join(
            'static/uploads',
            secure_filename(image.filename)
        ))

        image_name = image.filename

        cursor.execute("""
            INSERT INTO livres
            (titre, auteur, image, isbn, nombre_de_pages, langue,
             annee_publication, quantite, description, categorie_id, publiee)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            titre, auteur, image_name, ISBN, nombre_de_pages,
            langue, annee_publication, quantite, description,
            categorie, publiee
        ))

        mysql.connection.commit()

        flash("Livre créé avec succès", "success")

        cursor.close()

        return redirect(url_for('create_livre'))

    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()

    cursor.close()

    return render_template(
        'admin/livres/create_livre.html',
        categories=categories
    )




@app.route("/admin/livres", methods=["GET", "POST"])
def livres():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    search = request.args.get("search")
    if search:
        cursor.execute(""" SELECT livres.*, categories.nom AS categorie_nom FROM livres
        JOIN categories ON livres.categorie_id = categories.id WHERE livres.id = %s
         OR livres.titre LIKE %s """, (search, "%" + search + "%"))

    else:
        cursor.execute("""SELECT livres.*, categories.nom as categorie_nom from livres JOIN categories 
                   on livres.categorie_id=categories.id""")
    livres = cursor.fetchall()
    cursor.close()
    return render_template('admin/livres/gestion_des_livres.html', livres=livres)




@app.route('/logout')
def logout():
    g.user = None
    session['loggedin'] = False
    session['userid'] = None
    flash("You logged out successfully!!")
    return redirect(url_for('index'))




@app.route('/user/historique_reservations/',methods=['GET', 'POST'])
def historique_reservations():
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT r.id,l.titre AS livre_titre, c.nom AS livre_categorie, r.date_reservation,r.statut FROM reservations r LEFT JOIN livres l on r.livre_id=l.id LEFT JOIN categories c on c.id=l.id")
        reservations = cursor.fetchall()
        cursor.close()
        return render_template("user/historique_reservations.html",reservations=reservations)




@app.route('/test-logo')
def test_logo():

    logo_path = os.path.join(
        app.root_path,
        'uploads',
        'logo.jpeg'
    )

    print("================================")
    print("APP ROOT:", app.root_path)
    print("LOGO PATH:", logo_path)
    print("EXISTS:", os.path.exists(logo_path))
    print("================================")

    if not os.path.exists(logo_path):
        return "Logo introuvable : " + logo_path, 404

    return send_from_directory(
        os.path.join(app.root_path, 'uploads'),
        'logo.jpeg'
    )


@app.route('/user/reservation/recu/<int:id>')
def telecharger_recu(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT reservations.id,
               reservations.date_reservation,
               reservations.statut,
               users.nom,
               users.prenom,
               livres.titre
        FROM reservations
        JOIN users ON reservations.user_id = users.id
        JOIN livres ON reservations.livre_id = livres.id
        WHERE reservations.id = %s
    """, (id,))

    reservation = cursor.fetchone()
    cursor.close()

    if not reservation:
        return "Réservation introuvable", 404

    pdf = BytesIO()

    largeur = 80 * mm
    hauteur = 150 * mm

    document = canvas.Canvas(
        pdf,
        pagesize=(largeur, hauteur)
    )
    # =========================
    # LOGO
    # =========================

    logo_path = os.path.join(
        app.root_path,
        "uploads",
        "logo.jpeg"
    )

    print("================================")
    print("LOGO PATH =", logo_path)
    print("EXISTS =", os.path.exists(logo_path))
    print("================================")

    if os.path.exists(logo_path):
        document.drawImage(
            logo_path,
            5 * mm,
            120 * mm,
            width=18 * mm,
            height=18 * mm,
            preserveAspectRatio=True,
            mask="auto"
        )
    # =========================
    # TITRE
    # =========================

    document.setFont("Helvetica-Bold", 12)

    document.drawCentredString(
        largeur / 2,
        125 * mm,
        "BIBLIOTHÈQUE"
    )

    document.setFont("Helvetica-Bold", 11)

    document.drawCentredString(
        largeur / 2,
        117 * mm,
        "REÇU DE RÉSERVATION"
    )

    # Ligne
    document.line(
        8 * mm,
        113 * mm,
        72 * mm,
        113 * mm
    )

    # =========================
    # INFORMATIONS
    # =========================

    document.setFont("Helvetica", 9)

    y = 103 * mm

    document.drawString(
        8 * mm,
        y,
        f"Nom : {reservation['nom']} {reservation['prenom']}"
    )

    y -= 10 * mm

    document.drawString(
        8 * mm,
        y,
        f"Livre : {reservation['titre']}"
    )

    y -= 10 * mm

    document.drawString(
        8 * mm,
        y,
        f"Date : {reservation['date_reservation']}"
    )

    y -= 10 * mm

    document.drawString(
        8 * mm,
        y,
        f"Statut : {reservation['statut']}"
    )

    y -= 20 * mm

    # =========================
    # MESSAGE
    # =========================

    document.setFont("Helvetica-Bold", 9)

    document.drawCentredString(
        largeur / 2,
        y,
        "Merci pour votre réservation !"
    )

    y -= 7 * mm

    document.setFont("Helvetica", 8)

    document.drawCentredString(
        largeur / 2,
        y,
        "Veuillez mener le reçu avant de dépasser le délai de 24 h."
    )

    document.save()

    pdf.seek(0)

    return send_file(
        pdf,
        as_attachment=True,
        download_name=f"recu_reservation_{id}.pdf",
        mimetype="application/pdf"
    )


@app.route('/user/catalogue', methods=["POST","GET"])
def catalogue():
    recherche =request.args.get("recherche", "").strip()
    categories=request.args.get("categories", "").strip()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if recherche:
        cur.execute("""SELECT livres.*, categories.nom AS nom_categorie
        FROM livres JOIN categories ON livres.categorie_id = categories.id 
        WHERE livres.titre LIKE %s""", ("%" + recherche + "%",))
    elif categories:
        cur.execute("""SELECT livres.*, categories.nom AS nom_categorie
            FROM livres
            JOIN categories ON livres.categorie_id = categories.id
            WHERE categories.nom = %s """, (categories,))
    elif recherche and categories:
        cur.execute("""SELECT livres.*, categories.nom AS nom_categorie
        FROM livres JOIN categories ON livres.categorie_id = categories.id WHERE
        livres.titre LIKE %s AND categories.nom = %s """, ("%" + recherche + "%", categories,))
    else:
        cur.execute("SELECT livres.*, categories.nom AS nom_categorie FROM livres JOIN categories ON livres.categorie_id = categories.id")
    livres = cur.fetchall()
    return render_template("user/catalogue.html",livres=livres)


@app.route('/user/catalogue/reserver_livre/<int:id>', methods=["POST","GET"])
def reserver_livre(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM livres WHERE id=%s", (id,))
    livre = cursor.fetchone()
    cursor.execute("INSERT INTO reservations (user_id, livre_id, date_reservation) VALUES (%s, %s, NOW())",(g.user["id"],livre["id"]))
    mysql.connection.commit()
    cursor.close()
    flash("livres successfully", 'success')
    return redirect(url_for('catalogue'))


@app.route('/user/profil', methods=['GET', 'POST'])
def profil():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':

        action = request.form.get('action')
        if action == 'infos':

            nom = request.form['nom'].strip()
            prenom = request.form['prenom'].strip()
            email = request.form['email'].strip()
            if not re.fullmatch(r"[A-Za-zÀ-ÿ\s]+", nom):

                flash(
                    "Le nom doit contenir uniquement des lettres.",
                    "danger"
                )
                cursor.close()
                return redirect(url_for('profil'))
            if not re.fullmatch(r"[A-Za-zÀ-ÿ\s]+", prenom):
                flash(
                    "Le prénom doit contenir uniquement des lettres.",
                    "danger")
                cursor.close()
                return redirect(url_for('profil'))
            if not re.fullmatch(
                r"[A-Za-z0-9._%+-]+@gmail\.com",
                email,
                re.IGNORECASE
            ):
                flash(
                    "Veuillez entrer une adresse Gmail valide.",
                    "danger"
                )
                cursor.close()
                return redirect(url_for('profil'))
            cursor.execute("""SELECT id FROM users WHERE email = %s AND id != %s""", (
                email, g.user['id'] ))
            email_existe = cursor.fetchone()
            if email_existe:
                flash(
                    "Cette adresse Gmail est déjà utilisée par un autre utilisateur.",
                    "danger"
                )
                cursor.close()
                return redirect(url_for('profil'))
            cursor.execute(""" UPDATE users SET nom = %s,prenom = %s, email = %s WHERE id = %s""", (
                nom,prenom,email,g.user['id']))
            mysql.connection.commit()
            cursor.execute("""SELECT * FROM users WHERE id = %s""", (g.user['id'],))
            g.user = cursor.fetchone()
            flash( "Vos informations ont été modifiées avec succès.",
                "success")
        elif action == 'password':
            ancien_password = request.form['ancien_password']
            nouveau_password = request.form['nouveau_password']
            confirmer_password = request.form['confirmer_password']

            if not bcrypt.check_password_hash(
                g.user['password'],
                ancien_password):
                flash("L'ancien mot de passe est incorrect.",
                    "danger")

            elif nouveau_password != confirmer_password:
                flash("Les deux nouveaux mots de passe ne correspondent pas.",
                    "danger")
            else:

                nouveau_hash = bcrypt.generate_password_hash(
                    nouveau_password
                ).decode('utf-8')
                cursor.execute(""" UPDATE users SET password = %s WHERE id = %s""", (
                    nouveau_hash, g.user['id']))
                mysql.connection.commit()
                g.user['password'] = nouveau_hash
                flash( "Votre mot de passe a été modifié avec succès.",
                    "success")
    cursor.close()
    return render_template('user/profil.html')


@app.route('/user/dashboard',methods=["GET","POST"])
def dashboard():
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute(""" SELECT COUNT(*) AS total FROM reservations WHERE user_id = %s AND statut = %s
        """, (g.user['id'], 'en attente'))
        total_en_attente = cursor.fetchone()['total']

        cursor.execute(""" SELECT COUNT(*) AS total FROM reservations WHERE user_id = %s AND statut = %s
        """, (g.user['id'], 'refuse'))
        total_refusee = cursor.fetchone()['total']

        cursor.execute(""" SELECT COUNT(*) AS total FROM reservations WHERE user_id = %s
         AND statut = %s """, (g.user['id'], 'accepte'))
        total_acceptee = cursor.fetchone()['total']
        cursor.close()
        return render_template(
            'user/dashboard.html',
            total_en_attente=total_en_attente,
            total_refusees=total_refusee,
            total_acceptees=total_acceptee
        )


@app.route('/apropos')
def apropos():
    return render_template('apropos.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        nom = request.form['nom']
        email = request.form['email']
        sujet = request.form['sujet']
        message = request.form['message']
        msg = Message(
            subject=f"Contact : {sujet}",
            recipients=['bibliotheque@gmail.com'])
        msg.body = t"""Nouveau message reçu depuis le site de la bibliothèque.
Nom : {nom}
Email : {email}
Sujet : {sujet}
Message :
{message}
"""
        msg.reply_to = email
        mail.send(msg)
        return "Votre message a été envoyé avec succès."
    return render_template('contact.html')


@app.route('/supprimer_livre/<int:id>')
def supprimer_livre(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM livres WHERE id=%s", (id,))
    mysql.connection.commit()
    return redirect(url_for('livres'))


@app.route('/modifier_livre/<int:id>', methods=['GET', 'POST'])
def modifier_livre(id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()

    if request.method == 'POST':
        titre = request.form['titre']
        auteur = request.form['auteur']
        image = request.files["image"]
        ISBN = request.form["ISBN"]
        nombre_de_pages = request.form["nombre_de_pages"]
        langue = request.form["langue"]
        annee_publication = request.form["annee_publication"]
        quantite = request.form["quantite"]
        description = request.form["description"]
        categorie_id = request.form['categorie']
        cursor.execute(""" UPDATE livres SET titre=%s, auteur=%s, image=%s ,ISBN=%s, nombre_de_pages=%s,langue=%s, annee_publication =%s,quantite=%s ,description=%s, categorie_id = %s
        WHERE id=%s""", (titre, auteur,image,ISBN ,nombre_de_pages ,langue, annee_publication,  quantite , description, categorie_id, id,))
        mysql.connection.commit()
        return redirect(url_for('livres'))
    cursor.execute("SELECT * FROM livres WHERE id=%s", (id,))
    livre = cursor.fetchone()
    cursor.close()
    return render_template("admin/livres/modifier_livre.html", livre=livre,categories=categories)

if __name__ == '__main__':
    app.run(debug=True)
