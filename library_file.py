import os
import logging
import mysql.connector
import pandas as pd
import streamlit as st
from mysql.connector import Error
from dotenv import load_dotenv

# 1. Setup Logging & Environment
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
load_dotenv()


# 2. The Logic Layer (Backend)
class LibraryManager:
    def __init__(self):
        # 1. Load local .env if it exists (for local development)
        load_dotenv()

        # 2. Use st.secrets if available (Streamlit Cloud), else use os.getenv (Local)
        # This makes the code work BOTH on your PC and on the Web.
        self.config = {
            'host': st.secrets.get("DB_HOST", os.getenv("DB_HOST")),
            'user': st.secrets.get("DB_USER", os.getenv("DB_USER")),
            'password': st.secrets.get("DB_PASSWORD", os.getenv("DB_PASSWORD")),
            'database': st.secrets.get("DB_NAME", os.getenv("DB_NAME")),
            'port': 4000,
            'use_pure': True,
            'ssl_verify_identity': True
        }

    def _get_connection(self):
        try:
            return mysql.connector.connect(**self.config)
        except Error as e:
            st.error(f"Database Connection Error: {e}")
            return None

    def add_book(self, title, author, genre, rating):
        db = self._get_connection()
        if not db: return False
        try:
            cursor = db.cursor()
            query = "INSERT INTO my_library (title, author, genre, rating) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (title, author, genre, rating))
            db.commit()
            return True
        finally:
            db.close()

    def fetch_books(self):
        db = self._get_connection()
        if not db: return []
        try:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM my_library")
            return cursor.fetchall()
        finally:
            db.close()

    def delete_book(self, book_id):
        db = self._get_connection()
        if not db: return False
        try:
            cursor = db.cursor()
            cursor.execute("DELETE FROM my_library WHERE id = %s", (book_id,))
            db.commit()
            return cursor.rowcount > 0
        finally:
            db.close()

    def update_status(self, book_id, status):
        db = self._get_connection()
        if not db: return False
        try:
            cursor = db.cursor()
            cursor.execute("UPDATE my_library SET status = %s WHERE id = %s", (status, book_id))
            db.commit()
            return True
        finally:
            db.close()


# 3. The Interface Layer (Streamlit)
def main():
    st.set_page_config(page_title="Personal Library", layout="wide")
    manager = LibraryManager()

    st.title("📚 Personal Library Manager")
    st.sidebar.header("📥 Add New Entry")

    # Sidebar: Adding a Book
    with st.sidebar.form("add_form"):
        title = st.text_input("Book Title")
        author = st.text_input("Author")
        genre = st.selectbox("Genre", ["Technical", "Fiction", "Science", "History", "Other"])
        rating = st.slider("Rating", 1, 5, 3)
        if st.form_submit_button("Add Book"):
            if title and author:
                if manager.add_book(title, author, genre, rating):
                    st.success(f"'{title}' added!")
                    st.rerun()
            else:
                st.error("Please fill required fields.")

    # Main Section: Fetching Data
    data = manager.fetch_books()
    if data:
        df = pd.DataFrame(data)

        # Metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Books", len(df))
        c2.metric("Top Rated", len(df[df['rating'] == 5]))
        c3.metric("Currently Reading", len(df[df['status'] == 'Currently Reading']))

        # Search bar
        search = st.text_input("🔍 Search books by title or author...")
        if search:
            df = df[df['title'].str.contains(search, case=False) | df['author'].str.contains(search, case=False)]

        st.dataframe(df, use_container_width=True, hide_index=True)

        # Actions Section
        st.markdown("---")
        col_up, col_del = st.columns(2)

        with col_up:
            st.subheader("Update Status")
            selected_book = st.selectbox("Select book to update", df['title'].tolist())
            new_status = st.selectbox("New Status", ["Unread", "Currently Reading", "Read"])
            if st.button("Apply Status Change"):
                bid = df[df['title'] == selected_book]['id'].values[0]
                if manager.update_status(bid, new_status):
                    st.success("Updated!")
                    st.rerun()

        with col_del:
            st.subheader("Remove Book")
            del_book = st.selectbox("Select book to remove", df['title'].tolist())
            if st.button("🗑️ Permanent Delete", type="primary"):
                bid = df[df['title'] == del_book]['id'].values[0]
                if manager.delete_book(bid):
                    st.warning("Book Deleted.")
                    st.rerun()
    else:
        st.info("No books in your library yet. Use the sidebar to add one!")


if __name__ == "__main__":
    main()
