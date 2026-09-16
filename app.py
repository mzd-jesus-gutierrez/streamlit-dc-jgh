# ---------------------------------------------------------------------------
# Librerías
# ---------------------------------------------------------------------------
import pandas as pd
import streamlit as st
from sqlalchemy import text
from google.cloud import firestore


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
### Constantes de MOVIES
FIRESTORE_KEY_FILE  = "./keys/data-science-project-key.json"  # Archivo no versionado
COLLECTION_MOVIES   = "movies"
# Nombres dentro del collection de movies
FIELD_NAME          = "name"
FIELD_GENRE         = "genre"
FIELD_DIRECTOR      = "director"
FIELD_COMPANY       = "company"
# Orden de columnas para el DF de movies
MOVIE_FIELDS        = [FIELD_NAME, FIELD_GENRE, FIELD_DIRECTOR, FIELD_COMPANY]
# Etiquetas de movies
FIELD_LABELS        = {
            FIELD_NAME: "Película",
            FIELD_GENRE: "Género",
            FIELD_DIRECTOR: "Director",
            FIELD_COMPANY: "Compañía",
        }
### Constantes de GUEST
POSTGRES_CONNECTION = "postgresql"
TABLE_PEOPLE        = "people"
# Nombres dentro de la tabla de guest
FIELD_EMAIL         = "email"
FIELD_COMMENT       = "comment"
# Orden de columnas para el DF de guest
GUEST_FIELDS = [FIELD_EMAIL, FIELD_COMMENT]
# Etiquetas de guest
GUEST_LABELS = {
    FIELD_EMAIL: "Correo electrónico",
    FIELD_COMMENT: "Comentario",
}


# ---------------------------------------------------------------------------
# Definición de funciones
# ---------------------------------------------------------------------------

# Acceso a datos
def create_firestore_connection():
    return firestore.Client.from_service_account_json(FIRESTORE_KEY_FILE)

def create_postgresql_connection():
    return st.connection(POSTGRES_CONNECTION, type="sql")

def get_movies(movie_db_conn):
    records = [doc.to_dict() for doc in movie_db_conn.collection(COLLECTION_MOVIES).stream()]
    # Ordenamos por orden alfabético los nombres de películas
    return pd.DataFrame(records, columns=MOVIE_FIELDS).sort_values(by=FIELD_NAME)

def get_guests_comments(guest_db_conn):
    return guest_db_conn.query(
        f"""
        SELECT {FIELD_EMAIL}, {FIELD_COMMENT}
        FROM {TABLE_PEOPLE};
        """,
        ttl=0
    )

def create_movie(movie_db_conn, movie):
    movie_db_conn.collection(COLLECTION_MOVIES).add(movie)

def create_guest(guest_db_conn, email, comment):
    with guest_db_conn.session as session:
        session.execute(
            text(
                f"""
                INSERT INTO {TABLE_PEOPLE} ({FIELD_EMAIL}, {FIELD_COMMENT})
                VALUES (:email, :comment)
                """
            ),
            {
                "email": email,
                "comment": comment,
            },
        )
        session.commit()


# Filtros de datos
def filter_movies_by_title(movies, title):
    return movies[movies[FIELD_NAME].str.contains(title, case=False, na=False, regex=False)]

def filter_movies_by_director(movies: pd.DataFrame, director: str):
    return movies[movies[FIELD_DIRECTOR] == director]


# Mostrar datos
def show_movies(header, movies):
    st.header(header)
    st.write(f"Películas encontradas: {len(movies)}")
    st.dataframe(
        movies.rename(columns=FIELD_LABELS),
        width="stretch",
        hide_index=True,
    )


# Funciones de visualización y del sidebar
def add_basic_info():
    st.set_page_config(page_title="Dashboard de películas", layout="wide")
    st.title("Dashboard de películas")

def add_show_all_movies_filter(movies):
    # Listado completo
    if st.sidebar.checkbox("Mostrar todas las películas", value=False):
        show_movies("Todas las películas", movies)

def add_show_title_movies_filter(movies):
    # Búsqueda por título de la pelí
    st.sidebar.subheader("Buscar por película")
    search_title = st.sidebar.text_input(FIELD_LABELS[FIELD_NAME]).strip()
    if st.sidebar.button("Buscar por película"):
        if search_title:
            show_movies(
                "Resultados de la búsqueda",
                filter_movies_by_title(movies, search_title),
            )
        else:
            st.sidebar.warning("Ingresa el título de la película a buscar.")

def add_show_director_movies_filter(movies):
    # Búsqueda por director de pelí
    st.sidebar.subheader("Buscar por director")
    directors = sorted(movies[FIELD_DIRECTOR].dropna().unique())
    selected_director = st.sidebar.selectbox(
        FIELD_LABELS[FIELD_DIRECTOR],
        directors,
        index=None,
        placeholder="Selecciona un director",
    )
    if st.sidebar.button("Buscar por director"):
        if selected_director:
            show_movies(
                f"Películas de {selected_director}",
                filter_movies_by_director(movies, selected_director),
            )
        else:
            st.sidebar.warning("Selecciona un director.")

def add_new_movie_form(movie_db_conn, movies):
    st.sidebar.subheader("Nueva película")

    # Obtenemos género, directores y compañías únicas basados en la BD actual, esto solo para fines del ejercicio
    genres    = sorted(movies[FIELD_GENRE].dropna().unique())
    directors = sorted(movies[FIELD_DIRECTOR].dropna().unique())
    companies = sorted(movies[FIELD_COMPANY].dropna().unique())

    with st.sidebar.form("new_movie_form", clear_on_submit=True):
        name = st.text_input(FIELD_LABELS[FIELD_NAME])

        genre = st.selectbox(
            FIELD_LABELS[FIELD_GENRE],
            genres,
            index=None,
            placeholder="Selecciona un género",
        )

        director = st.selectbox(
            FIELD_LABELS[FIELD_DIRECTOR],
            directors,
            index=None,
            placeholder="Selecciona un director",
        )

        company = st.selectbox(
            FIELD_LABELS[FIELD_COMPANY],
            companies,
            index=None,
            placeholder="Selecciona una compañía",
        )
        submitted = st.form_submit_button("Agregar película")

    if not submitted:
        return

    movie = {
        FIELD_NAME: name.strip(),
        FIELD_GENRE: genre,
        FIELD_DIRECTOR: director,
        FIELD_COMPANY: company,
    }
    
    if not all(movie.values()):
        st.sidebar.warning("Llena todos los campos.")
        return

    try:
        create_movie(movie_db_conn, movie)
    except Exception as error:
        st.sidebar.error(f"No se pudo guardar la película: {error}")
        return

    st.sidebar.success("La película se agregó correctamente.")

def add_new_guest_form(guest_db_conn):
    st.sidebar.subheader("Libro de visitas")

    with st.sidebar.form("guest_form", clear_on_submit=True):
        email = st.text_input(GUEST_LABELS[FIELD_EMAIL])
        comment = st.text_area(GUEST_LABELS[FIELD_COMMENT])

        submitted = st.form_submit_button("Registrar comentario")

    if not submitted:
        return

    email = email.strip()
    comment = comment.strip()

    if not email or not comment:
        st.sidebar.warning("Llena todos los campos.")
        return

    try:
        create_guest(guest_db_conn, email, comment)
    except Exception as error:
        st.sidebar.error(f"No se pudo registrar el comentario: {error}")
        return

    st.sidebar.success("Comentario registrado correctamente.")

def add_show_guests(guest_db_conn):
    if st.sidebar.button("Ver visitas"):
        st.sidebar.subheader("Visitantes")
        guest_comments = get_guests_comments(guest_db_conn) 
        if guest_comments.empty:
            st.sidebar.info("No hay visitas registradas.")
            return

        for index, row in guest_comments.iterrows():
            st.sidebar.write(
                f"{index + 1}.- {row[FIELD_EMAIL]} | {row[FIELD_COMMENT]}"
            )



# - MAIN - Aplicación, lo que corremos como main, no es necesario ponerlo así, pero se acomoda mejor el código
def main():
    add_basic_info()

    # Conexiones de BD
    movie_db_conn = create_firestore_connection()
    guest_db_conn = create_postgresql_connection()

    movies        = get_movies(movie_db_conn)

    if movies.empty:
        st.info("No hay películas registradas.")
    else:
        add_show_all_movies_filter(movies)
        add_show_title_movies_filter(movies)
        add_show_director_movies_filter(movies)
    
    # Alta de películas
    add_new_movie_form(movie_db_conn, movies)

    # Libro de visitas
    st.sidebar.markdown("---")
    add_new_guest_form(guest_db_conn)
    add_show_guests(guest_db_conn)


# ---------------------------------------------------------------------------
# Función principal main que corre todo lo necesario
# ---------------------------------------------------------------------------
main()
